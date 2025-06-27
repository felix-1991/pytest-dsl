"""变量提供者模块

定义了变量提供者的接口和具体实现，用于将不同来源的变量注入到TestContext中。
这样可以实现解耦，让关键字只需要通过context获取变量，而不需要直接依赖特定的变量源。
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict


class VariableProvider(ABC):
    """变量提供者接口

    所有的变量提供者都需要实现这个接口，以便可以注册到TestContext中。
    """

    @abstractmethod
    def get_variable(self, key: str) -> Optional[Any]:
        """获取变量值

        Args:
            key: 变量键

        Returns:
            变量值，如果不存在返回None
        """
        pass

    @abstractmethod
    def has_variable(self, key: str) -> bool:
        """检查变量是否存在

        Args:
            key: 变量键

        Returns:
            True如果变量存在，否则False
        """
        pass

    def get_all_variables(self) -> Dict[str, Any]:
        """获取所有变量（可选实现）

        Returns:
            包含所有变量的字典
        """
        return {}


class YAMLVariableProvider(VariableProvider):
    """YAML变量提供者

    将yaml_vars包装成变量提供者，使其可以注入到TestContext中。
    """

    def __init__(self):
        # 延迟导入，避免循环依赖
        from pytest_dsl.core.yaml_vars import yaml_vars
        self.yaml_vars = yaml_vars

    def get_variable(self, key: str) -> Optional[Any]:
        """从YAML变量源获取变量值"""
        return self.yaml_vars.get_variable(key)

    def has_variable(self, key: str) -> bool:
        """检查YAML变量源中是否存在变量"""
        return self.yaml_vars.has_variable(key)

    def get_all_variables(self) -> Dict[str, Any]:
        """获取所有YAML变量"""
        return self.yaml_vars.get_all_variables()


class GlobalContextVariableProvider(VariableProvider):
    """全局上下文变量提供者

    将global_context包装成变量提供者，但需要避免和YAML变量重复。
    """

    def __init__(self):
        # 延迟导入，避免循环依赖
        from pytest_dsl.core.global_context import global_context
        self.global_context = global_context

    def get_variable(self, key: str) -> Optional[Any]:
        """从全局上下文获取变量值"""
        # 注意：global_context的get_variable方法内部也会调用yaml_vars
        # 为了避免重复，这里直接访问存储的变量
        try:
            # 直接从全局变量存储中获取，跳过YAML变量
            from filelock import FileLock
            with FileLock(self.global_context._lock_file):
                variables = self.global_context._load_variables()
                return variables.get(key)
        except Exception:
            return None

    def has_variable(self, key: str) -> bool:
        """检查全局上下文中是否存在变量"""
        try:
            from filelock import FileLock
            with FileLock(self.global_context._lock_file):
                variables = self.global_context._load_variables()
                return key in variables
        except Exception:
            return False

    def get_all_variables(self) -> Dict[str, Any]:
        """获取所有全局变量"""
        try:
            from filelock import FileLock
            with FileLock(self.global_context._lock_file):
                return self.global_context._load_variables()
        except Exception:
            return {}


class CompositeVariableProvider(VariableProvider):
    """组合变量提供者

    可以将多个变量提供者组合在一起，按优先级顺序查找变量。
    """

    def __init__(self, providers: list = None):
        """初始化组合变量提供者

        Args:
            providers: 变量提供者列表，按优先级排序（索引越小优先级越高）
        """
        self.providers = providers or []

    def add_provider(self, provider: VariableProvider):
        """添加变量提供者"""
        if provider not in self.providers:
            self.providers.append(provider)

    def remove_provider(self, provider: VariableProvider):
        """移除变量提供者"""
        if provider in self.providers:
            self.providers.remove(provider)

    def get_variable(self, key: str) -> Optional[Any]:
        """按优先级顺序从提供者中获取变量"""
        for provider in self.providers:
            try:
                value = provider.get_variable(key)
                if value is not None:
                    return value
            except Exception:
                continue
        return None

    def has_variable(self, key: str) -> bool:
        """检查是否有任何提供者包含该变量"""
        for provider in self.providers:
            try:
                if provider.has_variable(key):
                    return True
            except Exception:
                continue
        return False

    def get_all_variables(self) -> Dict[str, Any]:
        """获取所有变量，优先级高的覆盖优先级低的"""
        all_vars = {}

        # 从后往前遍历，让优先级高的覆盖优先级低的
        for provider in reversed(self.providers):
            try:
                vars_dict = provider.get_all_variables()
                all_vars.update(vars_dict)
            except Exception:
                continue

        return all_vars


# 创建默认的变量提供者实例
def create_default_variable_providers() -> list:
    """创建默认的变量提供者列表

    按优先级排序：YAML变量 > 全局上下文变量

    Returns:
        变量提供者列表
    """
    providers = [
        YAMLVariableProvider(),
        GlobalContextVariableProvider()
    ]
    return providers


def setup_context_with_default_providers(context):
    """为TestContext设置默认的变量提供者

    Args:
        context: TestContext实例
    """
    providers = create_default_variable_providers()
    for provider in providers:
        context.register_external_variable_provider(provider)
