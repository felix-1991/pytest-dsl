import allure
from parser.lexer import get_lexer
from parser.parser import get_parser, Node
from core.keyword_manager import keyword_manager


class DSLExecutor:
    def __init__(self):
        self.variables = {}
        
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
        elif isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            return self._get_variable(value[2:-1])
        elif isinstance(value, str):
            return self._replace_variables_in_string(value)
        return value
    
    def _get_variable(self, var_name):
        """获取变量值"""
        if var_name in self.variables:
            return self.variables[var_name]
        raise Exception(f"变量未定义: {var_name}")
    
    def _replace_variables_in_string(self, value):
        """替换字符串中的变量引用"""
        import re
        def replace_var(match):
            return str(self._get_variable(match.group(1)))
        return re.sub(r'\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}', replace_var, value)

    def _handle_start(self, node):
        """处理开始节点"""
        metadata = {}
        for child in node.children:
            if child.type == 'Metadata':
                for item in child.children:
                    metadata[item.type] = item.value
                    
        # 设置 Allure 报告信息
        if '@name' in metadata:
            allure.dynamic.title(metadata['@name'])
        if '@description' in metadata:
            allure.dynamic.description(metadata['@description'])
        if '@tags' in metadata:
            for tag in metadata['@tags']:
                allure.dynamic.tag(tag.value)
                
        # 执行所有子节点
        for child in node.children:
            self.execute(child)

    def _handle_statements(self, node):
        """处理语句列表"""
        for stmt in node.children:
            self.execute(stmt)

    @allure.step("变量赋值")
    def _handle_assignment(self, node):
        """处理赋值语句"""
        var_name = node.value
        expr_value = self.eval_expression(node.children[0])
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

    @allure.step("执行关键字调用")
    def _execute_keyword_call(self, node):
        """执行关键字调用"""
        keyword_name = node.value
        keyword_info = keyword_manager.get_keyword_info(keyword_name)
        if not keyword_info:
            raise Exception(f"未注册的关键字: {keyword_name}")
            
        kwargs = self._prepare_keyword_params(node, keyword_info)
        return keyword_manager.execute(keyword_name, **kwargs)

    def _prepare_keyword_params(self, node, keyword_info):
        """准备关键字调用参数"""
        mapping = keyword_info.get('mapping', {})
        kwargs = {}
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