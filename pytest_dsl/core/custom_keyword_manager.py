import os
from pytest_dsl.core.lexer import get_lexer
from pytest_dsl.core.parser import get_parser, Node
from pytest_dsl.core.dsl_executor import DSLExecutor
from pytest_dsl.core.keyword_manager import keyword_manager


class CustomKeywordManager:
    """自定义关键字管理器

    负责加载和注册自定义关键字
    """

    def __init__(self):
        """初始化自定义关键字管理器"""
        self.resource_cache = {}  # 缓存已加载的资源文件
        self.resource_paths = []  # 资源文件搜索路径
        self.auto_imported_resources = set()  # 记录已自动导入的资源文件

    def add_resource_path(self, path: str) -> None:
        """添加资源文件搜索路径

        Args:
            path: 资源文件路径
        """
        if path not in self.resource_paths:
            self.resource_paths.append(path)

    def auto_import_resources_directory(
            self, project_root: str = None) -> None:
        """自动导入项目中的resources目录

        Args:
            project_root: 项目根目录，默认为当前工作目录
        """
        if project_root is None:
            project_root = os.getcwd()

        # 查找resources目录
        resources_dir = os.path.join(project_root, "resources")

        if (not os.path.exists(resources_dir) or
                not os.path.isdir(resources_dir)):
            # 如果没有resources目录，静默返回
            return

        print(f"发现resources目录: {resources_dir}")

        # 递归查找所有.resource文件
        resource_files = []
        for root, dirs, files in os.walk(resources_dir):
            for file in files:
                if file.endswith('.resource'):
                    resource_files.append(os.path.join(root, file))

        if not resource_files:
            print("resources目录中没有找到.resource文件")
            return

        print(f"在resources目录中发现 {len(resource_files)} 个资源文件")

        # 按照依赖关系排序并加载资源文件
        sorted_files = self._sort_resources_by_dependencies(resource_files)

        for resource_file in sorted_files:
            try:
                # 检查是否已经自动导入过
                absolute_path = os.path.abspath(resource_file)
                if absolute_path not in self.auto_imported_resources:
                    self.load_resource_file(resource_file)
                    self.auto_imported_resources.add(absolute_path)
                    print(f"自动导入资源文件: {resource_file}")
            except Exception as e:
                print(f"自动导入资源文件失败 {resource_file}: {e}")

    def _sort_resources_by_dependencies(self, resource_files):
        """根据依赖关系对资源文件进行排序

        Args:
            resource_files: 资源文件列表

        Returns:
            list: 按依赖关系排序后的资源文件列表
        """
        # 简单的拓扑排序实现
        dependencies = {}
        all_files = set()

        # 分析每个文件的依赖关系
        for file_path in resource_files:
            all_files.add(file_path)
            dependencies[file_path] = self._extract_dependencies(file_path)

        # 拓扑排序
        sorted_files = []
        visited = set()
        temp_visited = set()

        def visit(file_path):
            if file_path in temp_visited:
                # 检测到循环依赖，跳过
                return
            if file_path in visited:
                return

            temp_visited.add(file_path)

            # 访问依赖的文件
            for dep in dependencies.get(file_path, []):
                if dep in all_files:  # 只处理在当前文件列表中的依赖
                    visit(dep)

            temp_visited.remove(file_path)
            visited.add(file_path)
            sorted_files.append(file_path)

        # 访问所有文件
        for file_path in resource_files:
            if file_path not in visited:
                visit(file_path)

        return sorted_files

    def _extract_dependencies(self, file_path):
        """提取资源文件的依赖关系

        Args:
            file_path: 资源文件路径

        Returns:
            list: 依赖的文件路径列表
        """
        dependencies = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 解析文件获取导入信息
            lexer = get_lexer()
            parser = get_parser()
            ast = parser.parse(content, lexer=lexer)

            if ast.type == 'Start' and ast.children:
                metadata_node = ast.children[0]
                if metadata_node.type == 'Metadata':
                    for item in metadata_node.children:
                        if item.type == '@import':
                            imported_file = item.value
                            # 处理相对路径
                            if not os.path.isabs(imported_file):
                                imported_file = os.path.join(
                                    os.path.dirname(file_path), imported_file)
                            # 规范化路径
                            imported_file = os.path.normpath(imported_file)
                            dependencies.append(imported_file)

        except Exception as e:
            # 如果解析失败，返回空依赖列表
            print(f"解析资源文件依赖失败 {file_path}: {e}")

        return dependencies

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
                project_root = os.path.dirname(
                    os.path.dirname(os.path.dirname(__file__)))
                full_path = os.path.join(project_root, file_path)
                if os.path.exists(full_path):
                    file_path = full_path
                    absolute_path = os.path.abspath(file_path)
                else:
                    raise FileNotFoundError(f"资源文件不存在: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 标记为已加载（在解析前标记，避免循环导入）
            self.resource_cache[absolute_path] = True

            # 使用公共方法解析和处理资源文件内容
            self._process_resource_file_content(content, file_path)

        except Exception as e:
            # 如果处理失败，移除缓存标记
            self.resource_cache.pop(absolute_path, None)
            print(f"资源文件 {file_path} 加载失败: {str(e)}")
            raise

    def _process_resource_file_content(self, content: str,
                                       file_path: str) -> None:
        """处理资源文件内容

        Args:
            content: 文件内容
            file_path: 文件路径
        """
        # 解析资源文件
        lexer = get_lexer()
        parser = get_parser()
        ast = parser.parse(content, lexer=lexer)

        # 处理导入指令
        self._process_imports(ast, os.path.dirname(file_path))

        # 注册关键字
        self._register_keywords_from_ast(ast, file_path)

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

    def _register_keywords_from_ast(self, ast: Node,
                                    source_name: str) -> None:
        """从AST中注册关键字（重构后的版本）

        Args:
            ast: 抽象语法树
            source_name: 来源名称
        """
        if ast.type != 'Start' or len(ast.children) < 2:
            return

        # 遍历语句节点
        statements_node = ast.children[1]
        if statements_node.type != 'Statements':
            return

        for node in statements_node.children:
            if node.type in ['CustomKeyword', 'Function']:
                self._register_custom_keyword(node, source_name)

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

            # 导入ReturnException以避免循环导入
            from pytest_dsl.core.dsl_executor import ReturnException

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
                    executor.test_context.set(
                        param_name, kwargs[param_mapping_name])

            # 重要：创建变量替换器，使变量解析正常工作
            from pytest_dsl.core.variable_utils import VariableReplacer
            executor.variable_replacer = VariableReplacer(
                executor.variables, executor.test_context
            )

            # 执行关键字体中的语句
            result = None
            try:
                for stmt in body_node.children:
                    executor.execute(stmt)
            except ReturnException as e:
                # 捕获return异常，提取返回值
                result = e.return_value
            except Exception as e:
                print(f"执行自定义关键字 {keyword_name} 时发生错误: {str(e)}")
                raise

            return result

        print(f"已注册自定义关键字: {keyword_name} 来自文件: {file_path}")

    def register_keyword_from_dsl_content(self, dsl_content: str,
                                          source_name: str = "DSL内容") -> list:
        """从DSL内容注册关键字（公共方法）

        Args:
            dsl_content: DSL文本内容
            source_name: 来源名称，用于日志显示

        Returns:
            list: 注册成功的关键字名称列表

        Raises:
            Exception: 解析或注册失败时抛出异常
        """
        try:
            # 解析DSL内容
            lexer = get_lexer()
            parser = get_parser()
            ast = parser.parse(dsl_content, lexer=lexer)

            # 收集注册前的关键字列表
            existing_keywords = (
                set(keyword_manager._keywords.keys())
                if hasattr(keyword_manager, '_keywords')
                else set()
            )

            # 使用统一的注册方法
            self._register_keywords_from_ast(ast, source_name)

            # 计算新注册的关键字
            new_keywords = (
                set(keyword_manager._keywords.keys())
                if hasattr(keyword_manager, '_keywords')
                else set()
            )
            registered_keywords = list(new_keywords - existing_keywords)

            if not registered_keywords:
                raise ValueError("在DSL内容中未找到任何关键字定义")

            return registered_keywords

        except Exception as e:
            print(f"从DSL内容注册关键字失败（来源：{source_name}）: {e}")
            raise

    def register_specific_keyword_from_dsl_content(
            self, keyword_name: str, dsl_content: str,
            source_name: str = "DSL内容") -> bool:
        """从DSL内容注册指定的关键字（公共方法）

        Args:
            keyword_name: 要注册的关键字名称
            dsl_content: DSL文本内容
            source_name: 来源名称，用于日志显示

        Returns:
            bool: 是否注册成功

        Raises:
            Exception: 解析失败或未找到指定关键字时抛出异常
        """
        try:
            # 解析DSL内容
            lexer = get_lexer()
            parser = get_parser()
            ast = parser.parse(dsl_content, lexer=lexer)

            # 查找指定的关键字定义
            if ast.type == 'Start' and len(ast.children) >= 2:
                statements_node = ast.children[1]
                if statements_node.type == 'Statements':
                    for node in statements_node.children:
                        if (node.type in ['CustomKeyword', 'Function'] and
                                node.value == keyword_name):
                            self._register_custom_keyword(node, source_name)
                            return True

            raise ValueError(f"在DSL内容中未找到关键字定义: {keyword_name}")

        except Exception as e:
            print(f"从DSL内容注册关键字失败 {keyword_name}（来源：{source_name}）: {e}")
            raise


# 创建全局自定义关键字管理器实例
custom_keyword_manager = CustomKeywordManager()
