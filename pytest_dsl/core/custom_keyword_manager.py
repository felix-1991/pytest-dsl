from typing import Dict, Any, List, Optional
import os
import pathlib
from pytest_dsl.core.lexer import get_lexer
from pytest_dsl.core.parser import get_parser, Node
from pytest_dsl.core.dsl_executor import DSLExecutor
from pytest_dsl.core.keyword_manager import keyword_manager
from pytest_dsl.core.context import TestContext


class CustomKeywordManager:
    """自定义关键字管理器
    
    负责加载和注册自定义关键字
    """
    
    def __init__(self):
        """初始化自定义关键字管理器"""
        self.resource_cache = {}  # 缓存已加载的资源文件
        self.resource_paths = []  # 资源文件搜索路径
    
    def add_resource_path(self, path: str) -> None:
        """添加资源文件搜索路径
        
        Args:
            path: 资源文件路径
        """
        if path not in self.resource_paths:
            self.resource_paths.append(path)
    
    def load_resource_file(self, file_path: str) -> None:
        """加载资源文件
        
        Args:
            file_path: 资源文件路径
        """
        # 规范化路径，解决路径叠加的问题
        file_path = os.path.normpath(file_path)
        
        # 如果已经缓存，则跳过
        absolute_path = os.path.abspath(file_path)
        if absolute_path in self.resource_cache:
            return
        
        # 读取文件内容
        if not os.path.exists(file_path):
            # 尝试在资源路径中查找
            for resource_path in self.resource_paths:
                full_path = os.path.join(resource_path, file_path)
                if os.path.exists(full_path):
                    file_path = full_path
                    absolute_path = os.path.abspath(file_path)
                    break
            else:
                # 如果文件不存在，尝试在根项目目录中查找
                # 一般情况下文件路径可能是相对于项目根目录的
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                full_path = os.path.join(project_root, file_path)
                if os.path.exists(full_path):
                    file_path = full_path
                    absolute_path = os.path.abspath(file_path)
                else:
                    raise FileNotFoundError(f"资源文件不存在: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析资源文件
            lexer = get_lexer()
            parser = get_parser()
            ast = parser.parse(content, lexer=lexer)
            
            # 标记为已加载
            self.resource_cache[absolute_path] = True
            
            # 处理导入指令
            self._process_imports(ast, os.path.dirname(file_path))
            
            # 注册关键字
            self._register_keywords(ast, file_path)
        except Exception as e:
            print(f"资源文件 {file_path} 加载失败: {str(e)}")
            raise
    
    def _process_imports(self, ast: Node, base_dir: str) -> None:
        """处理资源文件中的导入指令
        
        Args:
            ast: 抽象语法树
            base_dir: 基础目录
        """
        if ast.type != 'Start' or not ast.children:
            return
        
        metadata_node = ast.children[0]
        if metadata_node.type != 'Metadata':
            return
        
        for item in metadata_node.children:
            if item.type == '@import':
                imported_file = item.value
                # 处理相对路径
                if not os.path.isabs(imported_file):
                    imported_file = os.path.join(base_dir, imported_file)
                    
                # 规范化路径，避免路径叠加问题
                imported_file = os.path.normpath(imported_file)
                
                # 递归加载导入的资源文件
                self.load_resource_file(imported_file)
    
    def _register_keywords(self, ast: Node, file_path: str) -> None:
        """从AST中注册关键字
        
        Args:
            ast: 抽象语法树
            file_path: 文件路径
        """
        if ast.type != 'Start' or len(ast.children) < 2:
            return
        
        # 遍历语句节点
        statements_node = ast.children[1]
        if statements_node.type != 'Statements':
            return
        
        for node in statements_node.children:
            if node.type == 'CustomKeyword':
                self._register_custom_keyword(node, file_path)
    
    def _register_custom_keyword(self, node: Node, file_path: str) -> None:
        """注册自定义关键字
        
        Args:
            node: 关键字节点
            file_path: 资源文件路径
        """
        # 提取关键字信息
        keyword_name = node.value
        params_node = node.children[0]
        body_node = node.children[1]
        
        # 构建参数列表
        parameters = []
        param_mapping = {}
        param_defaults = {}  # 存储参数默认值
        
        for param in params_node if params_node else []:
            param_name = param.value
            param_default = None
            
            # 检查是否有默认值
            if param.children and param.children[0]:
                param_default = param.children[0].value
                param_defaults[param_name] = param_default  # 保存默认值
            
            # 添加参数定义
            parameters.append({
                'name': param_name,
                'mapping': param_name,  # 中文参数名和内部参数名相同
                'description': f'自定义关键字参数 {param_name}'
            })
            
            param_mapping[param_name] = param_name
        
        # 注册自定义关键字到关键字管理器
        @keyword_manager.register(keyword_name, parameters)
        def custom_keyword_executor(**kwargs):
            """自定义关键字执行器"""
            # 创建一个新的DSL执行器
            executor = DSLExecutor()
            
            # 获取传递的上下文
            context = kwargs.get('context')
            if context:
                executor.test_context = context
            
            # 先应用默认值
            for param_name, default_value in param_defaults.items():
                executor.variables[param_name] = default_value
                executor.test_context.set(param_name, default_value)
            
            # 然后应用传入的参数值（覆盖默认值）
            for param_name, param_mapping_name in param_mapping.items():
                if param_mapping_name in kwargs:
                    # 确保参数值在标准变量和测试上下文中都可用
                    executor.variables[param_name] = kwargs[param_mapping_name]
                    executor.test_context.set(param_name, kwargs[param_mapping_name])
            
            # 执行关键字体中的语句
            result = None
            try:
                for stmt in body_node.children:
                    # 检查是否是return语句
                    if stmt.type == 'Return':
                        # 对表达式求值
                        result = executor.eval_expression(stmt.children[0])
                        break
                    else:
                        # 执行普通语句
                        executor.execute(stmt)
            except Exception as e:
                print(f"执行自定义关键字 {keyword_name} 时发生错误: {str(e)}")
                raise
            
            return result
        
        print(f"已注册自定义关键字: {keyword_name} 来自文件: {file_path}")


# 创建全局自定义关键字管理器实例
custom_keyword_manager = CustomKeywordManager() 