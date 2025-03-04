import re
import allure
from core.lexer import get_lexer
from core.parser import get_parser, Node
from core.keyword_manager import keyword_manager
from core.global_context import global_context
from core.test_context import TestContext
import keywords


class DSLExecutor:
    def __init__(self):
        self.variables = {}
        self.test_context = TestContext()
        
    def eval_expression(self, expr_node):
        """
        对表达式节点进行求值，返回表达式的值。
        
        :param expr_node: AST中的表达式节点
        :return: 表达式求值后的结果
        :raises Exception: 当遇到未定义变量或无法求值的类型时抛出异常
        """
        if expr_node.type == 'Expression':
            return self._eval_expression_value(expr_node.value)
        elif expr_node.type == 'KeywordCall':
            return self.execute(expr_node)
        else:
            raise Exception(f"无法求值的表达式类型: {expr_node.type}")
    
    def _eval_expression_value(self, value):
        """处理表达式值的具体逻辑"""
        if isinstance(value, Node):
            return self.eval_expression(value)
        elif isinstance(value, str):
            # 定义变量引用模式
            pattern = r'\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
            # 检查整个字符串是否完全匹配单一变量引用模式
            match = re.fullmatch(pattern, value)
            if match:
                var_name = match.group(1)
                return self._get_variable(var_name)
            else:
                # 如果不是单一变量，则替换字符串中的所有变量引用
                return self._replace_variables_in_string(value)
        return value
    
    def _get_variable(self, var_name):
        """获取变量值，优先从本地变量获取，如果不存在则尝试从全局上下文获取"""
        if var_name in self.variables:
            return self.variables[var_name]
        elif global_context.has_variable(var_name):
            return global_context.get_variable(var_name)
        raise Exception(f"变量未定义: {var_name}")
    
    def _replace_variables_in_string(self, value):
        """替换字符串中的变量引用"""
        # 使用更严格的变量名匹配模式
        pattern = r'\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
        result = value
        matches = list(re.finditer(pattern, value))
        
        # 从后向前替换，避免前面的替换影响后面的索引位置
        for match in reversed(matches):
            var_name = match.group(1)
            var_value = self._get_variable(var_name)  # 使用现有的_get_variable方法
            result = result[:match.start()] + str(var_value) + result[match.end():]
        
        return result

    def _handle_start(self, node):
        """处理开始节点"""
        try:
            # 清空上下文，确保每个测试用例都有一个新的上下文
            self.test_context.clear()
            metadata = {}
            teardown_node = None
            
            # 先处理元数据和找到teardown节点
            for child in node.children:
                if child.type == 'Metadata':
                    for item in child.children:
                        metadata[item.type] = item.value
                elif child.type == 'Teardown':
                    teardown_node = child
                    
            # 设置 Allure 报告信息
            if '@name' in metadata:
                allure.dynamic.title(metadata['@name'])
            if '@description' in metadata:
                allure.dynamic.description(metadata['@description'])
            if '@tags' in metadata:
                for tag in metadata['@tags']:
                    allure.dynamic.tag(tag.value)
                    
            # 执行所有非teardown节点
            for child in node.children:
                if child.type != 'Teardown':
                    self.execute(child)
        finally:
            if teardown_node:
                with allure.step("执行清理操作"):
                    try:
                        self.execute(teardown_node)
                    except Exception as e:
                        allure.attach(
                            f"清理失败: {str(e)}",
                            name="清理失败",
                            attachment_type=allure.attachment_type.TEXT
                        )
            # 测试用例执行完成后清空上下文
            self.test_context.clear()

    def _handle_statements(self, node):
        """处理语句列表"""
        for stmt in node.children:
            self.execute(stmt)

    @allure.step("变量赋值")
    def _handle_assignment(self, node):
        """处理赋值语句"""
        var_name = node.value
        expr_value = self.eval_expression(node.children[0])
        
        # 检查变量名是否以g_开头，如果是则设置为全局变量
        if var_name.startswith('g_'):
            global_context.set_variable(var_name, expr_value)
            allure.attach(
                f"全局变量: {var_name}\n值: {expr_value}",
                name="全局变量赋值",
                attachment_type=allure.attachment_type.TEXT
            )
        else:
            self.variables[var_name] = expr_value
            allure.attach(
                f"变量: {var_name}\n值: {expr_value}",
                name="赋值详情",
                attachment_type=allure.attachment_type.TEXT
            )

    @allure.step("关键字调用赋值")
    def _handle_assignment_keyword_call(self, node):
        """处理关键字调用赋值"""
        var_name = node.value
        keyword_call_node = node.children[0]
        result = self.execute(keyword_call_node)
        
        if result is not None:
            # 检查变量名是否以g_开头，如果是则设置为全局变量
            if var_name.startswith('g_'):
                global_context.set_variable(var_name, result)
                allure.attach(
                    f"全局变量: {var_name}\n值: {result}",
                    name="全局变量赋值",
                    attachment_type=allure.attachment_type.TEXT
                )
            else:
                self.variables[var_name] = result
                allure.attach(
                    f"变量: {var_name}\n值: {result}",
                    name="赋值详情",
                    attachment_type=allure.attachment_type.TEXT
                )
        else:
            raise Exception(f"关键字 {keyword_call_node.value} 没有返回结果")

    @allure.step("执行循环")
    def _handle_for_loop(self, node):
        """处理for循环"""
        var_name = node.value
        start = self.eval_expression(node.children[0])
        end = self.eval_expression(node.children[1])
        
        for i in range(int(start), int(end)):
            self.variables[var_name] = i
            with allure.step(f"循环轮次: {var_name} = {i}"):
                self.execute(node.children[2])

    def _execute_keyword_call(self, node):
        """执行关键字调用"""
        keyword_name = node.value
        keyword_info = keyword_manager.get_keyword_info(keyword_name)
        if not keyword_info:
            raise Exception(f"未注册的关键字: {keyword_name}")
            
        kwargs = self._prepare_keyword_params(node, keyword_info)
        
        with allure.step(f"执行关键字: {keyword_name}"):
            try:
                result = keyword_manager.execute(keyword_name, **kwargs)
                self._log_keyword_execution(keyword_name, kwargs, result)
                return result
            except Exception as e:
                self._log_keyword_failure(keyword_name, kwargs, e)
                raise

    def _prepare_keyword_params(self, node, keyword_info):
        """准备关键字调用参数"""
        mapping = keyword_info.get('mapping', {})
        kwargs = {'context': self.test_context}  # 默认传入context参数
        for param in node.children[0]:
            param_name = param.value
            english_param_name = mapping.get(param_name, param_name)
            kwargs[english_param_name] = self.eval_expression(param.children[0])
        return kwargs

    def _log_keyword_execution(self, keyword_name, kwargs, result):
        """记录关键字执行结果"""
        allure.attach(
            f"关键字: {keyword_name}\n参数: {kwargs}\n返回值: {result}",
            name="执行详情",
            attachment_type=allure.attachment_type.TEXT
        )

    def _log_keyword_failure(self, keyword_name, kwargs, exception):
        """记录关键字执行失败"""
        allure.attach(
            f"关键字: {keyword_name}\n参数: {kwargs}\n异常: {str(exception)}",
            name="执行失败",
            attachment_type=allure.attachment_type.TEXT
        )

    @allure.step("执行清理操作")
    def _handle_teardown(self, node):
        """处理清理操作"""
        self.execute(node.children[0])

    def execute(self, node):
        """执行AST节点"""
        handlers = {
            'Start': self._handle_start,
            'Metadata': lambda _: None,
            'Statements': self._handle_statements,
            'Assignment': self._handle_assignment,
            'AssignmentKeywordCall': self._handle_assignment_keyword_call,
            'ForLoop': self._handle_for_loop,
            'KeywordCall': self._execute_keyword_call,
            'Teardown': self._handle_teardown
        }
        
        handler = handlers.get(node.type)
        if handler:
            return handler(node)
        raise Exception(f"未知的节点类型: {node.type}")

def read_file(filename):
    """读取 DSL 文件内容"""
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()