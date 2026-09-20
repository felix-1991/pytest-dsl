"""Request-scoped remote variables must not survive or cross keyword calls."""

from concurrent.futures import ThreadPoolExecutor
import threading
import time
import tempfile
from types import SimpleNamespace

import pytest

from pytest_dsl.core.context import TestContext as Context
from pytest_dsl.core.dsl_executor import DSLExecutor
from pytest_dsl.core.global_context import global_context, GlobalContext
from pytest_dsl.core.keyword_manager import keyword_manager
import pytest_dsl.keywords  # Load builtins before the registry snapshot fixture.
from pytest_dsl.core.variable_providers import setup_context_with_default_providers
from pytest_dsl.core.yaml_vars import yaml_vars
from pytest_dsl.remote.keyword_client import RemoteKeywordClient
from pytest_dsl.remote.keyword_server import RemoteKeywordServer
from pytest_dsl.remote.variable_bridge import (
    get_synced_variable, list_synced_variables, variable_bridge,
)


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, 'tempdir', str(tmp_path))
    monkeypatch.setattr(global_context, '_storage_dir', str(tmp_path))
    monkeypatch.setattr(global_context, '_storage_file', str(tmp_path / 'vars.json'))
    monkeypatch.setattr(global_context, '_lock_file', str(tmp_path / 'vars.lock'))
    monkeypatch.setattr(yaml_vars, '_variables', {})
    monkeypatch.setattr(yaml_vars, '_enable_hooks', False)
    monkeypatch.setattr(keyword_manager, '_keywords', dict(keyword_manager._keywords))


@pytest.fixture
def server():
    instance = RemoteKeywordServer.__new__(RemoteKeywordServer)
    instance.api_key = None
    instance.max_concurrency = 20
    instance._concurrency_limiter = threading.BoundedSemaphore(20)
    instance.shared_variables = {}
    instance._variables_lock = threading.RLock()
    return instance


def invoke(server, name, variables):
    return server.run_keyword_with_metadata(
        name, {}, {'client_request_id': name, 'context_variables': variables})


def test_request_variables_visible_without_mutating_server_containers(server):
    yaml_vars._variables['owner'] = 'server'

    @keyword_manager.register('isolation_read', [])
    def read(context):
        return [context.get('owner'), yaml_vars.get_variable('owner'),
                global_context.get_variable('owner'), get_synced_variable('owner')]

    result = invoke(server, 'isolation_read', {'owner': 'case-A'})
    assert result['status'] == 'PASS'
    assert result['return']['result'] == ['case-A'] * 4
    assert result['return']['captures'] == {}  # Inputs are not echoed as outputs.
    assert server.shared_variables == {}
    assert yaml_vars._variables == {'owner': 'server'}
    assert global_context._load_variables() == {}


def test_concurrent_requests_and_empty_followup_do_not_share_variables(server):
    barrier = threading.Barrier(2)

    @keyword_manager.register('isolation_parallel', [])
    def read(context):
        barrier.wait(timeout=3)
        return [context.get('owner'), yaml_vars.get_variable('owner'),
                global_context.get_variable('owner'), list_synced_variables()]

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(invoke, server, 'isolation_parallel', {'owner': owner})
                   for owner in ('A', 'B')]
        values = [future.result(timeout=5)['return']['result'] for future in futures]
    assert values == [['A', 'A', 'A', {'owner': 'A'}],
                      ['B', 'B', 'B', {'owner': 'B'}]]

    @keyword_manager.register('isolation_empty', [])
    def empty(context):
        return context.has('owner') or yaml_vars.has_variable('owner')

    assert invoke(server, 'isolation_empty', {})['return']['result'] is False
    assert server.shared_variables == {}


def test_failure_releases_request_scope_and_preserves_none(server):
    yaml_vars._variables['nullable'] = 'server-default'

    @keyword_manager.register('isolation_fail', [])
    def fail(context):
        assert context.get('nullable') is None
        assert yaml_vars.has_variable('nullable')
        raise RuntimeError('expected failure')

    result = invoke(server, 'isolation_fail', {'nullable': None})
    assert result['status'] == 'FAIL'
    assert result['error'] == 'expected failure'
    assert yaml_vars.get_variable('nullable') == 'server-default'


def test_installed_legacy_bridge_does_not_leak_into_scoped_call(server):
    variable_bridge.install_bridge({'old_case': 'stale'})
    try:
        @keyword_manager.register('isolation_legacy', [])
        def read(context):
            return [yaml_vars.get_variable('old_case'),
                    global_context.get_variable('old_case'), get_synced_variable('old_case')]

        assert invoke(server, 'isolation_legacy', {})['return']['result'] == [None] * 3
    finally:
        variable_bridge.uninstall_bridge()


def test_global_updates_and_deletions_are_returned_without_server_disk_write(server):
    @keyword_manager.register('isolation_globals', [])
    def mutate(context):
        global_context.set_variable('g_new', 42)
        global_context.delete_variable('g_old')
        return [context.get('g_new'), context.has('g_old')]

    result = invoke(server, 'isolation_globals', {'g_old': 1})
    assert result['return']['result'] == [42, False]
    assert result['variable_effects'] == {'set': {'g_new': 42}, 'deleted': ['g_old']}
    assert global_context._load_variables() == {}


def test_executor_sync_sees_current_globals_and_deletions():
    global_context.set_variable('g_version', 'old')
    executor = DSLExecutor(enable_hooks=False, enable_tracking=False)
    executor.state.set_variable('g_version', 'new')
    assert executor.test_context.get_all_context_variables()['g_version'] == 'new'
    global_context.delete_variable('g_version')
    assert 'g_version' not in executor.test_context.get_all_context_variables()


def test_bulk_context_priority_matches_single_lookup():
    yaml_vars._variables['same'] = 'yaml'
    global_context.set_variable('same', 'global')
    context = Context()
    setup_context_with_default_providers(context)
    assert context.get('same') == context.get_all_context_variables()['same']


def test_realtime_sync_honors_source_flags_and_yaml_allowlist(monkeypatch):
    yaml_vars._variables.update({'allowed': 1, 'excluded': 2})
    global_context.set_variable('g_hidden', 3)
    context = Context()
    setup_context_with_default_providers(context)
    context.set('local', 4)
    client = RemoteKeywordClient(sync_config={'sync_global_vars': False,
                                             'yaml_sync_keys': ['allowed']})
    sent = []
    monkeypatch.setattr(client, '_sync_variables',
                        lambda variables, **kw: sent.append(variables) or {'status': 'success'})
    client._sync_context_variables_before_execution(context)
    assert sent == [{'allowed': 1, 'local': 4}]
    client.sync_config['sync_yaml_vars'] = False
    client._sync_context_variables_before_execution(context)
    assert sent[-1] == {'local': 4}


def test_new_protocol_sends_snapshot_in_business_call_only(monkeypatch):
    client = RemoteKeywordClient()
    client._server_capabilities = {'request_metadata': True, 'request_scoped_context': True}
    context = Context()
    context.set('owner', 'A')
    calls = []

    def rpc(method, *args, **kwargs):
        calls.append((method, args))
        return {'status': 'PASS', 'return': 'ok'}

    monkeypatch.setattr(client, '_rpc_call', rpc)
    assert client._execute_remote_keyword(name='read', context=context) == 'ok'
    assert len(calls) == 1
    assert calls[0][0] == 'run_keyword_with_metadata'
    assert calls[0][1][2]['context_variables'] == {'owner': 'A'}


def test_new_protocol_does_not_send_initial_shared_variables(monkeypatch):
    yaml_vars._variables['config'] = 'value'
    client = RemoteKeywordClient()
    client._server_capabilities = {'request_scoped_context': True}
    calls = []
    monkeypatch.setattr(client, '_sync_variables', lambda *a, **k: calls.append(a))
    client._send_initial_variables()
    assert calls == []


def test_sync_budget_includes_client_lock_wait(monkeypatch):
    client = RemoteKeywordClient()
    entered = threading.Event()
    release = threading.Event()
    def hold():
        with client._get_rpc_lock():
            entered.set()
            release.wait(timeout=2)
    holder = threading.Thread(target=hold)
    holder.start()
    assert entered.wait(timeout=1)
    monkeypatch.setattr(client, '_sync_variables_once', lambda *a, **k: {'status': 'success'})
    try:
        start = time.monotonic()
        with pytest.raises(TimeoutError, match='锁|lock'):
            client._sync_variables({'x': 1}, phase='test', timeout=0.04)
        assert time.monotonic() - start < 0.5
    finally:
        release.set()
        holder.join(timeout=2)


def test_independent_global_stores_do_not_reuse_previous_run():
    first = GlobalContext()
    second = GlobalContext()
    first.set_variable('g_old_run', 'old')
    assert second.get_stored_variables() == {}


def test_explicit_run_store_can_be_shared_by_workers(tmp_path):
    first = GlobalContext(storage_dir=tmp_path / 'run')
    second = GlobalContext(storage_dir=tmp_path / 'run')
    first.set_variable('g_shared', 'value')
    assert second.get_stored_variables() == {'g_shared': 'value'}


def test_client_applies_remote_global_effects(server, monkeypatch):
    @keyword_manager.register('isolation_effects', [])
    def mutate(context):
        global_context.set_variable('g_new', 9)
        global_context.delete_variable('g_old')
        return True

    global_context.set_variable('g_old', 1)
    context = Context()
    setup_context_with_default_providers(context)
    client = RemoteKeywordClient()
    client._server_capabilities = server.get_server_capabilities()
    monkeypatch.setattr(client, '_rpc_call',
                        lambda method, *args, **kw: getattr(server, method)(*args))
    assert client._execute_remote_keyword(name='isolation_effects', context=context) is True
    assert global_context.get_stored_variables() == {'g_new': 9}
    assert server.shared_variables == {}


def test_legacy_sync_does_not_pollute_new_request(server):
    server.sync_variables_from_client({'previous_case': 'stale'})

    @keyword_manager.register('isolation_mixed', [])
    def read(context):
        return context.get('previous_case')

    assert invoke(server, 'isolation_mixed', {})['return']['result'] is None
    assert server.run_keyword('isolation_mixed', {})['return']['result'] == 'stale'


def test_remote_clear_all_includes_nonprefixed_global_names(server, monkeypatch):
    global_context.set_variable('custom_name', 1)
    yaml_vars._variables['configuration'] = 'keep'
    context = Context()
    setup_context_with_default_providers(context)
    client = RemoteKeywordClient()
    client._server_capabilities = server.get_server_capabilities()
    monkeypatch.setattr(client, '_rpc_call',
                        lambda method, *args, **kw: getattr(server, method)(*args))
    client._execute_remote_keyword(name='清除所有全局变量', context=context)
    assert global_context.get_stored_variables() == {}
    assert yaml_vars.get_variable('configuration') == 'keep'


def test_nested_call_keeps_inputs_when_yaml_sync_disabled():
    from pytest_dsl.core.request_variables import RequestVariables
    with RequestVariables({'ordinary': 123, 'custom_global': 456},
                          global_names=['custom_global']):
        context = Context()
        setup_context_with_default_providers(context)
        client = RemoteKeywordClient(sync_config={'sync_yaml_vars': False,
                                                 'sync_global_vars': False})
        assert client._prepare_context_variables(context) == {'ordinary': 123}


def test_snapshot_global_file_read_uses_remaining_sync_budget(monkeypatch):
    from contextlib import contextmanager
    observed = []
    @contextmanager
    def lock(timeout=None):
        observed.append(timeout)
        yield
    monkeypatch.setattr(global_context, '_lock', lock)
    client = RemoteKeywordClient(sync_config={'sync_timeout': 0.05})
    client._prepare_context_variables(None)
    assert observed and all(timeout is not None and 0 < timeout <= 0.05
                            for timeout in observed)


def test_payload_limit_counts_utf8_bytes():
    from pytest_dsl.core.serialization_utils import XMLRPCSerializer
    valid, error = XMLRPCSerializer.validate_xmlrpc_data({'text': '中' * (2 * 1024 * 1024)})
    assert valid is False
    assert '过大' in error


def test_rpc_reports_payload_and_preparation_cost():
    from pytest_dsl.core.serialization_utils import XMLRPCSerializer
    metrics = {}
    proxy = SimpleNamespace(echo=lambda values: values)
    assert XMLRPCSerializer.safe_xmlrpc_call(
        proxy, 'echo', {'x': 'value'}, _rpc_metrics=metrics) == {'x': 'value'}
    assert metrics['payload_bytes'] > 0
    assert metrics['serialization_elapsed_ms'] >= 0


@pytest.mark.parametrize('configured_timeout', ['1', None, 0, -1])
def test_scoped_call_normalizes_sync_timeout(configured_timeout, monkeypatch):
    client = RemoteKeywordClient(sync_config={'sync_timeout': configured_timeout})
    client._server_capabilities = {'request_metadata': True, 'request_scoped_context': True}
    def rpc(method, *args, **kwargs):
        assert isinstance(kwargs['lock_timeout'], float)
        assert kwargs['lock_timeout'] > 0
        return {'status': 'PASS', 'return': 'ok'}
    monkeypatch.setattr(client, '_rpc_call', rpc)
    assert client._execute_remote_keyword(name='read', context=Context()) == 'ok'


@pytest.mark.parametrize('collection_cost,lock_cost,validation_cost', [
    (0, 0, 0.5),       # Serialization alone exceeds the budget.
    (0.5, 0, 0.125),   # Collection and serialization reach the exact deadline.
    (0, 0.5, 0.125),   # Lock waiting must not reset the preparation budget.
])
def test_scoped_call_rejects_expired_budget_before_send(
        collection_cost, lock_cost, validation_cost, monkeypatch):
    from pytest_dsl.core.serialization_utils import XMLRPCCallError, XMLRPCSerializer

    now = [100.0]
    sent = []
    released = []
    client = RemoteKeywordClient(sync_config={'sync_timeout': 1})
    client._server_capabilities = {'request_metadata': True, 'request_scoped_context': True}
    client.server = SimpleNamespace(run_keyword_with_metadata=lambda *args: (
        sent.append(args) or {'status': 'PASS', 'return': 'ok'}))
    monkeypatch.setattr(time, 'monotonic', lambda: now[0])

    def collect(*args, **kwargs):
        now[0] += collection_cost
        return {'owner': 'A'}

    def acquire(timeout):
        assert 0 < timeout <= 1 - collection_cost
        now[0] += lock_cost
        return True

    validate = XMLRPCSerializer.validate_xmlrpc_data

    def slow_validate(*args, **kwargs):
        result = validate(*args, **kwargs)
        now[0] += validation_cost
        return result

    monkeypatch.setattr(client, '_prepare_context_variables', collect)
    monkeypatch.setattr(client, '_rpc_lock', SimpleNamespace(
        acquire=acquire, release=lambda: released.append(True)))
    monkeypatch.setattr(XMLRPCSerializer, 'validate_xmlrpc_data', slow_validate)
    with pytest.raises(Exception, match='同步预算.*未发送请求') as exc_info:
        client._execute_remote_keyword(name='read', context=Context())
    assert isinstance(exc_info.value.__cause__, XMLRPCCallError)
    assert exc_info.value.__cause__.category == 'timeout'
    assert sent == []
    assert released == [True]


@pytest.mark.parametrize('scoped_context', [True, False])
def test_preparation_budget_preserves_keyword_timeout(scoped_context, monkeypatch):
    from pytest_dsl.core.serialization_utils import XMLRPCSerializer
    from pytest_dsl.remote.keyword_client import TimeoutTransport

    now = [100.0]
    client = RemoteKeywordClient(sync_config={'sync_timeout': 1})
    client._server_capabilities = {
        'request_metadata': True, 'request_scoped_context': scoped_context,
    }
    transport = TimeoutTransport(timeout=600)
    calls = []

    def execute(*args):
        assert transport.get_configured_timeout() == 600
        calls.append(args)
        now[0] += 60  # Business execution is allowed to exceed sync_timeout.
        return {'status': 'PASS', 'return': 'ok'}

    client.server = SimpleNamespace(
        run_keyword_with_metadata=execute, _ServerProxy__transport=transport)
    monkeypatch.setattr(time, 'monotonic', lambda: now[0])
    monkeypatch.setattr(client, '_prepare_context_variables', lambda *a, **kw: {})
    monkeypatch.setattr(client, '_sync_context_variables_before_execution',
                        lambda *a, **kw: {})
    validate = XMLRPCSerializer.validate_xmlrpc_data

    def slow_validate(*args, **kwargs):
        result = validate(*args, **kwargs)
        # Legacy keyword calls do not use the new preparation deadline.
        now[0] += 0.125 if scoped_context else 0.5
        return result

    monkeypatch.setattr(XMLRPCSerializer, 'validate_xmlrpc_data', slow_validate)
    assert client._execute_remote_keyword(name='read', context=Context()) == 'ok'
    assert len(calls) == 1
    assert transport.get_configured_timeout() == 600
