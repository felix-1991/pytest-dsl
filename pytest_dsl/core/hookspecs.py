"""
pytest-dsl hook规范定义

使用pluggy定义hook接口，允许外部框架扩展DSL功能
"""
import pluggy
from typing import Dict, List, Optional, Any

# 创建pytest-dsl的hook标记器
hookspec = pluggy.HookspecMarker("pytest_dsl")
hookimpl = pluggy.HookimplMarker("pytest_dsl")


class DSLHookSpecs:
    """DSL Hook规范"""

    @hookspec
    def dsl_load_content(self, dsl_id: str) -> Optional[str]:
        """加载DSL内容

        Args:
            dsl_id: DSL标识符（可以是文件路径、数据库ID等）

        Returns:
            DSL内容字符串，如果无法加载返回None
        """

    @hookspec
    def dsl_list_cases(self, project_id: Optional[int] = None,
                       filters: Optional[Dict[str, Any]] = None
                       ) -> List[Dict[str, Any]]:
        """列出DSL用例

        Args:
            project_id: 项目ID，用于过滤（可选）
            filters: 其他过滤条件（可选）

        Returns:
            用例列表，每个用例包含id、name、description等字段
        """

    @hookspec
    def dsl_register_custom_keywords(self,
                                     project_id: Optional[int] = None) -> None:
        """注册自定义关键字

        Args:
            project_id: 项目ID，用于过滤（可选）
        """

    @hookspec
    def dsl_get_execution_context(self, dsl_id: str,
                                  base_context: Dict[str, Any]
                                  ) -> Dict[str, Any]:
        """获取执行上下文

        Args:
            dsl_id: DSL标识符
            base_context: 基础上下文

        Returns:
            扩展后的执行上下文
        """

    @hookspec(firstresult=True)  # 只使用第一个返回结果
    def dsl_create_executor(self) -> Optional[Any]:
        """创建自定义DSL执行器

        Returns:
            自定义执行器实例，如果返回None则使用默认执行器
        """

    @hookspec
    def dsl_before_execution(self, dsl_id: str,
                             context: Dict[str, Any]) -> None:
        """DSL执行前的hook

        Args:
            dsl_id: DSL标识符
            context: 执行上下文
        """

    @hookspec
    def dsl_after_execution(self, dsl_id: str, context: Dict[str, Any],
                            result: Any,
                            exception: Optional[Exception] = None) -> None:
        """DSL执行后的hook

        Args:
            dsl_id: DSL标识符
            context: 执行上下文
            result: 执行结果
            exception: 如果执行失败，包含异常信息
        """

    @hookspec
    def dsl_transform_content(self, dsl_id: str, content: str) -> str:
        """转换DSL内容

        Args:
            dsl_id: DSL标识符
            content: 原始DSL内容

        Returns:
            转换后的DSL内容
        """

    @hookspec
    def dsl_validate_content(self, dsl_id: str, content: str) -> List[str]:
        """验证DSL内容

        Args:
            dsl_id: DSL标识符
            content: DSL内容

        Returns:
            验证错误列表，空列表表示验证通过
        """

    @hookspec
    def dsl_load_variables(self, project_id: Optional[int] = None,
                           environment: Optional[str] = None,
                           filters: Optional[Dict[str, Any]] = None
                           ) -> Dict[str, Any]:
        """加载变量配置

        Args:
            project_id: 项目ID，用于过滤（可选）
            environment: 环境名称，如dev、test、prod等（可选）
            filters: 其他过滤条件（可选）

        Returns:
            变量字典，键为变量名，值为变量值
        """

    @hookspec
    def dsl_get_variable(self, var_name: str, project_id: Optional[int] = None,
                         environment: Optional[str] = None
                         ) -> Optional[Any]:
        """获取单个变量值

        Args:
            var_name: 变量名
            project_id: 项目ID，用于过滤（可选）
            environment: 环境名称（可选）

        Returns:
            变量值，如果变量不存在返回None
        """

    @hookspec
    def dsl_list_variable_sources(self, project_id: Optional[int] = None
                                  ) -> List[Dict[str, Any]]:
        """列出可用的变量源

        Args:
            project_id: 项目ID，用于过滤（可选）

        Returns:
            变量源列表，每个源包含name、type、description等字段
        """

    @hookspec
    def dsl_validate_variables(self, variables: Dict[str, Any],
                               project_id: Optional[int] = None
                               ) -> List[str]:
        """验证变量配置

        Args:
            variables: 变量字典
            project_id: 项目ID，用于过滤（可选）

        Returns:
            验证错误列表，空列表表示验证通过
        """
