"""Local keyword invocation for DSL execution."""

import difflib
import re

import allure

from pytest_dsl.core.execution.exceptions import DSLExecutionError
from pytest_dsl.core.keyword_manager import keyword_manager


class KeywordInvoker:
    """Executes registered local keywords for a DSL executor."""

    def __init__(self, executor):
        self.executor = executor

    def execute(self, node):
        """Execute a KeywordCall node."""
        executor = self.executor
        keyword_name = node.value
        line_info = executor._get_line_info(node)

        keyword_info = keyword_manager.get_keyword_info(keyword_name)
        if not keyword_info:
            error_msg = f"未注册的关键字: {keyword_name}"
            with allure.step(f"调用关键字: {keyword_name}"):
                allure.attach(
                    f"执行KeywordCall节点: 未注册的关键字: {keyword_name}"
                    f"{line_info}\n上下文: 执行KeywordCall节点",
                    name="DSL执行异常",
                    attachment_type=allure.attachment_type.TEXT,
                )
            raise Exception(error_msg)

        with allure.step(f"调用关键字: {keyword_name}"):
            try:
                kwargs = self.prepare_params(node, keyword_info)
                kwargs['step_name'] = keyword_name
                kwargs['skip_logging'] = True

                result = keyword_manager.execute(keyword_name, **kwargs)

                allure.attach(
                    f"关键字: {keyword_name}\n执行结果: 成功{line_info}",
                    name="关键字调用",
                    attachment_type=allure.attachment_type.TEXT,
                )

                return result
            except Exception as e:
                error_details = self._format_keyword_error(e, node, line_info)
                allure.attach(
                    error_details,
                    name="DSL执行异常",
                    attachment_type=allure.attachment_type.TEXT,
                )
                raise

    def prepare_params(self, node, keyword_info):
        """Prepare keyword kwargs from DSL parameter nodes."""
        executor = self.executor
        mapping = keyword_info.get('mapping', {})
        kwargs = {'context': executor.test_context}

        if node.children[0]:
            seen_raw_names = set()
            seen_mapped_names = set()
            for param in node.children[0]:
                param_name = param.value
                english_param_name = mapping.get(param_name, param_name)

                if mapping:
                    allowed_cn = set(mapping.keys())
                    allowed_en = set(mapping.values())
                    if (param_name not in allowed_cn and
                            param_name not in allowed_en):
                        details = [
                            f"关键字参数错误: {node.value} 不支持参数: "
                            f"{param_name}",
                            f"支持的参数: "
                            f"{self._format_supported_params(mapping)}",
                        ]
                        suggestion = self._suggest_param_name(
                            param_name,
                            mapping,
                        )
                        if suggestion:
                            details.append(suggestion)
                        raise DSLExecutionError(
                            " \n ".join(details),
                            line_number=getattr(node, 'line_number', None),
                            node_type=getattr(node, 'type', None),
                        )

                if param_name in seen_raw_names:
                    raise DSLExecutionError(
                        f"关键字参数错误: {node.value} 参数重复: {param_name}",
                        line_number=getattr(node, 'line_number', None),
                        node_type=getattr(node, 'type', None),
                    )
                if english_param_name in seen_mapped_names:
                    raise DSLExecutionError(
                        f"关键字参数错误: {node.value} 参数重复(映射后): "
                        f"{english_param_name}",
                        line_number=getattr(node, 'line_number', None),
                        node_type=getattr(node, 'type', None),
                    )
                seen_raw_names.add(param_name)
                seen_mapped_names.add(english_param_name)

                with allure.step(f"解析参数: {param_name}"):
                    try:
                        param_value = executor.eval_expression(
                            param.children[0])
                        kwargs[english_param_name] = param_value

                        allure.attach(
                            f"参数名: {param_name}\n"
                            f"参数值: {param_value}",
                            name="参数解析详情",
                            attachment_type=allure.attachment_type.TEXT,
                        )
                    except Exception as e:
                        raise Exception(
                            f"参数解析异常 ({param_name}): {str(e)}")

        return kwargs

    def _format_keyword_error(self, error, node, line_info):
        error_text = str(error)
        if "参数解析异常" not in error_text and "无法解析变量引用" not in error_text:
            return (f"执行KeywordCall节点: {error_text}{line_info}\n"
                    f"上下文: 执行KeywordCall节点")

        if "参数解析异常" in error_text:
            match = re.search(r'参数解析异常 \(([^)]+)\): (.+)', error_text)
            if match:
                param_name, detailed_error = match.groups()
                return (f"参数解析失败 ({param_name}): "
                        f"{detailed_error}{line_info}\n"
                        f"上下文: 执行KeywordCall节点")

        return (f"参数解析失败: {error_text}{line_info}\n"
                f"上下文: 执行KeywordCall节点")

    def _format_supported_params(self, mapping) -> str:
        if not mapping:
            return "（无可用参数信息）"
        items = []
        for cn_name, en_name in mapping.items():
            if cn_name == en_name:
                items.append(f"{cn_name}")
            else:
                items.append(f"{cn_name}({en_name})")
        return ", ".join(items)

    def _suggest_param_name(self, bad_name: str, mapping) -> str:
        if not mapping:
            return ""
        candidates = list(mapping.keys()) + list(mapping.values())
        matches = difflib.get_close_matches(
            bad_name, candidates, n=1, cutoff=0.6)
        if matches:
            return f"你是不是想用: {matches[0]}"
        return ""
