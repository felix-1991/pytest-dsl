"""Exercise the real XML-RPC/HTTP stack with controlled socket failures."""
import errno
import io
import socket
import ssl
import xmlrpc.client
from unittest.mock import Mock

import pytest

from pytest_dsl.core.serialization_utils import XMLRPCCallError
from pytest_dsl.remote.keyword_client import RemoteKeywordClient


@pytest.fixture
def clock(monkeypatch):
    now = [0.0]
    monkeypatch.setattr('pytest_dsl.remote.keyword_client.time.monotonic', lambda: now[0])
    monkeypatch.setattr('pytest_dsl.remote.keyword_client.time.sleep',
                        lambda delay: now.__setitem__(0, now[0] + delay))
    return now


def response_socket(*, read_error=None, send_error=None):
    body = xmlrpc.client.dumps(({'status': 'PASS', 'return': 'ok'},),
                              methodresponse=True).encode()
    response = b'HTTP/1.0 200 OK\r\nContent-Length: ' + str(len(body)).encode() + b'\r\n\r\n' + body
    sock = Mock()
    if read_error == 'disconnect':
        sock.makefile.return_value = io.BytesIO(b'')
    elif read_error is not None:
        sock.makefile.return_value.readline.side_effect = read_error
    else:
        sock.makefile.return_value = io.BytesIO(response)
    if send_error is not None:
        sock.sendall.side_effect = send_error
    return sock


@pytest.mark.parametrize('scheme', ['http', 'https'])
@pytest.mark.parametrize('method', ['run_keyword', 'run_keyword_with_metadata'])
def test_three_connect_retries_recover_without_replaying_keyword(monkeypatch, clock, scheme, method):
    sock = response_socket()
    create = Mock(side_effect=[socket.timeout('lost SYN')] * 3 + [sock])
    monkeypatch.setattr(socket, 'create_connection', create)
    monkeypatch.setattr(ssl.SSLContext, 'wrap_socket', lambda self, sock, **kwargs: sock)
    client = RemoteKeywordClient(url=f'{scheme}://localhost:8270/')
    metrics = {}
    result = client._rpc_call(method, 'dd', {}, metrics=metrics)
    assert result['return'] == 'ok'
    assert create.call_count == 4
    wire = b''.join(call.args[0] for call in sock.sendall.call_args_list)
    assert wire.count(b'POST / HTTP/1.1') == 1
    assert wire.count(b'<methodName>') == 1
    sock.settimeout.assert_called_with(600)
    assert clock[0] == pytest.approx(3.5)
    assert metrics['connect_attempts'] == 4


def test_exhausted_retries_discard_connection_and_next_call_rebuilds(monkeypatch, clock):
    connections = []
    client = RemoteKeywordClient()
    transport = client.server._ServerProxy__transport
    proxy = client.server
    def fail(address, timeout, *args, **kwargs):
        connections.append(transport._connection[1])
        clock[0] += timeout
        raise socket.timeout('lost SYN')
    monkeypatch.setattr(socket, 'create_connection', fail)
    for _ in range(2):
        with pytest.raises(XMLRPCCallError) as caught:
            client._rpc_call('run_keyword', 'dd', {})
        error = caught.value
        assert error.category == 'timeout'
        assert error.transport_diagnostics['connect_attempts'] == 4
        assert 'failure_stage=tcp_connect' in str(error)
        assert 'connect_attempts=4' in str(error)
        assert transport._connection == (None, None)
        assert client.server is proxy
    assert len(connections) == 8
    assert connections[0] is not connections[4]
    assert clock[0] == pytest.approx(47.0)


@pytest.mark.parametrize('config, expected', [
    ({'connect_retry_count': 0}, 1),
    ({'connect_retry_count': '1', 'connect_timeout': 2}, 2),
])
def test_connect_retry_configuration(monkeypatch, clock, config, expected):
    create = Mock(side_effect=socket.timeout('unreachable'))
    monkeypatch.setattr(socket, 'create_connection', create)
    client = RemoteKeywordClient(sync_config=config)
    with pytest.raises(XMLRPCCallError):
        client._rpc_call('run_keyword', 'dd', {})
    assert create.call_count == expected
    assert create.call_args.args[1] == config.get('connect_timeout', 5)


@pytest.mark.parametrize('retry_budget, rpc_budget, expected', [
    (2.5, None, [1, 1]),
    (4.2, None, [1, 1, 0.7]),
    (2.5, 0.75, [0.75]),
])
def test_connect_retry_budget_includes_backoff_and_clamps_next_attempt(
        monkeypatch, clock, retry_budget, rpc_budget, expected):
    limits = []
    def fail(address, timeout, *args, **kwargs):
        limits.append(timeout)
        clock[0] += timeout
        raise socket.timeout('unreachable')
    monkeypatch.setattr(socket, 'create_connection', fail)
    client = RemoteKeywordClient(sync_config={'connect_timeout': 1, 'connect_retry_budget': retry_budget})
    with pytest.raises(XMLRPCCallError):
        client._rpc_call('run_keyword', 'dd', {}, timeout=rpc_budget)
    assert clock[0] <= (rpc_budget or retry_budget)
    assert limits == pytest.approx(expected)


def test_connect_budget_also_limits_single_attempt_when_retries_disabled(monkeypatch, clock):
    create = Mock(side_effect=socket.timeout('unreachable'))
    monkeypatch.setattr(socket, 'create_connection', create)
    client = RemoteKeywordClient(sync_config={'connect_retry_count': 0, 'connect_retry_budget': 0.25})
    with pytest.raises(XMLRPCCallError):
        client._rpc_call('run_keyword', 'dd', {})
    assert create.call_count == 1
    assert create.call_args.args[1] == 0.25


@pytest.mark.parametrize('read_error, send_error', [
    ('disconnect', None),
    (socket.timeout('response stalled'), None),
    (ConnectionResetError(errno.ECONNRESET, 'response reset'), None),
    (None, BrokenPipeError(errno.EPIPE, 'send interrupted')),
])
@pytest.mark.parametrize('scheme', ['http', 'https'])
def test_business_request_is_never_replayed_after_send(monkeypatch, clock, read_error, send_error, scheme):
    sock = response_socket(read_error=read_error, send_error=send_error)
    create = Mock(return_value=sock)
    monkeypatch.setattr(socket, 'create_connection', create)
    monkeypatch.setattr(ssl.SSLContext, 'wrap_socket', lambda self, sock, **kwargs: sock)
    client = RemoteKeywordClient(url=f'{scheme}://localhost:8270/')
    with pytest.raises(XMLRPCCallError):
        client._rpc_call('run_keyword_with_metadata', 'dd', {}, {}, None)
    assert create.call_count == 1
    assert sock.sendall.call_count == (1 if send_error else 2)


@pytest.mark.parametrize('error, attempts', [
    (ConnectionRefusedError(errno.ECONNREFUSED, 'starting'), 4),
    (OSError(10060, 'Windows timeout'), 4),
    (socket.gaierror(socket.EAI_NONAME, 'unknown host'), 1),
    (PermissionError(errno.EACCES, 'forbidden'), 1),
])
def test_only_transient_connect_errors_are_retried(monkeypatch, clock, error, attempts):
    create = Mock(side_effect=error)
    monkeypatch.setattr(socket, 'create_connection', create)
    with pytest.raises(XMLRPCCallError):
        RemoteKeywordClient()._rpc_call('run_keyword', 'dd', {})
    assert create.call_count == attempts


def test_business_policy_does_not_leak_into_sync_or_probe(monkeypatch, clock):
    create = Mock(side_effect=socket.timeout('unreachable'))
    monkeypatch.setattr(socket, 'create_connection', create)
    client = RemoteKeywordClient()
    for method, expected in [('run_keyword', 4), ('get_keyword_names', 1),
                             ('sync_variables_from_client', 1)]:
        create.reset_mock()
        with pytest.raises(XMLRPCCallError):
            client._rpc_call(method, {})
        assert create.call_count == expected


def test_real_server_executes_once_after_three_connect_failures(monkeypatch):
    import threading
    from xmlrpc.server import SimpleXMLRPCServer

    try:
        server = SimpleXMLRPCServer(('127.0.0.1', 0), allow_none=True, logRequests=False)
    except PermissionError as exc:
        pytest.skip(f'本环境不允许监听本机端口: {exc}')
    executions = []
    def execute(name, params, metadata, api_key):
        executions.append(name)
        return {'status': 'PASS', 'return': 'ok'}
    server.register_function(execute, 'run_keyword_with_metadata')
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    original_connect = socket.create_connection
    attempts = []
    def flaky_connect(address, timeout=None, *args, **kwargs):
        attempts.append(timeout)
        if len(attempts) <= 3:
            raise socket.timeout('simulated lost SYN')
        return original_connect(address, timeout, *args, **kwargs)
    monkeypatch.setattr(socket, 'create_connection', flaky_connect)
    client = RemoteKeywordClient(
        url=f'http://127.0.0.1:{server.server_address[1]}/',
        sync_config={'connect_retry_interval': 0.001})
    client._server_capabilities = {'request_metadata': True, 'request_scoped_context': True}
    try:
        result = client._execute_remote_keyword_with_outcome(name='dd')
        assert result.value == 'ok'
        assert result.diagnostics['client_rpc']['connect_attempts'] == 4
        assert len(attempts) == 4
        assert executions == ['dd']
    finally:
        client.server._ServerProxy__transport.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
