"""Recovery of slow connection failures without replaying business RPCs."""
import socket
from unittest.mock import Mock

import pytest

from pytest_dsl.core.serialization_utils import XMLRPCCallError
from pytest_dsl.remote.keyword_client import (
    RemoteKeywordClient, TimeoutTransport, TimeoutSafeTransport,
)


@pytest.fixture
def clock(monkeypatch):
    now = [0.0]
    monkeypatch.setattr('pytest_dsl.remote.keyword_client.time.monotonic', lambda: now[0])
    monkeypatch.setattr('pytest_dsl.remote.keyword_client.time.sleep', lambda delay: now.__setitem__(0, now[0] + delay))
    return now


@pytest.mark.parametrize('transport_type', [TimeoutTransport, TimeoutSafeTransport])
def test_tcp_connect_is_short_but_business_response_keeps_long_timeout(transport_type):
    transport = transport_type(timeout=600)
    connection = transport.make_connection('localhost:8270')
    sock = Mock()
    create = Mock(return_value=sock)
    # Reconfigure the cached connection with a controlled socket factory.
    connection._create_connection = create
    transport.make_connection('localhost:8270')
    connection._create_connection(('localhost', 8270), 600, None)
    assert create.call_args.args[1] == 5
    sock.settimeout.assert_called_with(600)
    transport.close()


def test_connect_timeout_is_clamped_to_remaining_rpc_timeout():
    transport = TimeoutTransport(timeout=0.25)
    conn = transport.make_connection('localhost:8270')
    create = Mock(side_effect=socket.timeout('connect timed out'))
    conn._create_connection = create
    transport.make_connection('localhost:8270')
    with pytest.raises(socket.timeout):
        conn._create_connection(('localhost', 8270), 0.25, None)
    assert create.call_args.args[1] == 0.25
    assert transport.get_effective_timeout() == 0.25


def test_sync_retries_after_a_full_attempt_timeout(clock, monkeypatch):
    client = RemoteKeywordClient(sync_config={'sync_retry_jitter': 0})
    calls = []
    def sync(variables, **kwargs):
        calls.append(kwargs['timeout'])
        if len(calls) == 1:
            clock[0] += kwargs['timeout']
            raise XMLRPCCallError('timed out', method_name='sync', category='timeout', elapsed_seconds=kwargs['timeout'])
        return {'status': 'success'}
    monkeypatch.setattr(client, '_sync_variables_once', sync)
    monkeypatch.setattr(client, '_replace_server_proxy', lambda: None)
    monkeypatch.setattr(client, '_refresh_server_capabilities_after_reconnect', lambda timeout: None)
    result = client._sync_variables({'version': 1}, phase='context.sync', timeout=30)
    assert result['diagnostics']['client_sync_attempts'] == 2
    assert calls[0] == 10
    assert clock[0] < 30


def test_slow_capability_handshake_leaves_budget_for_sync(clock, monkeypatch):
    client = RemoteKeywordClient(sync_config={'sync_retry_jitter': 0})
    calls = []
    def rpc(method, *args, **kwargs):
        calls.append((method, kwargs['timeout']))
        if len(calls) == 1 or method == 'get_server_capabilities':
            clock[0] += kwargs['timeout']
            raise XMLRPCCallError('timed out', method_name=method, category='timeout', elapsed_seconds=kwargs['timeout'])
        return {'status': 'success'}
    monkeypatch.setattr(client, '_rpc_call', rpc)
    result = client._sync_variables({'version': 1}, phase='context.sync', timeout=30)
    assert result['status'] == 'success'
    assert [name for name, _ in calls] == ['sync_variables_from_client', 'get_server_capabilities', 'sync_variables_from_client']
    assert calls[1][1] <= 2
    assert clock[0] < 30


def test_permanent_slow_failure_stays_within_total_budget(clock, monkeypatch):
    client = RemoteKeywordClient(sync_config={'sync_retry_count': 10, 'sync_retry_jitter': 0})
    calls = []
    def sync(variables, **kwargs):
        calls.append(kwargs['timeout'])
        clock[0] += kwargs['timeout']
        raise XMLRPCCallError('timed out', method_name='sync', category='timeout', elapsed_seconds=kwargs['timeout'])
    monkeypatch.setattr(client, '_sync_variables_once', sync)
    monkeypatch.setattr(client, '_replace_server_proxy', lambda: None)
    monkeypatch.setattr(client, '_refresh_server_capabilities_after_reconnect', lambda timeout: None)
    with pytest.raises(XMLRPCCallError):
        client._sync_variables({}, phase='context.sync', timeout=25)
    assert len(calls) == 3
    assert clock[0] <= 25


def test_wait_ready_retries_read_only_rpc_without_sync_or_business_calls(clock, monkeypatch):
    client = RemoteKeywordClient()
    calls = []
    def rpc(method, *args, **kwargs):
        calls.append(method)
        if len(calls) == 1:
            clock[0] += kwargs['timeout']
            raise XMLRPCCallError('timed out', method_name=method, category='timeout', elapsed_seconds=kwargs['timeout'])
        return ['打印']
    monkeypatch.setattr(client, '_rpc_call', rpc)
    assert client.wait_until_ready(timeout=12, probe_timeout=3, interval=1) is True
    assert calls == ['get_keyword_names', 'get_keyword_names']
    assert clock[0] == 4


def test_wait_ready_times_out_with_last_error(clock, monkeypatch):
    client = RemoteKeywordClient()
    def rpc(method, *args, **kwargs):
        clock[0] += kwargs['timeout']
        raise XMLRPCCallError('unreachable', method_name=method, category='timeout', elapsed_seconds=kwargs['timeout'])
    monkeypatch.setattr(client, '_rpc_call', rpc)
    with pytest.raises(TimeoutError, match='远程服务.*未就绪') as error:
        client.wait_until_ready(timeout=7, probe_timeout=3, interval=1)
    assert clock[0] == 7
    assert isinstance(error.value.__cause__, XMLRPCCallError)


def test_wait_ready_does_not_retry_server_fault(clock, monkeypatch):
    client = RemoteKeywordClient()
    rpc = Mock(side_effect=XMLRPCCallError('denied', method_name='get_keyword_names', category='server_fault', elapsed_seconds=0))
    monkeypatch.setattr(client, '_rpc_call', rpc)
    with pytest.raises(XMLRPCCallError):
        client.wait_until_ready(timeout=12)
    assert rpc.call_count == 1


def test_local_wait_keyword_uses_url_without_remote_registration(monkeypatch):
    from pytest_dsl.core.keyword_manager import keyword_manager
    import pytest_dsl.keywords.system_keywords
    wait = Mock(return_value=True)
    monkeypatch.setattr(RemoteKeywordClient, 'wait_until_ready', wait, raising=False)
    result = keyword_manager.execute('等待远程服务就绪', url='http://localhost:8270/', timeout=12, probe_timeout=3, interval=1)
    assert result is True
    wait.assert_called_once_with(timeout=12, probe_timeout=3, interval=1)


@pytest.mark.parametrize('value', [0, -1, float('inf'), float('nan')])
def test_readiness_rejects_invalid_budgets(value):
    client = RemoteKeywordClient()
    with pytest.raises(ValueError):
        client.wait_until_ready(timeout=value)


def test_business_keyword_is_not_retried_after_response_timeout(monkeypatch):
    client = RemoteKeywordClient()
    rpc = Mock(side_effect=XMLRPCCallError('response timeout', method_name='run_keyword', category='timeout', elapsed_seconds=1))
    monkeypatch.setattr(client, '_rpc_call', rpc)
    with pytest.raises(Exception, match='response timeout'):
        client._execute_remote_keyword_with_outcome(name='restart')
    assert rpc.call_count == 1


def test_tcp_connect_timeout_reports_actual_limit_and_reuses_read_timeout():
    transport = TimeoutTransport(timeout=600)
    transport.set_connect_timeout(2)
    connection = transport.make_connection('localhost:8270')
    create = Mock(side_effect=socket.timeout('connection dropped'))
    connection._create_connection = create
    transport.make_connection('localhost:8270')
    with pytest.raises(socket.timeout):
        connection.connect()
    assert create.call_args.args[1] == 2
    assert transport.get_effective_timeout() == 2
    assert transport.get_configured_timeout() == 600


def test_configured_short_connect_timeout_survives_reconnect(monkeypatch):
    client = RemoteKeywordClient(sync_config={'connect_timeout': 1.5})
    def inspect_transport(proxy, method, *args, **kwargs):
        transport = proxy._ServerProxy__transport
        assert transport._connect_timeout == 1.5
        return []
    monkeypatch.setattr('pytest_dsl.core.serialization_utils.XMLRPCSerializer.safe_xmlrpc_call', inspect_transport)
    client._rpc_call('get_keyword_names')
    client._replace_server_proxy()
    client._rpc_call('get_keyword_names')


def test_sync_accepts_numeric_string_budget(monkeypatch):
    client = RemoteKeywordClient()
    sync = Mock(return_value={'status': 'success'})
    monkeypatch.setattr(client, '_sync_variables_once', sync)
    assert client._sync_variables({}, phase='context.sync', timeout='30')['status'] == 'success'
    assert sync.call_args.kwargs['timeout'] == 10


def test_local_readiness_dsl_recovers_then_calls_real_read_only_service(monkeypatch):
    import threading
    from xmlrpc.server import SimpleXMLRPCServer
    from pytest_dsl.core.dsl_executor import DSLExecutor

    try:
        server = SimpleXMLRPCServer(('127.0.0.1', 0), logRequests=False)
    except PermissionError as exc:
        pytest.skip(f'本环境不允许监听本机端口: {exc}')
    calls = []
    def get_names():
        calls.append('get_keyword_names')
        return ['打印']
    server.register_function(get_names, 'get_keyword_names')
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    original_connect = socket.create_connection
    attempts = []
    def transient_connect(address, timeout=None, *args, **kwargs):
        attempts.append(timeout)
        if len(attempts) == 1:
            raise socket.timeout('simulated dropped connection')
        return original_connect(address, timeout, *args, **kwargs)
    monkeypatch.setattr(socket, 'create_connection', transient_connect)
    try:
        url = f'http://127.0.0.1:{server.server_address[1]}/'
        executor = DSLExecutor(enable_hooks=False, enable_tracking=False)
        executor.execute_from_content(
            f'[等待远程服务就绪], 服务地址: "{url}", 超时: 2, 探测超时: 0.1, 间隔: 0.01')
        assert calls == ['get_keyword_names']
        assert attempts == [0.1, 0.1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
