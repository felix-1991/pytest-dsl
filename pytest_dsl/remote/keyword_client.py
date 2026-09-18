import xmlrpc.client
from functools import partial
import logging
import math
import difflib
import os
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from pytest_dsl.core.keyword_manager import keyword_manager, Parameter
from pytest_dsl.remote.log_utils import is_verbose, preview_keys, preview_value

# 配置日志
logger = logging.getLogger(__name__)


@dataclass
class RemoteKeywordCallOutcome:
    value: Any
    diagnostics: Dict[str, Any] = field(default_factory=dict)


class RemoteKeywordExecutionError(Exception):
    """Remote keyword failure with structured server-side diagnostics."""

    def __init__(self, error, alias=None, keyword=None, url=None,
                 timeout=None, traceback_lines=None, diagnostics=None):
        self.error = str(error)
        self.alias = alias
        self.keyword = keyword
        self.url = url
        self.timeout = timeout
        self.traceback = list(traceback_lines or [])
        self.diagnostics = diagnostics or {}

        remote_name = f"{alias}|{keyword}" if alias and keyword else keyword
        location = ""
        if url:
            location = f" ({url}"
            if timeout is not None:
                location += f", timeout={timeout}s"
            location += ")"

        message = f"远程关键字执行失败: {remote_name}{location}: {self.error}"
        traceback_text = "".join(self.traceback)
        if traceback_text:
            message = f"{message}\n{traceback_text}"
        super().__init__(message)


class _TimeoutMixin:
    """为xmlrpc transport注入连接超时。"""

    def __init__(self, *args, timeout=None, connect_timeout=5.0, **kwargs):
        self._timeout = timeout
        self._connect_timeout = connect_timeout
        super().__init__(*args, **kwargs)

    def make_connection(self, host):
        conn = super().make_connection(host)
        # Bound TCP establishment separately from waiting for a keyword result.
        # HTTP and HTTPS both use this factory; leave HTTPS wrapping to stdlib.
        if (hasattr(conn, '_create_connection') and
                getattr(conn, '_dsl_socket_factory', None)
                is not conn._create_connection):
            create_socket = conn._create_connection

            def connect(address, timeout=None, *args, **kwargs):
                read_timeout = self._timeout
                connect_timeout = self._connect_timeout
                if read_timeout is not None:
                    connect_timeout = min(connect_timeout, read_timeout)
                self._effective_timeout = connect_timeout
                sock = create_socket(address, connect_timeout, *args, **kwargs)
                sock.settimeout(read_timeout)
                self._effective_timeout = read_timeout
                return sock

            conn._create_connection = connect
            conn._dsl_socket_factory = connect
        if self._timeout is not None:
            conn.timeout = self._timeout
            # HTTPConnection.timeout does not update an already-open socket.
            # ServerProxy may reuse a persistent connection, so update both.
            if getattr(conn, 'sock', None) is not None:
                conn.sock.settimeout(self._timeout)
        self._effective_timeout = (
            conn.sock.gettimeout()
            if getattr(conn, 'sock', None) is not None
            else conn.timeout
        )
        return conn

    def set_connect_timeout(self, timeout):
        self._connect_timeout = float(timeout)

    def set_timeout(self, timeout):
        self._timeout = float(timeout) if timeout is not None else None
        self._effective_timeout = self._timeout
        connection = getattr(self, '_connection', None)
        conn = connection[1] if connection and len(connection) > 1 else None
        if conn is not None:
            conn.timeout = self._timeout
            if getattr(conn, 'sock', None) is not None:
                conn.sock.settimeout(self._timeout)
                self._effective_timeout = conn.sock.gettimeout()
            else:
                self._effective_timeout = conn.timeout

    def get_configured_timeout(self):
        return self._timeout

    def get_effective_timeout(self):
        return getattr(self, '_effective_timeout', self._timeout)


class TimeoutTransport(_TimeoutMixin, xmlrpc.client.Transport):
    """HTTP transport with timeout support."""


class TimeoutSafeTransport(_TimeoutMixin, xmlrpc.client.SafeTransport):
    """HTTPS transport with timeout support."""


def _create_server_proxy(url, timeout):
    if str(url).lower().startswith('https://'):
        transport = TimeoutSafeTransport(timeout=timeout)
    else:
        transport = TimeoutTransport(timeout=timeout)
    return xmlrpc.client.ServerProxy(url, allow_none=True, transport=transport)


def _is_verbose() -> bool:
    return is_verbose()


def _print_verbose(message: str) -> None:
    if _is_verbose():
        print(message)


class RemoteKeywordClient:
    """远程关键字客户端，用于连接远程关键字服务器并执行关键字"""

    def __init__(self, url='http://localhost:8270/', api_key=None, alias=None,
                 sync_config=None, timeout=None):
        self.url = url
        self.timeout = float(timeout) if timeout is not None else 600.0
        self.server = _create_server_proxy(url, self.timeout)
        self._rpc_lock = threading.RLock()
        self._server_capabilities = {}
        self.keyword_cache = {}
        self.param_mappings = {}  # 存储每个关键字的参数映射
        self.api_key = api_key
        self.alias = alias or url.replace('http://', '').replace(
            'https://', '').split(':')[0]

        # 变量传递配置（简化版）
        default_sync_config = {
            'sync_global_vars': True,   # 连接时传递全局变量（g_开头）
            'sync_yaml_vars': True,     # 连接时传递YAML配置变量
            'yaml_sync_keys': None,     # 指定要同步的YAML键列表，None表示同步所有（除了排除的）
            'yaml_exclude_patterns': [  # 排除包含这些模式的YAML变量
                'private', 'remote_servers'  # 排除远程服务器配置避免循环
            ],
            # 实时同步是关键字执行的一部分；默认失败即阻断，避免远端使用旧变量。
            'realtime_sync_failure_policy': 'fail',
            # 同步应快速完成，不应占用关键字本身的长执行超时。
            'sync_timeout': min(self.timeout, 30.0),
            'sync_attempt_timeout': 10.0,
            'connect_timeout': 5.0,
            # 变量同步是幂等覆盖操作，可以对瞬时传输错误做有限重试。
            # 这里的次数指首次调用失败后的额外重试次数。
            'sync_retry_count': 2,
            'sync_retry_interval': 0.2,
            'sync_retry_backoff': 2.0,
            'sync_retry_max_interval': 1.0,
            'sync_retry_jitter': 0.1,
        }
        self.sync_config = default_sync_config
        if sync_config:
            self.sync_config.update(sync_config)

    def _get_rpc_lock(self):
        lock = getattr(self, '_rpc_lock', None)
        if lock is None:
            lock = threading.RLock()
            self._rpc_lock = lock
        return lock

    def _rpc_call(self, method_name, *args, phase=None, timeout=None,
                  request_id=None, lock_timeout=None, metrics=None):
        """Serialize access to ServerProxy and add call-stage diagnostics."""
        from pytest_dsl.core.serialization_utils import XMLRPCSerializer

        context_parts = [f"alias={self.alias}", f"phase={phase or method_name}"]
        if request_id:
            context_parts.append(f"client_request_id={request_id}")
        started_at = time.monotonic()
        lock = self._get_rpc_lock()
        wait_budget = (lock_timeout if lock_timeout is not None else
                       timeout if timeout is not None else self.timeout)
        if not lock.acquire(timeout=max(0.0, float(wait_budget))):
            raise TimeoutError(f'等待远程客户端 RPC 锁超时: {self.alias} ({phase})')
        try:
            if metrics is not None:
                metrics['client_lock_wait_ms'] = round((time.monotonic() - started_at) * 1000, 3)
            if timeout is not None:
                timeout = max(0.0, timeout - (time.monotonic() - started_at))
                if timeout <= 0:
                    raise TimeoutError(f'远程 RPC 预算耗尽: {self.alias} ({phase})')
            transport = getattr(self.server, '_ServerProxy__transport', None)
            set_connect_timeout = getattr(transport, 'set_connect_timeout', None)
            if callable(set_connect_timeout):
                set_connect_timeout(self._positive_timeout(
                    self.sync_config.get('connect_timeout'), 5.0))
            return XMLRPCSerializer.safe_xmlrpc_call(
                self.server,
                method_name,
                *args,
                _rpc_context=';'.join(context_parts),
                _rpc_timeout=timeout,
                _rpc_metrics=metrics,
            )
        finally:
            lock.release()

    @staticmethod
    def _positive_timeout(value, default):
        try:
            value = float(value)
        except (TypeError, ValueError, OverflowError):
            return default
        return value if math.isfinite(value) and value > 0 else default

    def _sync_variables_once(self, variables, *, phase, timeout=None,
                             request_id=None):
        """Perform one variable-sync RPC using the negotiated API."""
        capabilities = getattr(self, '_server_capabilities', {}) or {}
        if capabilities.get('sync_request_metadata'):
            metadata = {'client_request_id': request_id}
            if timeout is not None:
                metadata['sync_timeout_seconds'] = float(timeout)
            return self._rpc_call(
                'sync_variables_from_client_with_metadata',
                variables,
                metadata,
                self.api_key,
                phase=phase,
                timeout=timeout,
                request_id=request_id,
            )

        # Compatibility path for 0.36.0 and 0.36.1 servers.
        return self._rpc_call(
            'sync_variables_from_client',
            variables,
            self.api_key,
            phase=phase,
            timeout=timeout,
            request_id=request_id,
        )

    @staticmethod
    def _coerce_retry_number(value, default, *, integer=False,
                             minimum=0.0, maximum=None):
        """Normalize optional retry configuration without breaking startup."""
        try:
            converted = int(value) if integer else float(value)
        except (TypeError, ValueError, OverflowError):
            converted = default
        normalized = max(int(minimum) if integer else minimum, converted)
        if maximum is not None:
            normalized = min(maximum, normalized)
        return normalized

    def _sync_retry_settings(self):
        config = self.sync_config
        return {
            'count': self._coerce_retry_number(
                config.get('sync_retry_count', 2), 2,
                integer=True, minimum=0, maximum=10),
            'interval': self._coerce_retry_number(
                config.get('sync_retry_interval', 0.2), 0.2,
                maximum=60.0),
            'backoff': self._coerce_retry_number(
                config.get('sync_retry_backoff', 2.0), 2.0,
                minimum=1.0, maximum=10.0),
            'max_interval': self._coerce_retry_number(
                config.get('sync_retry_max_interval', 1.0), 1.0,
                maximum=60.0),
            'jitter': self._coerce_retry_number(
                config.get('sync_retry_jitter', 0.1), 0.1,
                maximum=10.0),
        }

    @staticmethod
    def _is_retryable_sync_error(error):
        """Only retry transport failures for the idempotent sync endpoint."""
        from pytest_dsl.core.serialization_utils import XMLRPCCallError

        return (
            isinstance(error, XMLRPCCallError)
            and error.category in {'network', 'timeout', 'http'}
        )

    def _replace_server_proxy(self):
        """Drop all transport state and create a fresh XML-RPC proxy."""
        with self._get_rpc_lock():
            old_server = getattr(self, 'server', None)
            transport = getattr(old_server, '_ServerProxy__transport', None)
            close = getattr(transport, 'close', None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass
            self.server = _create_server_proxy(self.url, self.timeout)
            # A restarted endpoint may run another protocol version. Until the
            # post-recovery handshake succeeds, use the universally supported
            # API.
            self._server_capabilities = {}

    def _refresh_server_capabilities_after_reconnect(self, timeout=None):
        """Best-effort protocol handshake after a recovered sync call."""
        try:
            capabilities = self._rpc_call(
                'get_server_capabilities',
                phase='reconnect.server_capabilities',
                timeout=timeout,
            )
            self._server_capabilities = (
                capabilities if isinstance(capabilities, dict) else {})
        except Exception as exc:
            # Legacy servers do not implement this method. A failed optional
            # handshake must not turn an already successful sync into failure.
            self._server_capabilities = {}
            _print_verbose(
                f"远程重连: {self.alias} 能力协商失败，使用兼容协议: {exc}")

    def _sync_variables(self, variables, *, phase, timeout=None,
                        request_id=None):
        """Synchronize variables with bounded transient-failure recovery."""
        # Keep the full retry sequence ordered with other calls made through
        # this client. Otherwise an older timed-out sync could retry after a
        # newer sync and overwrite the newer context.
        started_at = time.monotonic()
        budget = self._positive_timeout(timeout, self.sync_config.get('sync_timeout', 30.0))
        lock = self._get_rpc_lock()
        if not lock.acquire(timeout=budget):
            raise TimeoutError(f'等待远程变量同步锁超时: {self.alias}')
        try:
            remaining = budget - (time.monotonic() - started_at)
            if remaining <= 0:
                raise TimeoutError(f'远程变量同步锁等待已耗尽预算: {self.alias}')
            return self._sync_variables_with_retry(
                variables,
                phase=phase,
                timeout=remaining,
                request_id=request_id,
            )
        finally:
            lock.release()

    def _sync_variables_with_retry(self, variables, *, phase, timeout=None,
                                   request_id=None):
        timeout = float(timeout) if timeout is not None else None
        request_id = request_id or uuid.uuid4().hex
        settings = self._sync_retry_settings()
        total_attempts = settings['count'] + 1
        started_at = time.monotonic()
        deadline = (
            started_at + timeout
            if timeout is not None and timeout >= 0 else None
        )
        reconnected = False
        attempt_timeout = self._positive_timeout(
            self.sync_config.get('sync_attempt_timeout'), 10.0)

        for attempt in range(1, total_attempts + 1):
            if attempt == 1:
                remaining = timeout
            else:
                remaining = (
                    max(0.0, deadline - time.monotonic())
                    if deadline is not None else timeout
                )
            if attempt > 1 and remaining is not None and remaining <= 0:
                raise last_error

            try:
                result = self._sync_variables_once(
                    variables,
                    phase=f'{phase};attempt={attempt}/{total_attempts}',
                    timeout=(min(attempt_timeout, remaining)
                             if remaining is not None else attempt_timeout),
                    request_id=request_id,
                )
                if isinstance(result, dict):
                    result = dict(result)
                    diagnostics = dict(result.get('diagnostics') or {})
                    diagnostics['client_sync_attempts'] = attempt
                    diagnostics['client_reconnected'] = reconnected
                    result['diagnostics'] = diagnostics
                return result
            except Exception as exc:
                last_error = exc
                if (attempt >= total_attempts or
                        not self._is_retryable_sync_error(exc)):
                    raise

                delay = min(
                    settings['max_interval'],
                    settings['interval'] *
                    (settings['backoff'] ** (attempt - 1)),
                )
                if settings['jitter']:
                    delay += random.uniform(0.0, settings['jitter'])

                if deadline is not None:
                    remaining_before_retry = deadline - time.monotonic()
                    if remaining_before_retry <= delay:
                        raise

                logger.warning(
                    "远程变量同步发生瞬时传输错误，准备重试: "
                    "%s (%s), attempt=%s/%s, delay=%.3fs",
                    self.alias, phase, attempt, total_attempts, delay,
                )
                if delay > 0:
                    time.sleep(delay)
                self._replace_server_proxy()
                reconnected = True
                refresh_timeout = (
                    max(0.0, deadline - time.monotonic())
                    if deadline is not None else timeout
                )
                if refresh_timeout is None or refresh_timeout > 0:
                    # Optional negotiation must leave time for the actual sync.
                    self._refresh_server_capabilities_after_reconnect(
                        timeout=(min(2.0, refresh_timeout / 2)
                                 if refresh_timeout is not None else 2.0))

        raise last_error

    def wait_until_ready(self, timeout=120.0, probe_timeout=5.0, interval=1.0):
        """Poll a read-only RPC on the controller, without syncing variables.

        This checks the keyword service, not readiness of the tested business.
        It never registers or executes remote keywords.
        """
        values = [float(timeout), float(probe_timeout), float(interval)]
        if any(not math.isfinite(value) or value <= 0 for value in values):
            raise ValueError('就绪等待的超时和间隔必须为有限正数')
        timeout, probe_timeout, interval = values
        deadline = time.monotonic() + timeout
        last_error = None
        with self._get_rpc_lock():
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(
                        f'远程服务 {self.alias} 在 {timeout:g} 秒内未就绪'
                    ) from last_error
                try:
                    names = self._rpc_call(
                        'get_keyword_names', phase='readiness.probe',
                        timeout=min(probe_timeout, remaining))
                    if not isinstance(names, (list, tuple)):
                        raise ValueError('远程服务返回了无效的关键字列表')
                    return True
                except Exception as exc:
                    if not self._is_retryable_sync_error(exc):
                        raise
                    last_error = exc
                    self._replace_server_proxy()
                    remaining = deadline - time.monotonic()
                    if remaining > 0:
                        time.sleep(min(interval, remaining))

    def connect(self):
        """连接到远程服务器并获取可用关键字"""
        try:
            _print_verbose(f"远程连接: 开始连接 {self.alias} ({self.url})")
            keyword_names = self._rpc_call(
                'get_keyword_names', phase='connect.keyword_names')
            try:
                capabilities = self._rpc_call(
                    'get_server_capabilities',
                    phase='connect.server_capabilities')
                if isinstance(capabilities, dict):
                    self._server_capabilities = capabilities
            except Exception as exc:
                # Older servers do not expose capabilities. Keep the legacy
                # run_keyword signature instead of sending unsupported args.
                self._server_capabilities = {}
                _print_verbose(
                    f"远程连接: {self.alias} 使用兼容协议: {exc}")
            _print_verbose(
                f"远程连接: {self.alias} 加载关键字 {len(keyword_names)} 个")
            for name in keyword_names:
                self._register_remote_keyword(name)

            # 连接时传递变量到远程服务器
            self._send_initial_variables()

            logger.info(f"已连接到远程关键字服务器: {self.url}, 别名: {self.alias}")
            _print_verbose(f"远程连接: 成功 {self.alias} ({self.url})")
            return True
        except Exception as e:
            error_msg = f"连接远程关键字服务器失败: {str(e)}"
            logger.error(error_msg)
            print(
                f"远程连接失败: {self.alias} ({self.url}, timeout={self.timeout}s)，"
                f"原因: {error_msg}"
            )
            return False

    def _register_remote_keyword(self, name):
        """注册远程关键字到本地关键字管理器"""
        # 获取关键字参数信息
        try:
            contract = {}
            try:
                contract = self._rpc_call(
                    'get_keyword_contract', name,
                    phase='connect.keyword_contract')
            except Exception as e:
                _print_verbose(
                    f"远程关键字: {name} 契约获取失败，回退旧接口: {e}")

            param_names = []
            doc = ""
            param_details = []
            returns = None

            if contract:
                param_details = contract.get('parameters', [])
                doc = contract.get('documentation', '')
                returns = contract.get('returns')
                param_names = [param['name'] for param in param_details]
            else:
                param_names = self._rpc_call(
                    'get_keyword_arguments', name,
                    phase='connect.keyword_arguments')
                doc = self._rpc_call(
                    'get_keyword_documentation', name,
                    phase='connect.keyword_documentation')

                # 尝试获取参数详细信息（包括默认值）
                try:
                    param_details = self._rpc_call(
                        'get_keyword_parameter_details', name,
                        phase='connect.keyword_parameter_details')
                except Exception as e:
                    _print_verbose(
                        f"远程关键字: {name} 参数详情获取失败，使用基础参数: {e}")

                for param_name in param_names:
                    if not any(
                        detail.get('name') == param_name
                        for detail in param_details
                    ):
                        param_details.append({
                            'name': param_name,
                            'mapping': param_name,
                            'description': f'远程关键字参数: {param_name}',
                            'default': None
                        })

            _print_verbose(f"远程关键字注册: {name} 参数: {param_details}")

            # 创建参数列表
            parameters = []
            param_mapping = {}  # 为每个关键字创建参数映射

            for param_detail in param_details:
                param_name = param_detail['name']
                param_mapping_name = param_detail.get('mapping', param_name)
                param_desc = param_detail.get('description',
                                              f'远程关键字参数: {param_name}')
                param_default = param_detail.get('default')

                # 确保参数名称正确映射
                parameters.append({
                    'name': param_name,
                    'mapping': param_mapping_name,
                    'description': param_desc,
                    'default': param_default  # 添加默认值支持
                })
                # 添加到参数映射
                param_mapping[param_name] = param_mapping_name

            # 添加步骤名称参数，这是所有关键字都应该有的
            if not any(p['name'] == '步骤名称' for p in parameters):
                parameters.append({
                    'name': '步骤名称',
                    'mapping': 'step_name',
                    'description': '自定义的步骤名称，用于在报告中显示',
                    'default': None
                })
                param_mapping['步骤名称'] = 'step_name'

            # 创建远程关键字执行函数
            remote_func = partial(self._execute_remote_keyword, name=name)
            remote_func.__doc__ = doc

            # 注册到关键字管理器，使用别名前缀
            remote_keyword_name = f"{self.alias}|{name}"
            keyword_manager._keywords[remote_keyword_name] = {
                'func': remote_func,
                'mapping': {p['name']: p['mapping'] for p in parameters},
                'parameters': [Parameter(**p) for p in parameters],
                'defaults': {
                    p['mapping']: p['default'] for p in parameters
                    if p['default'] is not None
                },  # 添加默认值支持
                'returns': returns,
                'remote': True,  # 标记为远程关键字
                'alias': self.alias,
                'original_name': name
            }

            # 缓存关键字信息
            self.keyword_cache[name] = {
                'parameters': param_names,  # 注意这里只缓存原始参数，不包括步骤名称
                'doc': doc,
                'param_details': param_details,  # 缓存详细参数信息
                'returns': returns
            }
            # 保存参数映射
            self.param_mappings[name] = param_mapping

            logger.debug(f"已注册远程关键字: {remote_keyword_name}")
        except Exception as e:
            logger.error(f"注册远程关键字 {name} 失败: {str(e)}")

    def _execute_remote_keyword(self, **kwargs):
        """执行远程关键字"""
        return self._execute_remote_keyword_impl(False, **kwargs)

    def _execute_remote_keyword_with_outcome(self, **kwargs):
        """执行远程关键字并保留远程诊断信息。"""
        return self._execute_remote_keyword_impl(True, **kwargs)

    def _wrap_remote_outcome(self, value, diagnostics, return_outcome):
        if return_outcome:
            return RemoteKeywordCallOutcome(
                value=value,
                diagnostics=diagnostics or {})
        return value

    def _execute_remote_keyword_impl(self, return_outcome=False, **kwargs):
        """执行远程关键字"""
        name = kwargs.pop('name')
        client_request_id = uuid.uuid4().hex
        call_started_at = time.monotonic()

        capabilities = getattr(self, '_server_capabilities', {}) or {}
        scoped_context = capabilities.get('request_scoped_context', False)
        sync_budget = self._positive_timeout(
            getattr(self, 'sync_config', {}).get('sync_timeout'), 30.0)
        request_metadata = {'client_request_id': client_request_id}
        if scoped_context:
            global_names = set()
            variables = self._prepare_context_variables(
                kwargs.get('context'), global_names=global_names)
            request_metadata['context_variables'] = variables
            request_metadata['global_variable_names'] = sorted(global_names.intersection(variables))
            context_sync_result = {'diagnostics': {
                'mode': 'request', 'variable_count': len(variables),
            }}
            if time.monotonic() - call_started_at >= sync_budget:
                raise TimeoutError('收集远程上下文已耗尽同步预算')
        else:
            context_sync_result = self._sync_context_variables_before_execution(
                kwargs.get('context'), request_id=client_request_id)
        context_sync_elapsed_ms = (
            time.monotonic() - call_started_at) * 1000

        # 移除context参数，因为它不能被序列化
        if 'context' in kwargs:
            kwargs.pop('context', None)

        # 移除step_name参数，这是自动添加的，不需要传递给远程服务器
        if 'step_name' in kwargs:
            kwargs.pop('step_name', None)

        # 参数名校验：避免“参数不存在但不报错”的静默问题
        if name in self.param_mappings:
            mapping = self.param_mappings[name]  # 中文参数名 -> 英文参数名
            allowed_cn = set(mapping.keys())
            allowed_en = set(mapping.values())

            invalid = [
                k for k in kwargs.keys()
                if k not in allowed_cn and k not in allowed_en
            ]
            if invalid:
                candidates = list(allowed_cn) + list(allowed_en)
                suggestions = {}
                for bad in invalid:
                    match = difflib.get_close_matches(
                        bad, candidates, n=1, cutoff=0.6)
                    if match:
                        suggestions[bad] = match[0]

                supported_preview = ", ".join(
                    f"{cn}({en})" if cn != en else cn
                    for cn, en in mapping.items()
                )
                parts = [
                    f"远程关键字参数错误: {self.alias}|{name} 不支持参数: "
                    f"{', '.join(invalid)}",
                    f"支持的参数: {supported_preview}",
                ]
                if suggestions:
                    sug_text = ", ".join(
                        f"{k}->{v}" for k, v in suggestions.items()
                    )
                    parts.append(f"你是不是想用: {sug_text}")
                raise Exception(" \n ".join(parts))

        # 调试信息默认关闭，避免输出过多
        _print_verbose(f"远程调用: {self.alias}|{name} 参数: {kwargs}")

        # 创建反向映射字典，用于检查参数是否已经映射
        reverse_mapping = {}

        # 使用动态注册的参数映射
        if name in self.param_mappings:
            param_mapping = self.param_mappings[name]
            _print_verbose(f"远程调用: 使用参数映射 {param_mapping}")
            for cn_name, en_name in param_mapping.items():
                reverse_mapping[en_name] = cn_name
        else:
            # 如果没有任何映射，使用原始参数名
            param_mapping = None
            _print_verbose("远程调用: 未找到参数映射，使用原始参数名")

        # 映射参数名称
        mapped_kwargs = {}
        if param_mapping:
            for k, v in kwargs.items():
                if k in param_mapping:
                    mapped_key = param_mapping[k]
                    mapped_kwargs[mapped_key] = v
                    _print_verbose(f"远程调用: 参数映射 {k}->{mapped_key}={v}")
                else:
                    mapped_kwargs[k] = v
        else:
            mapped_kwargs = kwargs

        # 确保参数名称正确映射
        # 获取关键字的参数信息
        if name in self.keyword_cache:
            param_names = self.keyword_cache[name]['parameters']
            _print_verbose(f"远程调用: {name} 支持参数: {param_names}")
            # 不再显示警告信息，因为参数已经在服务器端正确处理
            # 服务器端会使用默认值或者报错，客户端不需要重复警告

        # 执行远程调用
        # 检查是否需要传递API密钥
        keyword_started_at = time.monotonic()
        rpc_metrics = {}
        try:
            capabilities = getattr(self, '_server_capabilities', {}) or {}
            if capabilities.get('request_metadata'):
                lock_budget = sync_budget
                if scoped_context:
                    lock_budget -= time.monotonic() - call_started_at
                    if lock_budget <= 0:
                        raise TimeoutError('远程上下文准备已耗尽同步预算')
                result = self._rpc_call(
                    'run_keyword_with_metadata',
                    name,
                    mapped_kwargs,
                    request_metadata,
                    self.api_key,
                    phase='keyword.execute', request_id=client_request_id,
                    lock_timeout=lock_budget,
                    metrics=rpc_metrics)
            elif self.api_key:
                result = self._rpc_call(
                    'run_keyword', name, mapped_kwargs, self.api_key,
                    phase='keyword.execute', request_id=client_request_id)
            else:
                result = self._rpc_call(
                    'run_keyword', name, mapped_kwargs,
                    phase='keyword.execute', request_id=client_request_id)
        except Exception as e:
            raise Exception(
                "远程关键字调用失败: "
                f"{self.alias}|{name} ({self.url}, "
                f"client_request_id={client_request_id}, "
                f"context_sync_elapsed="
                f"{context_sync_elapsed_ms / 1000:.3f}s): {e}"
            ) from e

        _print_verbose(f"远程调用: 结果 {result}")

        if scoped_context:
            self._apply_variable_effects(result.get('variable_effects') or {})

        diagnostics = (
            dict(result.get('diagnostics', {}) or {})
            if isinstance(result, dict) else {}
        )
        diagnostics['client_rpc'] = {
            **rpc_metrics,
            'client_request_id': client_request_id,
            'context_sync_elapsed_ms': round(context_sync_elapsed_ms, 3),
            'keyword_rpc_elapsed_ms': round(
                (time.monotonic() - keyword_started_at) * 1000, 3),
            'total_elapsed_ms': round(
                (time.monotonic() - call_started_at) * 1000, 3),
        }
        if isinstance(context_sync_result, dict):
            sync_diagnostics = context_sync_result.get('diagnostics')
            if isinstance(sync_diagnostics, dict):
                diagnostics['client_rpc'][
                    'context_sync_server'] = sync_diagnostics

        if result['status'] == 'PASS':
            return_data = result['return']

            # 处理新的返回格式
            if isinstance(return_data, dict):
                # 处理捕获的变量 - 这里需要访问本地上下文
                if 'captures' in return_data and return_data['captures']:
                    _print_verbose(
                        f"远程返回: 捕获变量 {return_data['captures']}")

                # 处理会话状态
                if ('session_state' in return_data and
                        return_data['session_state']):
                    _print_verbose(
                        f"远程返回: 会话状态 {return_data['session_state']}")

                # 处理响应数据
                if 'response' in return_data and return_data['response']:
                    print("远程关键字响应数据: 已接收")

                # 使用通用的返回处理机制
                # 检查是否有嵌套的新格式数据
                if 'result' in return_data and isinstance(return_data['result'], dict):
                    nested_data = return_data['result']
                    if 'side_effects' in nested_data:
                        # 处理嵌套的新格式数据
                        processed_result = self._process_return_data(nested_data)
                        return self._wrap_remote_outcome(
                            processed_result, diagnostics, return_outcome)

                # 处理原始格式数据
                processed_result = self._process_return_data(return_data)
                return self._wrap_remote_outcome(
                    processed_result, diagnostics, return_outcome)

            return self._wrap_remote_outcome(
                return_data, diagnostics, return_outcome)
        else:
            error_msg = result.get('error', '未知错误')
            traceback_lines = result.get('traceback', [])
            raise RemoteKeywordExecutionError(
                error_msg,
                alias=self.alias,
                keyword=name,
                url=self.url,
                timeout=self.timeout,
                traceback_lines=traceback_lines,
                diagnostics=diagnostics)

    def _apply_variable_effects(self, effects):
        """Explicit remote global writes belong to the caller's run."""
        from pytest_dsl.core.global_context import global_context
        global_context.set_variables(effects.get('set') or {}, attach=False)
        for name in effects.get('deleted') or []:
            global_context.delete_variable(name)

    def _process_return_data(self, return_data):
        """通用的返回数据处理方法

        Args:
            return_data: 远程关键字返回的数据

        Returns:
            处理后的返回数据
        """
        # 使用返回处理器注册表处理数据
        from .return_handlers import return_handler_registry

        processed_data = return_handler_registry.process(return_data)

        # 如果处理后的数据包含side_effects，直接处理副作用
        if isinstance(processed_data, dict) and 'side_effects' in processed_data:
            self._handle_side_effects(processed_data)
            # 返回主要结果
            return processed_data.get('result')
        else:
            return processed_data

    def _handle_side_effects(self, processed_data):
        """处理副作用

        Args:
            processed_data: 包含side_effects的处理后数据
        """
        side_effects = processed_data.get('side_effects', {})

        # 处理变量注入
        variables = side_effects.get('variables', {})
        if variables:
            _print_verbose(f"远程返回: 注入变量 {variables}")
            self._inject_variables(variables)

        # 处理上下文更新
        context_updates = side_effects.get('context_updates', {})
        if context_updates:
            _print_verbose(f"远程返回: 上下文更新 {context_updates}")
            self._update_context(context_updates)

    def _inject_variables(self, variables):
        """实际执行变量注入

        Args:
            variables: 要注入的变量字典
        """
        try:
            # 导入必要的模块
            from pytest_dsl.core.global_context import global_context

            # 获取当前执行器实例（如果存在）
            current_executor = self._get_current_executor()

            global_var_names = []
            local_var_names = []
            fallback_global_var_names = []

            for var_name, var_value in variables.items():
                if var_name.startswith('g_'):
                    # 全局变量
                    global_context.set_variable(var_name, var_value)
                    global_var_names.append(var_name)
                    _print_verbose(
                        f"✅ 注入全局变量: {var_name} = {preview_value(var_value)}"
                    )
                else:
                    # 本地变量
                    if current_executor:
                        current_executor.variable_replacer.local_variables[var_name] = var_value
                        current_executor.test_context.set(var_name, var_value)
                        local_var_names.append(var_name)
                        _print_verbose(
                            f"✅ 注入本地变量: {var_name} = {preview_value(var_value)}"
                        )
                    else:
                        # 如果没有执行器，至少设置为全局变量
                        global_context.set_variable(var_name, var_value)
                        fallback_global_var_names.append(var_name)
                        _print_verbose(
                            "⚠️  注入为全局变量（无执行器上下文）: "
                            f"{var_name} = {preview_value(var_value)}"
                        )

            # 默认输出摘要，避免变量过多刷屏
            total = len(variables)
            parts = [f"✅ 变量注入完成: {total} 项"]
            if global_var_names:
                parts.append(
                    f"global={len(global_var_names)} [{', '.join(global_var_names[:10])}"
                    f"{'...' if len(global_var_names) > 10 else ''}]"
                )
            if local_var_names:
                parts.append(
                    f"local={len(local_var_names)} [{', '.join(local_var_names[:10])}"
                    f"{'...' if len(local_var_names) > 10 else ''}]"
                )
            if fallback_global_var_names:
                parts.append(
                    f"fallback_global={len(fallback_global_var_names)} "
                    f"[{', '.join(fallback_global_var_names[:10])}"
                    f"{'...' if len(fallback_global_var_names) > 10 else ''}]"
                )
            print(" | ".join(parts))

        except Exception as e:
            print(f"❌ 变量注入失败: {str(e)}")

    def _update_context(self, context_updates):
        """实际执行上下文更新

        Args:
            context_updates: 要更新的上下文信息
        """
        try:
            # 处理会话状态更新
            if 'session_state' in context_updates:
                session_state = context_updates['session_state']
                _print_verbose(f"✅ 更新会话状态: {preview_value(session_state)}")
                # 这里可以根据需要更新会话管理器的状态

            # 处理响应数据更新
            if 'response' in context_updates:
                _print_verbose("✅ 更新响应数据: 已接收响应数据")
                # 可以将响应数据存储到特定位置

            # 处理其他上下文更新
            for key, value in context_updates.items():
                if key not in ['session_state', 'response']:
                    _print_verbose(f"✅ 更新上下文: {key} = {preview_value(value)}")
                    # 可以根据需要处理其他类型的上下文更新

            # 默认输出摘要，避免上下文过大刷屏
            keys_preview = preview_keys(context_updates, max_keys=20)
            print(
                "✅ 上下文更新完成: "
                f"keys={len(context_updates)} [{keys_preview}]"
            )

        except Exception as e:
            print(f"❌ 上下文更新失败: {str(e)}")

    def _get_current_executor(self):
        """获取当前的DSL执行器实例

        Returns:
            当前执行器实例或None
        """
        try:
            # 通过线程本地存储获取当前执行器
            import threading

            # 检查是否有线程本地的执行器
            if hasattr(threading.current_thread(), 'dsl_executor'):
                return threading.current_thread().dsl_executor

            return None

        except Exception:
            return None

    def _prepare_context_variables(self, context, *, global_names=None):
        """Apply the same source selection to every per-call snapshot."""
        from pytest_dsl.core.context import TestContext
        from pytest_dsl.core.variable_providers import (
            GlobalContextVariableProvider, YAMLVariableProvider,
            setup_context_with_default_providers,
        )
        from pytest_dsl.core.serialization_utils import XMLRPCSerializer
        from pytest_dsl.core.request_variables import current_request_variables

        deadline = time.monotonic() + self._positive_timeout(
            self.sync_config.get('sync_timeout'), 30.0)
        known_globals = global_names if global_names is not None else set()
        request = current_request_variables()
        if request is not None:
            known_globals.update(request.global_names)

        if context is None:
            context = TestContext()
            setup_context_with_default_providers(context)
        values = dict(self.sync_config.get('custom_variables') or {})
        providers = getattr(context, '_external_providers', None)
        if isinstance(providers, list):
            for provider in reversed(providers):
                if isinstance(provider, GlobalContextVariableProvider):
                    if not self.sync_config.get('sync_global_vars', True):
                        continue
                if isinstance(provider, YAMLVariableProvider):
                    if not self.sync_config.get('sync_yaml_vars', True):
                        continue
                if not hasattr(provider, 'get_all_variables'):
                    continue
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('收集远程上下文已耗尽同步预算')
                if isinstance(provider, GlobalContextVariableProvider):
                    external = provider.get_all_variables(lock_timeout=remaining)
                    known_globals.update(external)
                else:
                    external = provider.get_all_variables()
                if isinstance(provider, YAMLVariableProvider):
                    keys = self.sync_config.get('yaml_sync_keys')
                    if keys is not None:
                        external = {k: v for k, v in external.items() if k in keys}
                values.update(external)
            values.update(context.get_local_variables())
        else:
            values.update(context.get_all_context_variables())
        keys = self.sync_config.get('context_sync_keys')
        if keys is not None:
            values = {k: v for k, v in values.items() if k in keys}
        if not self.sync_config.get('sync_global_vars', True):
            values = {k: v for k, v in values.items()
                      if not k.startswith('g_') and k not in known_globals}
        patterns = self.sync_config.get('yaml_exclude_patterns', [])
        filtered = XMLRPCSerializer.filter_variables(values, patterns)
        filtered = self._apply_hook_filter(filtered, values, 'realtime')
        filtered = XMLRPCSerializer.filter_variables(filtered, patterns)
        if time.monotonic() >= deadline:
            raise TimeoutError('序列化远程上下文已耗尽同步预算')
        return filtered

    def _sync_context_variables_before_execution(self, context,
                                                  request_id=None):
        """在执行远程关键字前同步最新的上下文变量

        Args:
            context: TestContext实例，如果为None则跳过同步
        """
        if context is None:
            return

        try:
            started_at = time.monotonic()
            variables_to_sync = self._prepare_context_variables(context)

            if variables_to_sync:
                # 调用远程服务器的变量同步接口
                try:
                    sync_timeout = self._positive_timeout(
                        self.sync_config.get('sync_timeout'), 30.0)
                    sync_timeout -= time.monotonic() - started_at
                    if sync_timeout <= 0:
                        raise TimeoutError('收集远程上下文已耗尽同步预算')
                    result = self._sync_variables(
                        variables_to_sync,
                        phase='context.sync',
                        timeout=sync_timeout,
                        request_id=request_id,
                    )
                    if result.get('status') == 'success':
                        _print_verbose(
                            f"✅ 同步变量 {len(variables_to_sync)} 项 -> {self.alias}"
                        )
                    else:
                        error_code = result.get('error_code')
                        server_diagnostics = result.get('diagnostics') or {}
                        diagnostic_parts = []
                        if error_code:
                            diagnostic_parts.append(f"error_code={error_code}")
                        for key in ('request_id', 'stage', 'elapsed_ms',
                                    'lock_wait_ms', 'global_write_ms'):
                            value = server_diagnostics.get(key)
                            if value not in (None, ''):
                                diagnostic_parts.append(f"{key}={value}")
                        diagnostic_text = (
                            f" ({', '.join(diagnostic_parts)})"
                            if diagnostic_parts else '')
                        raise RuntimeError(
                            f"远程变量同步失败: {self.alias}: "
                            f"{result.get('error', '未知错误')}"
                            f"{diagnostic_text}"
                        )
                except Exception as e:
                    policy = self.sync_config.get(
                        'realtime_sync_failure_policy', 'fail')
                    if str(policy).lower() == 'warn':
                        print(f"❌ 调用远程变量同步接口失败: {str(e)}")
                        return False
                    raise RuntimeError(
                        f"执行远程关键字前同步上下文失败: {e}"
                    ) from e
            else:
                _print_verbose("远程同步: 没有需要同步的变量")
            return result if variables_to_sync else True

        except Exception as e:
            if str(self.sync_config.get(
                    'realtime_sync_failure_policy', 'fail')).lower() != 'warn':
                raise
            logger.warning(f"实时变量同步失败: {str(e)}")
            print(f"❌ 实时变量同步失败: {str(e)}")
            return False

    def _collect_context_variables(self, context):
        """从TestContext收集所有变量（包括外部提供者变量）

        Args:
            context: TestContext实例

        Returns:
            dict: 包含所有上下文变量的字典
        """
        if context is None:
            return {}

        try:
            # 使用新的get_all_context_variables方法
            return context.get_all_context_variables()
        except Exception as e:
            logger.warning(f"收集上下文变量失败: {str(e)}")
            return {}

    def _send_initial_variables(self):
        """连接时发送初始变量到远程服务器"""
        if (getattr(self, '_server_capabilities', {}) or {}).get('request_scoped_context'):
            return
        try:
            variables_to_send = {}

            # 收集全局变量
            if self.sync_config.get('sync_global_vars', True):
                variables_to_send.update(self._collect_global_variables())

            # 收集YAML变量
            if self.sync_config.get('sync_yaml_vars', True):
                variables_to_send.update(self._collect_yaml_variables())

            if variables_to_send:
                # 使用统一的序列化工具进行变量过滤和转换
                from pytest_dsl.core.serialization_utils import (
                    XMLRPCSerializer
                )
                serializable_variables = XMLRPCSerializer.filter_variables(
                    variables_to_send)

                # 注意：Hook过滤已在各个变量收集方法中完成，此处不再重复过滤

                if serializable_variables:
                    try:
                        result = self._sync_variables(
                            serializable_variables,
                            phase='connect.initial_sync',
                            timeout=self.sync_config.get('sync_timeout'),
                        )

                        if result.get('status') == 'success':
                            _print_verbose(
                                f"成功传递 {len(serializable_variables)} "
                                f"个变量到远程服务器 {self.alias}"
                            )
                        else:
                            print(f"传递变量到远程服务器失败: "
                                  f"{result.get('error', '未知错误')}")
                    except Exception as e:
                        print(f"调用远程变量接口失败: {str(e)}")
                else:
                    _print_verbose("没有可序列化的变量需要传递")
            else:
                _print_verbose("没有需要传递的变量")

        except Exception as e:
            logger.warning(f"初始变量传递失败: {str(e)}")
            print(f"初始变量传递失败: {str(e)}")

    def _collect_global_variables(self):
        """收集全局变量"""
        from pytest_dsl.core.global_context import global_context
        variables = {}

        # 获取所有全局变量（包括g_开头的变量）
        try:
            # 这里需要访问全局上下文的内部存储
            # 由于GlobalContext使用文件存储，我们需要直接读取
            import json
            import os
            storage_file = global_context._storage_file

            if os.path.exists(storage_file):
                with global_context._lock():
                    with open(storage_file, 'r', encoding='utf-8') as f:
                        stored_vars = json.load(f)
                        # 只同步g_开头的全局变量
                        global_vars = {
                            name: value for name, value in stored_vars.items() 
                            if name.startswith('g_')
                        }
                        if global_vars:
                            from pytest_dsl.core.serialization_utils import (
                                XMLRPCSerializer
                            )
                            filtered_global_vars = XMLRPCSerializer.filter_variables(
                                global_vars)

                            # 应用Hook过滤
                            filtered_global_vars = self._apply_hook_filter(
                                filtered_global_vars, global_vars, 'initial', 'global')

                            variables.update(filtered_global_vars)
        except Exception as e:
            logger.warning(f"收集全局变量失败: {str(e)}")

        return variables

    def _collect_yaml_variables(self):
        """收集YAML配置变量"""
        from pytest_dsl.core.yaml_vars import yaml_vars
        variables = {}

        try:
            # 获取所有YAML变量
            yaml_data = yaml_vars._variables
            if yaml_data:
                _print_verbose(f"客户端YAML变量总数: {len(yaml_data)}")

                # 检查同步配置中是否指定了特定的键
                sync_keys = self.sync_config.get('yaml_sync_keys', None)
                exclude_patterns = self.sync_config.get(
                    'yaml_exclude_patterns', [
                        'password', 'secret', 'token', 'credential', 'auth',
                        'private', 'remote_servers'  # 排除远程服务器配置避免循环
                    ]
                )

                if sync_keys:
                    # 如果指定了特定键，只传递这些键，直接使用原始变量名
                    specific_vars = {
                        key: yaml_data[key] for key in sync_keys 
                        if key in yaml_data
                    }
                    if specific_vars:
                        from pytest_dsl.core.serialization_utils import (
                            XMLRPCSerializer
                        )
                        filtered_specific_vars = XMLRPCSerializer.filter_variables(
                            specific_vars)
                        variables.update(filtered_specific_vars)
                        # 只输出摘要，避免变量过多刷屏
                        _print_verbose(
                            "将同步指定YAML变量: "
                            f"{len(filtered_specific_vars)} 项 "
                            f"[{preview_keys(filtered_specific_vars)}]"
                        )
                else:
                    # 传递所有YAML变量，但排除敏感信息
                    from pytest_dsl.core.serialization_utils import (
                        XMLRPCSerializer
                    )
                    filtered_yaml_vars = XMLRPCSerializer.filter_variables(
                        yaml_data, exclude_patterns)

                    # 应用Hook过滤
                    filtered_yaml_vars = self._apply_hook_filter(
                        filtered_yaml_vars, yaml_data, 'initial', 'yaml')

                    variables.update(filtered_yaml_vars)
                    # 只输出摘要，避免变量过多刷屏
                    _print_verbose(
                        "将同步YAML变量: "
                        f"{len(filtered_yaml_vars)} 项 "
                        f"[{preview_keys(filtered_yaml_vars)}]"
                    )

        except Exception as e:
            logger.warning(f"收集YAML变量失败: {str(e)}")
            print(f"收集YAML变量失败: {str(e)}")

        return variables

    def _apply_hook_filter(self, variables, original_variables, sync_type, variable_source='context'):
        """应用Hook过滤

        Args:
            variables: 经过基础过滤的变量字典
            original_variables: 原始变量字典
            sync_type: 同步类型 ('initial', 'realtime', 'change')
            variable_source: 变量来源 ('context', 'global', 'yaml')

        Returns:
            经过Hook过滤的变量字典
        """
        try:
            from pytest_dsl.core.hook_manager import hook_manager

            # 构建同步上下文
            sync_context = {
                'server_alias': self.alias,
                'server_url': self.url,
                'sync_type': sync_type,
                'variable_source': variable_source,
            }

            # 调用所有注册的过滤hook
            hook_results = hook_manager.pm.hook.dsl_filter_sync_variables(
                variables=variables, sync_context=sync_context)

            for filtered_result in hook_results:
                if filtered_result is not None:
                    variables = filtered_result
                    _print_verbose(
                        f"远程同步: Hook过滤后变量 {len(variables)} 项 "
                        f"(服务器: {self.alias}, 类型: {sync_type})"
                    )

        except Exception as e:
            _print_verbose(f"远程同步: Hook过滤失败，使用原始过滤结果: {e}")

        return variables


# 远程关键字客户端管理器
class RemoteKeywordManager:
    """远程关键字客户端管理器，管理多个远程服务器连接"""

    def __init__(self):
        self.clients = {}  # 别名 -> 客户端实例

    def register_remote_server(self, url, alias, api_key=None,
                               sync_config=None, timeout=None):
        """注册远程关键字服务器

        Args:
            url: 服务器URL
            alias: 服务器别名
            api_key: API密钥(可选)
            sync_config: 变量同步配置(可选)
            timeout: XML-RPC调用超时时间(秒)

        Returns:
            bool: 是否成功连接
        """
        _print_verbose(f"远程连接: 注册服务器 {alias} ({url})")
        client = RemoteKeywordClient(url=url, api_key=api_key, alias=alias,
                                     sync_config=sync_config, timeout=timeout)
        success = client.connect()

        if success:
            _print_verbose(f"远程连接: 注册完成 {alias} ({url})")
            self.clients[alias] = client
        else:
            _print_verbose(f"远程连接: 注册失败 {alias} ({url})")

        return success

    def get_client(self, alias):
        """获取指定别名的客户端实例"""
        return self.clients.get(alias)

    def execute_remote_keyword(self, alias, keyword_name, **kwargs):
        """执行远程关键字

        Args:
            alias: 服务器别名
            keyword_name: 关键字名称
            **kwargs: 关键字参数

        Returns:
            执行结果
        """
        client = self.get_client(alias)
        if not client:
            raise Exception(
                f"未找到别名为 {alias} 的远程服务器。"
                "请确认运行命令已加载包含 remote_servers 的YAML配置，"
                "或 @remote 预连接成功；"
                f"当前调用: {alias}|[{keyword_name}]"
            )

        return client._execute_remote_keyword(name=keyword_name, **kwargs)

    def execute_remote_keyword_with_outcome(self, alias, keyword_name, **kwargs):
        """执行远程关键字并返回业务结果和远程诊断信息。"""
        client = self.get_client(alias)
        if not client:
            raise Exception(
                f"未找到别名为 {alias} 的远程服务器。"
                "请确认运行命令已加载包含 remote_servers 的YAML配置，"
                "或 @remote 预连接成功；"
                f"当前调用: {alias}|[{keyword_name}]"
            )

        return client._execute_remote_keyword_with_outcome(
            name=keyword_name, **kwargs)


# 创建全局远程关键字管理器实例
remote_keyword_manager = RemoteKeywordManager()
