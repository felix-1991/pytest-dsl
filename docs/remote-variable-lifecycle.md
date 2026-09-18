# 0.37.0 远程变量生命周期与升级说明

客户端和服务端都升级到 0.37.0 后，通过协议能力
`request_scoped_context` 自动启用请求级上下文。协议版本为 4。

## 变量如何传递

客户端为每次远程关键字构造当前上下文快照，将它放入
`run_keyword_with_metadata` 的 `context_variables` 字段，与关键字参数
一起发送。连接时不再向新服务端写入共享变量；执行前不再额外进行同步 RPC。

服务端通过 `ContextVar` 为本次请求安装独立变量视图。`TestContext`、
`yaml_vars.get_variable/has_variable/get_all_variables`、`global_context`
以及变量桥接辅助函数都使用该视图。输入不会写入服务器 YAML 配置、
共享字典或全局 JSON 文件，也不会作为 captures 原样回传。无论成功或异常，
退出请求都会恢复原上下文。因此没有需要按用例定时回收的远端输入缓存，
客户端崩溃也不会留下这类缓存；空快照不会继承上个用例的变量。

服务端本地 YAML 仍可作为缺失变量的默认配置。显式 `None` 会覆盖同名默认值。
关键字必须通过上述 API 读取变量；直接访问 `_variables` 等内部容器不属于
请求级变量接口。自行启动的后台线程不自动继承请求上下文，应在请求期间
显式传递所需值，不要依赖后台读取已结束的用例上下文。

## 全局变量与返回值

普通变量保留原有本地用例生命周期，teardown 后清理。
外部配置和全局变量不再预先复制成本地缓存，更新、删除后下一次同步读取最新值。
单变量查询与批量收集采用同一提供者优先级。

远端显式调用 `global_context.set_variable/set_variables/delete_variable/clear_all`
产生的变更记录在响应顶层 `variable_effects` 中。客户端将其应用到自己的
全局存储，包括关键字失败但返回了结构化响应的情况。非 `g_` 前缀的显式全局
变量通过 `global_variable_names` 保留来源，清理时不会误删普通配置。
如果连接中断而没有收到响应，这些变更无法确认；业务关键字不会自动重放。

pytest 的全局存储位于本次运行的生命周期临时目录，同次运行的 xdist worker
共享该目录，session teardown 完成后回收。下次运行不会加载旧的
`pytest_dsl_global_vars/global_vars.json`。独立进程默认也使用新临时存储。
嵌入式程序如需明确共享存储，可使用 `GlobalContext(storage_dir=...)`，或在
启动执行前调用单例的 `configure_storage(...)`；不要在执行中切换目录。

## 同步范围与性能

新协议减少一次同步网络往返，避免同步引起的全局文件写入和服务端同步锁竞争。
每次请求仍携带完整的**已筛选快照**，暂不引入远端增量缓存及其版本/删除协议。
较大的上下文可显式缩小范围：

```yaml
remote_servers:
  worker:
    url: http://127.0.0.1:8270/
    sync_config:
      sync_global_vars: true
      sync_yaml_vars: true
      yaml_sync_keys: [http_clients, environment]
      context_sync_keys: [http_clients, environment, token, g_base_url]
      sync_timeout: 30
```

`yaml_sync_keys` 仅筛选 YAML 来源，`context_sync_keys` 筛选最终快照，
未设置时不限制；空列表表示该范围不发送变量。实时路径遵守
`sync_global_vars`、`sync_yaml_vars` 和上述筛选配置。嵌套远程调用的请求输入
作为上下文来源处理，不会因为关闭服务器 YAML 同步而丢失。

XML-RPC 单参数上限仍为 5 MiB，按 UTF-8 **字节数**检查；大字符串不截断。
超限时明确失败。RPC 诊断增加 `payload_bytes`（各参数 XML 校验体大小之和，
不是 HTTP 抓包大小）、`serialization_elapsed_ms` 和 `client_lock_wait_ms`。
`context_sync_server.mode=request` 表示使用请求快照。

同步预算包含客户端同步锁等待，并传递到收集全局变量时的文件锁等待。
预算在处理阶段之间检查；Python 序列化、文件系统调用和业务关键字不是可强制
取消的操作，因此该预算不等于整个远程关键字的硬实时截止时间。

## 旧协议兼容

旧客户端仍能访问旧同步接口。新版服务端不再把这些同步值直接写进 YAML，
而是在旧关键字调用期间以共享字典快照提供变量访问。

新版客户端连接旧服务端时保留旧同步流程。旧流程仍没有用例身份，多个客户端
共用服务器时不能保证隔离，也没有安全的按用例删除方式。要解决跨用例残留、
并发串值，必须同时升级客户端和服务端；升级前让 worker 使用各自的服务进程。

0.36.x 的全局文件不会自动删除，以免影响仍在运行的旧进程；0.37.0 不再隐式读取它。
