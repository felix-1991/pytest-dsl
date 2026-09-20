# 远程连接建连超时风险分析

关联堆栈：`windows|dd` 调用 `run_keyword_with_metadata` 失败，目标
`http://10.74.106.160:8270/`。代码基线：`0.37.1`（仓库当前工作区）。

## 一、结论

这次失败**不是网络抖动引发的含糊问题**，也不是序列化或关键字执行的问题。
失败点是 **TCP 建连阶段**，且该路径**没有任何重试**。

关键证据（来自堆栈尾部）：

```
XMLRPCCallError: XML-RPC调用超时
(method=run_keyword_with_metadata, elapsed=5.031s,
 configured_timeout=600.0s, effective_timeout=5.0s, ...)

  socket.connect(sa)  ->  TimeoutError: timed out
  timeout = 5.0, address = ('10.74.106.160', 8270)
```

三个可直接读出的事实：

1. `configured_timeout=600.0s`，但 `effective_timeout=5.0s`。两个数字分别
   反映**读超时**和**建连超时**两层，实际生效的是后者。
2. `elapsed=5.031s`，贴着 5 秒预算失败，说明是**临界失败**，不是彻底不可达。
3. `serialization_elapsed_ms: 16.0` 且 `payload_bytes: 102706`。100KB 请求
   序列化只花 16ms，**瓶颈完全在网络侧**，任何朝序列化优化的方向都是无效的。

## 二、结构性风险

四条风险（会导致失败）+ 一条观察项（正确设计，无需改动）。

### 风险 1：建连超时被写死，且不可配置

`self._connect_timeout` 默认 5.0，`_rpc_call` 在**每次调用前**都用
`sync_config['connect_timeout']` 覆盖 transport 上的建连超时：

- [keyword_client.py:220](../pytest_dsl/remote/keyword_client.py)
- [keyword_client.py:74](../pytest_dsl/remote/keyword_client.py)

跨网段（10.74.x）场景下 5 秒偏紧：一次 SYN 重传（1s + 2s + 4s）就能吃掉
整个预算。用户即便想调大，也没有对外暴露的配置入口说明。

### 风险 2：三层里只有一层真的在重试

| 层 | 位置 | 对"建连超时"是否重试 |
| --- | --- | --- |
| stdlib `Transport.request` | `xmlrpc/client.py:1166` | **否**（有循环，被 errno 白名单挡掉） |
| 变量同步 `_sync_variables_with_retry` | keyword_client.py:371 | **是**（2 次 + 退避 + 重建 proxy） |
| 关键字执行 `run_keyword_with_metadata` | `_rpc_call`，keyword_client.py:195 | **否，零重试** |

**同一个异常，走变量同步会被重试，走关键字执行会直接抛出。** 这是本次
失败最核心的不对称性。

### 风险 3：stdlib 的重试循环兜不住建连超时

`Transport.request` 确实有 `for i in (0, 1)` 循环，但 except 子句是：

```python
except OSError as e:
    if i or e.errno not in (errno.ECONNRESET, errno.ECONNABORTED,
                            errno.EPIPE):
        raise
```

白名单只有 `ECONNRESET / ECONNABORTED / EPIPE`，而**建连超时的 errno 是
`ETIMEDOUT`（110）**，不在名单内，第一次就重新抛出。实测确认：

```
connect timeout  -> connect() called: 1 time(s)  -> NOT retried
ECONNRESET       -> connect() called: 2 time(s)  -> retried
```

所以这个循环的真实语义是"**复用连接已冷死时重连一次**"，从设计上就不管
建连超时。堆栈里 `sock is None` 走到 `connect()`，正好落在它管不着的分支。

> 注：目标环境是 Python 3.12，`TimeoutError` 是 `OSError` 子类，会进入
> `except OSError` 分支，但随即被 errno 判断重新抛出，结论一致。

### 观察 4：失败即丢弃连接，这是正确策略，不是缺陷

> 本条原写作"风险 4（冷建连成本）"，经复核后**下调为观察项**。原表述把一个
> 正确的设计选择当成了问题，详见下方论证。

`_discard_connection()` 在 timeout/network/http/protocol 时无条件
`transport.close()`（serialization_utils.py:557）。**这个策略本身是对的，
而且是更稳定的做法**，理由是 `xmlrpc.client.Transport` 只有**单连接**语义：

- `Transport._connection` 缓存的是**一条** `(host, HTTPConnection)`，
  实测确认（调用两次后 `_connection` 仍是长度 2 的元组，第二个元素是同一个
  `HTTPConnection` 实例）。**这里没有任何连接池**，所以 `close()` 并不存在
  "关掉一条、重新开一条"的额外开销——反正下一次调用也只能复用它。
- 相反,**不复用**才是风险来源。`make_connection` 里的注释已经点明了要害：

  ```python
  # Make sure a timeout is set, even when the connection is reused.
  conn.timeout = timeout
  ```

  一条已经带上 5s socket timeout 的旧连接,如果服务端刚重启、端口换了归属,
  复用它会立刻踩到 `RemoteDisconnected` / `ConnectionResetError`,而这类
  错误在服务端侧看起来就是"客户端发了半个请求"。
- 因此 `close()` 的正确理解是:**只在"这条连接的状态已不可信"时才销毁它**。
  丢弃之后下一次是冷建连,那是**正确性的代价**,不是性能缺陷。

**唯一值得商榷的细节**:`_discard_connection` 位于 `safe_xmlrpc_call` 的
`_raise()` 内,在**持锁期间**执行 close,可能触发 `socket.shutdown()` 的
阻塞(涉及一次 FIN 往返)。这是微秒到毫秒级开销,且被 `try/except` 包住,
**不构成实际问题**,仅作为实现细节记录。

**结论:不需要为此做任何改动。** 建议 2 的重试方案同理——重试时重建连接是
对的(旧连接状态不可信),而重试的收益来自"再试一次握手",不来自"省下握手"。

### 风险 5：`timeout` 与 `connect_timeout` 语义混淆

`_rpc_call` 的 `timeout` 参数语义是"整个 RPC 的预算"，但实际只作用在
**读超时**上——建连超时始终由 `connect_timeout` 单独支配。堆栈里
`timeout=None`（`api_key` 为 `None`，未进入 `set_timeout`），所以
`configured_timeout` 停留在 600.0，而 `effective_timeout` 是 5.0。

这会让排查时误判"给了 600 秒为什么 5 秒就挂了"。

## 三、修改建议

### 建议 1（必做）：把建连超时暴露为可配置项

保留 5.0 作为默认值，但允许通过 `sync_config` 覆盖，并给出建议区间。

**改动点**：`__init__` 的 `default_sync_config`（keyword_client.py:175）已含
`'connect_timeout': 5.0`，无需改结构；只需确认 `_rpc_call` 的读取路径生效
（当前已生效），并在 `docs/remote-variable-lifecycle.md` 或配置文档中补充说明。

### 建议 2（核心）：给关键字执行路径增加"仅建连失败"的重试

这是收益最大的一条，且必须严格限定重试范围。

**关键约束：不能无脑照搬同步路径。**

- **建连超时** → socket 未建立，请求一个字节都没发出 → 重试安全 ✅
- **读超时** → 请求已送达，服务端可能已在执行 → 重试会**重复执行** ❌

两者当前都被归类为 `'timeout'`，无法区分。**精确判据**：`_TimeoutMixin` 的
`connect` 包装函数在 `create_socket` 抛异常的那一刻，`transport._connection`
尚未赋值。据此在 transport 上落一个 `_last_connect_failed` 标志，重试决策
只看这个标志，即可严格锁定在"请求未发出"这一类。

**改动点**：`_TimeoutMixin`（keyword_client.py:55）与 `_rpc_call`
（keyword_client.py:195）。

```python
# _TimeoutMixin.__init__ 增加
self._last_connect_failed = False
self._connect_error = None

# _TimeoutMixin.make_connection 的 connect 包装函数中
def connect(address, timeout=None, *args, **kwargs):
    read_timeout = self._timeout
    connect_timeout = self._connect_timeout
    if read_timeout is not None:
        connect_timeout = min(connect_timeout, read_timeout)
    self._effective_timeout = connect_timeout
    try:
        sock = create_socket(address, connect_timeout, *args, **kwargs)
    except Exception as exc:
        # 关键：此刻尚未取得 socket，请求未发出，重试安全
        self._last_connect_failed = True
        self._connect_error = exc
        raise
    self._last_connect_failed = False
    self._connect_error = None
    sock.settimeout(read_timeout)
    self._effective_timeout = read_timeout
    return sock
```

`_rpc_call` 的重试循环**必须放在已持有 `_rpc_lock` 之后**，与
`_sync_variables`（keyword_client.py:356）保持同一套结构，避免旧的重试
序列盖掉更新的调用：

```python
def _rpc_call(self, method_name, *args, phase=None, timeout=None,
              request_id=None, lock_timeout=None, metrics=None,
              preparation_deadline=None):
    ...
    if not lock.acquire(timeout=max(0.0, float(wait_budget))):
        raise TimeoutError(f'等待远程客户端 RPC 锁超时: {self.alias} ({phase})')
    try:
        deadline = (started_at + timeout) if timeout is not None else None
        settings = self._sync_retry_settings()   # 复用同一套退避参数
        total_attempts = settings['count'] + 1
        last_error = None
        for attempt in range(1, total_attempts + 1):
            if deadline is not None and time.monotonic() >= deadline:
                raise last_error or TimeoutError(
                    f'远程 RPC 预算耗尽: {self.alias} ({phase})')
            remaining = (deadline - time.monotonic()) if deadline is not None else None
            try:
                transport = getattr(self.server, '_ServerProxy__transport', None)
                set_connect_timeout = getattr(transport, 'set_connect_timeout', None)
                if callable(set_connect_timeout):
                    set_connect_timeout(self._positive_timeout(
                        self.sync_config.get('connect_timeout'), 5.0))
                if transport is not None:
                    transport._last_connect_failed = False   # 每轮开始前复位
                return XMLRPCSerializer.safe_xmlrpc_call(
                    self.server, method_name, *args,
                    _rpc_context=';'.join(context_parts),
                    _rpc_timeout=remaining,
                    _rpc_metrics=metrics,
                    _rpc_preparation_deadline=preparation_deadline,
                )
            except XMLRPCCallError as exc:
                last_error = exc
                if (attempt >= total_attempts
                        or not self._is_connect_only_failure(exc)):
                    raise
                # 仅重建连接，不重放已发出的请求
                delay = min(settings['max_interval'],
                            settings['interval'] * settings['backoff'] ** (attempt - 1))
                if settings['jitter']:
                    delay += random.uniform(0.0, settings['jitter'])
                if deadline is not None and deadline - time.monotonic() <= delay:
                    raise
                logger.warning(
                    "远程关键字建连失败，准备重试: %s (%s), attempt=%s/%s, delay=%.3fs",
                    self.alias, phase, attempt, total_attempts, delay)
                if delay > 0:
                    time.sleep(delay)
                self._replace_server_proxy()
    finally:
        lock.release()
```

配套的判定函数（**必须只认"建连失败"，不能扩展成通用的 timeout 判定**）：

```python
def _is_connect_only_failure(self, error):
    """仅当连接从未建立（请求未发出）时返回 True。

    读超时不在此列：请求可能已被服务端执行，重放会造成重复执行。
    """
    if not isinstance(error, XMLRPCCallError):
        return False
    if error.category not in {'timeout', 'network'}:
        return False
    original = getattr(error, 'original_exception', None)
    return (isinstance(original, (socket.timeout, TimeoutError, OSError))
            and getattr(self, '_last_connect_failed', False))
```

`original_exception` 字段名已确认与 `XMLRPCCallError` 定义一致
（serialization_utils.py:16）。`_last_connect_failed` 由 transport 侧维护，
`_rpc_call` 在异常路径读取；**每轮重试开始前显式复位**，避免上一轮的建连失败
污染后续判定。

**重试时为什么要 `_replace_server_proxy()`**：与观察 4 同理——一次失败后旧
连接状态已不可信（可能已被 `_discard_connection` 关闭，也可能停在半开状态），
**必须重建而不是复用**。重试的收益来自"再发起一次握手"，不来自"省下握手"。
参见观察 4 的论证。

### 建议 3（建议做）：把重试基建抽成通用能力

`_is_retryable_sync_error`（keyword_client.py:304）与
`_replace_server_proxy`（keyword_client.py:313）已经写好了。建议抽成
"传输失败恢复"公共层，同步路径与关键字路径共用，只是**重试判据不同**：

| 路径 | 判据 | 原因 |
| --- | --- | --- |
| 变量同步 | `{network, timeout, http}` | 幂等，可安全重放 |
| 关键字执行 | 仅建连失败 | 非幂等，禁止重放 |

### 建议 4（可选）：调用前预热，把建连成本移出关键路径

在 `execute_keyword_call` 之前做一次轻量探活（形如 `wait_until_ready`
的单次探测，见 keyword_client.py:452），把 TCP 握手成本从关键字关键路径上
挪走。适合用例密集调用远程关键字的场景。

## 四、实施优先级

1. **建议 2** —— 收益最大，直接消除本次故障形态。优先落地。
2. **建议 1** —— 改动最小，让用户能自行缓解。可与 2 并行。
3. **建议 3** —— 结构性收敛，建议在 2 稳定后做，避免一次改两处。
4. **建议 4** —— 锦上添花，按需。

## 五、验证要点

实现后需要用测试固定以下边界，建议补充到
`tests/test_remote_context_isolation.py` 或新增连接层测试文件：

1. **建连失败会重试**：注入 `connect()` 抛 `socket.timeout`，断言
   `connect()` 被调用次数 = `sync_retry_count + 1`。
2. **读超时不重试**：注入一个"已发送请求后阻塞"的服务端，断言请求
   只被发送一次（防重复执行的关键回归）。
3. **重试期间连接被重建**：断言 `_replace_server_proxy` 被调用、
   `_server_capabilities` 被清空。
4. **预算不被突破**：给定 `timeout`，断言总耗时不超过该预算加少量余量。
5. **诊断信息可读**：失败时 `client_sync_attempts` / 类别字段能区分
   "建连失败"与"读超时"。

第 2 条是本方案的安全底线，必须覆盖。
