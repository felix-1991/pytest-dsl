"""Remote keyword integration for DSL execution."""

import allure

from pytest_dsl.core.execution.exceptions import DSLExecutionError
from pytest_dsl.core.reporting import (
    format_keyword_arguments,
    is_verbose,
    print_keyword_trace,
    preview_value,
)
from pytest_dsl.remote.diagnostics import diagnostics_has_output


def _format_remote_diagnostics(diagnostics, fallback_traceback=None,
                               error_text=None):
    if not isinstance(diagnostics, dict) or not diagnostics:
        return "远程诊断: <无>"

    lines = []
    request_id = diagnostics.get("request_id")
    if request_id:
        lines.append(f"request_id: {request_id}")
    keyword = diagnostics.get("keyword")
    if keyword:
        lines.append(f"keyword: {keyword}")
    status = diagnostics.get("status")
    if status:
        lines.append(f"status: {status}")
    elapsed_ms = diagnostics.get("elapsed_ms")
    if elapsed_ms is not None:
        lines.append(f"elapsed_ms: {elapsed_ms}")

    diagnostic_error = diagnostics.get("error") or error_text
    if diagnostic_error:
        lines.append(f"error: {diagnostic_error}")

    stdout = diagnostics.get("stdout")
    if stdout:
        lines.extend(["", "[stdout]", str(stdout)])

    stderr = diagnostics.get("stderr")
    if stderr:
        lines.extend(["", "[stderr]", str(stderr)])

    logs = diagnostics.get("logs") or []
    if logs:
        lines.extend(["", "[logging]"])
        for item in logs:
            level = item.get("level", "INFO")
            logger = item.get("logger", "root")
            message = item.get("message", "")
            lines.append(f"{level} {logger}: {message}")
            if item.get("traceback"):
                lines.append(str(item["traceback"]))

    traceback_lines = diagnostics.get("traceback") or fallback_traceback or []
    if traceback_lines:
        lines.extend(["", "[traceback]", "".join(traceback_lines)])

    truncated = diagnostics.get("truncated") or {}
    truncated_parts = [
        name for name, is_truncated in truncated.items() if is_truncated
    ]
    if truncated_parts:
        lines.extend(["", f"truncated: {', '.join(truncated_parts)}"])

    return "\n".join(lines)


class RemoteKeywordInvoker:
    """Handles remote keyword imports, calls, assignments, and sync."""

    def __init__(self, executor):
        self.executor = executor

    def handle_import(self, node):
        """处理远程关键字导入"""
        from pytest_dsl.remote.keyword_client import remote_keyword_manager

        executor = self.executor
        remote_info = node.value
        url = executor._replace_variables_in_string(remote_info['url'])
        alias = executor._replace_variables_in_string(remote_info['alias'])

        if alias is None or (isinstance(alias, str) and not alias.strip()):
            raise Exception("远程服务器别名不能为空")
        if not isinstance(alias, str):
            alias = str(alias)

        try:
            success = remote_keyword_manager.register_remote_server(url, alias)
        except Exception as exc:
            print(
                f"远程服务器 {alias} 暂不可用，跳过预连接: {url} ({exc})。"
                f"如果用例执行到 {alias}|[...]，会在调用行失败。"
            )
            return False

        if not success:
            print(
                f"远程服务器 {alias} 暂不可用，跳过预连接: {url}。"
                f"如果用例执行到 {alias}|[...]，会在调用行失败。"
            )
            return False

        print(f"远程服务器已连接: {alias} ({url})")

        allure.attach(
            f"已连接到远程关键字服务器: {url}\n"
            f"别名: {alias}",
            name="远程关键字导入",
            attachment_type=allure.attachment_type.TEXT,
        )
        return True

    def notify_variable_changed(self, var_name, var_value):
        """通知远程服务器变量已发生变化"""
        try:
            from pytest_dsl.core.serialization_utils import XMLRPCSerializer

            variables_to_filter = {var_name: var_value}
            filtered_variables = XMLRPCSerializer.filter_variables(
                variables_to_filter)

            if not filtered_variables:
                return

            from pytest_dsl.remote.keyword_client import remote_keyword_manager

            ok_aliases = []
            for alias, client in remote_keyword_manager.clients.items():
                try:
                    final_variables = client._apply_hook_filter(
                        filtered_variables, variables_to_filter, 'change')

                    if not final_variables:
                        continue

                    result = XMLRPCSerializer.safe_xmlrpc_call(
                        client.server, 'sync_variables_from_client',
                        final_variables, client.api_key)

                    if result.get('status') == 'success':
                        ok_aliases.append(alias)
                    else:
                        error_msg = result.get('error', '未知错误')
                        print(f"❌ 变量 {var_name} 同步到远程服务器 {alias} "
                              f"失败: {error_msg}")

                except Exception as e:
                    print(f"❌ 通知远程服务器 {alias} 变量变化失败: {str(e)}")

            if ok_aliases and is_verbose():
                print(
                    f"🔄 变量 {var_name} 已同步到远程服务器: "
                    f"{', '.join(ok_aliases)}"
                )

        except ImportError:
            pass
        except Exception as e:
            print(f"❌ 通知远程服务器变量变化时发生错误: {str(e)}")

    def execute_keyword_call(self, node):
        """执行远程关键字调用"""
        from pytest_dsl.remote.keyword_client import remote_keyword_manager

        executor = self.executor
        call_info = node.value
        alias = executor._replace_variables_in_string(call_info['alias'])
        if alias is None or (isinstance(alias, str) and not alias.strip()):
            raise Exception("远程调用别名不能为空")
        if not isinstance(alias, str):
            alias = str(alias)
        keyword_name = call_info['keyword']
        line_info = executor._get_line_info(node)

        with allure.step(f"执行远程关键字: {alias}|{keyword_name}"):
            argument_details = ""
            try:
                params = []
                if node.children and node.children[0]:
                    params = node.children[0]

                kwargs = {}
                seen_param_names = set()
                for param in params:
                    param_name = param.value
                    if param_name in seen_param_names:
                        raise DSLExecutionError(
                            f"远程关键字参数错误: {alias}|{keyword_name} 参数重复: "
                            f"{param_name}",
                            line_number=getattr(node, 'line_number', None),
                            node_type=getattr(node, 'type', None),
                        )
                    seen_param_names.add(param_name)
                    param_value = executor.eval_expression(param.children[0])
                    kwargs[param_name] = param_value

                kwargs['context'] = executor.test_context
                argument_details = format_keyword_arguments(kwargs)
                print_keyword_trace(f"{alias}|{keyword_name}", kwargs)

                step_name = kwargs.get(
                    '步骤名称',
                    kwargs.get('step_name', f"{alias}|{keyword_name}")
                )

                with allure.step(step_name):
                    outcome = (
                        remote_keyword_manager
                        .execute_remote_keyword_with_outcome(
                            alias, keyword_name, **kwargs)
                    )
                result = getattr(outcome, "value", outcome)
                diagnostics = getattr(outcome, "diagnostics", {}) or {}
                if is_verbose():
                    details = (f"远程关键字: {alias}|{keyword_name}\n"
                               f"{argument_details}\n"
                               f"远程关键字结果: {result}{line_info}")
                    attachment_name = "远程关键字执行详情"
                else:
                    details = (f"远程关键字: {alias}|{keyword_name}\n"
                               f"{argument_details}\n"
                               f"结果: {preview_value(result)}{line_info}")
                    attachment_name = "远程关键字执行结果"
                allure.attach(
                    details,
                    name=attachment_name,
                    attachment_type=allure.attachment_type.TEXT,
                )
                if diagnostics_has_output(diagnostics):
                    allure.attach(
                        _format_remote_diagnostics(diagnostics),
                        name="远程关键字远端日志",
                        attachment_type=allure.attachment_type.TEXT,
                    )
                return result
            except Exception as e:
                error_details = (f"执行RemoteKeywordCall节点: {str(e)}"
                                 f"{line_info}\n上下文: 执行RemoteKeywordCall节点")
                if argument_details:
                    error_details = f"{error_details}\n{argument_details}"
                diagnostics = getattr(e, "diagnostics", {}) or {}
                request_id = diagnostics.get("request_id")
                if request_id:
                    error_details = f"{error_details}\n远程请求ID: {request_id}"
                allure.attach(
                    error_details,
                    name="DSL执行异常",
                    attachment_type=allure.attachment_type.TEXT,
                )
                if diagnostics_has_output(diagnostics):
                    allure.attach(
                        _format_remote_diagnostics(
                            diagnostics,
                            fallback_traceback=getattr(e, "traceback", []),
                            error_text=str(e)),
                        name="远程关键字失败诊断",
                        attachment_type=allure.attachment_type.TEXT,
                    )
                raise

    def handle_assignment_keyword_call(self, node):
        """处理远程关键字调用赋值"""
        executor = self.executor
        var_name = node.value
        line_info = executor._get_line_info(node)

        with allure.step(f"远程关键字赋值: {var_name}"):
            try:
                remote_keyword_call_node = node.children[0]
                # Call execute_keyword_call directly instead of
                # executor.execute() to avoid a nested dispatch cycle.
                # A nested dispatch would overwrite tracker.current_step
                # and prevent the outer finish_current_step() from
                # working correctly.
                result = self.execute_keyword_call(remote_keyword_call_node)

                if result is None:
                    raise Exception("远程关键字没有返回结果")

                actual_result = self._apply_remote_result_captures(result)
                scope = executor.state.set_variable(var_name, actual_result)
                if scope == "global":
                    allure.attach(
                        f"全局变量: {var_name}\n值: {actual_result}{line_info}",
                        name="远程关键字赋值",
                        attachment_type=allure.attachment_type.TEXT,
                    )
                else:
                    allure.attach(
                        f"变量: {var_name}\n值: {actual_result}{line_info}",
                        name="远程关键字赋值",
                        attachment_type=allure.attachment_type.TEXT,
                    )

                if isinstance(result, dict) and 'captures' in result:
                    captures = result.get('captures', {})
                    for capture_var, capture_value in captures.items():
                        self.notify_variable_changed(capture_var, capture_value)
            except Exception as e:
                error_details = (f"执行AssignmentRemoteKeywordCall节点: {str(e)}"
                                 f"{line_info}\n"
                                 f"上下文: 执行AssignmentRemoteKeywordCall节点")
                allure.attach(
                    error_details,
                    name="DSL执行异常",
                    attachment_type=allure.attachment_type.TEXT,
                )
                raise

    def _apply_remote_result_captures(self, result):
        if not (isinstance(result, dict) and 'result' in result):
            return result

        main_result = result['result']
        captures = result.get('captures', {})
        for capture_var, capture_value in captures.items():
            self.executor.state.set_variable(capture_var, capture_value)

        return main_result
