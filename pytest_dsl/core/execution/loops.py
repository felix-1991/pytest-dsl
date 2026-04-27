"""Loop statement handlers for DSL execution."""

import allure

from pytest_dsl.core.execution.exceptions import (
    BreakException,
    ContinueException,
    ReturnException,
)


class LoopHandlers:
    """Executes DSL loop nodes for a DSL executor."""

    def __init__(self, executor):
        self.executor = executor

    def handle_for_loop(self, node):
        """处理传统for循环（向后兼容）"""
        return self.handle_for_range_loop(node)

    def handle_for_range_loop(self, node):
        """处理range类型的for循环: for i in range(0, 5) do ... end"""
        executor = self.executor
        step_name = f"执行范围循环: {node.value}"
        line_info = executor._get_line_info(node)

        with allure.step(step_name):
            try:
                var_name = node.value
                start_range = executor.eval_expression(node.children[0])
                end_range = executor.eval_expression(node.children[1])
                loop_items = list(range(start_range, end_range))

                allure.attach(
                    f"循环变量: {var_name}\n循环范围: {start_range} 到 "
                    f"{end_range}\n循环项: {loop_items}{line_info}",
                    name="范围循环信息",
                    attachment_type=allure.attachment_type.TEXT,
                )

                statements_node = node.children[2]

                for item in loop_items:
                    executor.state.set_local_variable(var_name, item)
                    executor._notify_remote_servers_variable_changed(
                        var_name, item)

                    try:
                        self._execute_loop_iteration(
                            statements_node=statements_node,
                            line_info=line_info,
                            node_type="ForRangeLoop",
                            step_label=f"{var_name} = {item}",
                            break_message=(
                                f"在 {var_name} = {item} 时遇到break语句，"
                                f"退出循环"
                            ),
                            continue_message=(
                                f"在 {var_name} = {item} 时遇到continue语句，"
                                f"跳过本次循环"
                            ),
                            return_message=(
                                f"在 {var_name} = {item} 时遇到return语句，"
                                f"退出函数"
                            ),
                        )
                    except _LoopBreak:
                        break
            except (BreakException, ContinueException, ReturnException):
                raise
            except Exception as e:
                self._attach_loop_error("ForRangeLoop", str(e), line_info)
                raise

    def handle_for_item_loop(self, node):
        """处理单变量遍历循环: for item in array do ... end"""
        executor = self.executor
        step_name = f"执行遍历循环: {node.value}"
        line_info = executor._get_line_info(node)

        with allure.step(step_name):
            try:
                var_name = node.value
                collection = executor.eval_expression(node.children[0])

                if not hasattr(collection, '__iter__'):
                    raise TypeError(
                        f"对象不可迭代: {type(collection).__name__}")

                loop_items = (
                    list(collection) if not isinstance(collection, list)
                    else collection
                )

                allure.attach(
                    f"循环变量: {var_name}\n遍历集合: {collection}\n集合类型: "
                    f"{type(collection).__name__}\n集合长度: "
                    f"{len(loop_items)}{line_info}",
                    name="遍历循环信息",
                    attachment_type=allure.attachment_type.TEXT,
                )

                statements_node = node.children[1]

                for item in collection:
                    executor.state.set_local_variable(var_name, item)
                    executor._notify_remote_servers_variable_changed(
                        var_name, item)

                    try:
                        self._execute_loop_iteration(
                            statements_node=statements_node,
                            line_info=line_info,
                            node_type="ForItemLoop",
                            step_label=f"{var_name} = {item}",
                            break_message=(
                                f"在 {var_name} = {item} 时遇到break语句，"
                                f"退出循环"
                            ),
                            continue_message=(
                                f"在 {var_name} = {item} 时遇到continue语句，"
                                f"跳过本次循环"
                            ),
                            return_message=(
                                f"在 {var_name} = {item} 时遇到return语句，"
                                f"退出函数"
                            ),
                        )
                    except _LoopBreak:
                        break
            except (BreakException, ContinueException, ReturnException):
                raise
            except Exception as e:
                self._attach_loop_error("ForItemLoop", str(e), line_info)
                raise

    def handle_for_key_value_loop(self, node):
        """处理键值对遍历循环: for key, value in dict do ... end"""
        executor = self.executor
        variables = node.value
        key_var = variables['key_var']
        value_var = variables['value_var']
        step_name = f"执行键值对循环: {key_var}, {value_var}"
        line_info = executor._get_line_info(node)

        with allure.step(step_name):
            try:
                collection = executor.eval_expression(node.children[0])

                if not isinstance(collection, dict):
                    raise TypeError(
                        f"键值对遍历要求字典类型，得到: "
                        f"{type(collection).__name__}")

                allure.attach(
                    f"键变量: {key_var}\n值变量: {value_var}\n遍历字典: "
                    f"{collection}\n字典长度: {len(collection)}{line_info}",
                    name="键值对循环信息",
                    attachment_type=allure.attachment_type.TEXT,
                )

                statements_node = node.children[1]

                for key, value in collection.items():
                    executor.state.set_local_variable(key_var, key)
                    executor.state.set_local_variable(value_var, value)
                    executor._notify_remote_servers_variable_changed(
                        key_var, key)
                    executor._notify_remote_servers_variable_changed(
                        value_var, value)

                    try:
                        self._execute_loop_iteration(
                            statements_node=statements_node,
                            line_info=line_info,
                            node_type="ForKeyValueLoop",
                            step_label=(
                                f"{key_var} = {key}, {value_var} = {value}"
                            ),
                            break_message=(
                                f"在 {key_var} = {key}, {value_var} = {value} "
                                f"时遇到break语句，退出循环"
                            ),
                            continue_message=(
                                f"在 {key_var} = {key}, {value_var} = {value} "
                                f"时遇到continue语句，跳过本次循环"
                            ),
                            return_message=(
                                f"在 {key_var} = {key}, {value_var} = {value} "
                                f"时遇到return语句，退出函数"
                            ),
                        )
                    except _LoopBreak:
                        break
            except (BreakException, ContinueException, ReturnException):
                raise
            except Exception as e:
                self._attach_loop_error("ForKeyValueLoop", str(e), line_info)
                raise

    def _execute_loop_iteration(self, statements_node, line_info, node_type,
                                step_label, break_message, continue_message,
                                return_message):
        with allure.step(f"循环轮次: {step_label}"):
            try:
                self.executor.execute(statements_node)
            except BreakException:
                allure.attach(
                    break_message,
                    name="循环Break",
                    attachment_type=allure.attachment_type.TEXT,
                )
                raise _LoopBreak()
            except ContinueException:
                allure.attach(
                    continue_message,
                    name="循环Continue",
                    attachment_type=allure.attachment_type.TEXT,
                )
            except ReturnException as e:
                allure.attach(
                    return_message,
                    name="循环Return",
                    attachment_type=allure.attachment_type.TEXT,
                )
                raise e
            except Exception as e:
                error_details = (f"循环执行异常 ({step_label}): "
                                 f"{str(e)}{line_info}\n"
                                 f"上下文: 执行{node_type}节点")
                allure.attach(
                    error_details,
                    name="DSL执行异常",
                    attachment_type=allure.attachment_type.TEXT,
                )
                raise

    def _attach_loop_error(self, node_type, error_text, line_info):
        error_details = (f"执行{node_type}节点: {error_text}{line_info}\n"
                         f"上下文: 执行{node_type}节点")
        allure.attach(
            error_details,
            name="DSL执行异常",
            attachment_type=allure.attachment_type.TEXT,
        )


class _LoopBreak(Exception):
    """Internal sentinel for breaking only the current loop handler."""
    pass
