import os
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path


class YAMLVariableManager:
    """管理YAML格式的变量文件，支持hook扩展"""

    def __init__(self):
        self._loaded_files: List[str] = []
        self._variables: Dict[str, Any] = {}
        self._enable_hooks = True  # 是否启用hook

    def has_variable(self, name: str) -> bool:
        """检查变量是否存在

        Args:
            name: 变量名

        Returns:
            bool: 变量是否存在
        """
        # 首先检查本地变量
        if name in self._variables:
            return True

        # 如果启用了hook，尝试通过hook查找
        if self._enable_hooks:
            hook_value = self._get_variable_through_hook(name)
            return hook_value is not None

        return False

    def load_yaml_file(self, file_path: str) -> None:
        """加载单个YAML文件中的变量"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"变量文件不存在: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                variables = yaml.safe_load(f)
                if variables and isinstance(variables, dict):
                    # 记录已加载的文件
                    self._loaded_files.append(file_path)
                    # 更新变量字典，新文件中的变量会覆盖旧的
                    self._variables.update(variables)
            except yaml.YAMLError as e:
                raise ValueError(f"YAML文件格式错误 {file_path}: {str(e)}")

    def load_yaml_files(self, file_paths: List[str]) -> None:
        """批量加载多个YAML文件中的变量"""
        for file_path in file_paths:
            self.load_yaml_file(file_path)

    def load_from_directory(self, directory: str, pattern: str = "*.yaml") -> None:
        """从指定目录加载所有匹配的YAML文件"""
        dir_path = Path(directory)
        if not dir_path.exists() or not dir_path.is_dir():
            raise NotADirectoryError(f"目录不存在: {directory}")

        yaml_files = list(dir_path.glob(pattern))
        for yaml_file in yaml_files:
            self.load_yaml_file(str(yaml_file))

    def get_variable(self, name: str) -> Optional[Any]:
        """获取变量值，支持hook扩展

        优先级：
        1. 本地YAML变量
        2. Hook提供的变量

        Args:
            name: 变量名

        Returns:
            变量值，如果不存在返回None
        """
        # 首先从本地变量获取
        if name in self._variables:
            return self._variables[name]

        # 如果启用了hook，尝试通过hook获取
        if self._enable_hooks:
            hook_value = self._get_variable_through_hook(name)
            if hook_value is not None:
                # 可选：将hook获取的变量缓存到本地
                # self._variables[name] = hook_value
                return hook_value

        return None

    def _get_variable_through_hook(self, name: str) -> Optional[Any]:
        """通过hook获取变量值

        Args:
            name: 变量名

        Returns:
            变量值，如果不存在返回None
        """
        try:
            from .hook_manager import hook_manager

            # 确保hook管理器已初始化
            hook_manager.initialize()

            # 如果没有已注册的插件，直接返回
            if not hook_manager.get_plugins():
                return None

            # 尝试从环境变量获取当前环境
            environment = os.environ.get(
                'PYTEST_DSL_ENVIRONMENT') or os.environ.get('ENVIRONMENT')

            # 调用dsl_get_variable hook
            variable_results = hook_manager.pm.hook.dsl_get_variable(
                var_name=name,
                project_id=None,  # 可以根据需要传递project_id
                environment=environment
            )

            # 返回第一个非None的结果
            for result in variable_results:
                if result is not None:
                    return result

            return None

        except Exception as e:
            # Hook调用失败时记录警告但不影响正常流程
            print(f"通过hook获取变量失败: {e}")
            return None

    def get_all_variables(self) -> Dict[str, Any]:
        """获取所有已加载的变量"""
        return self._variables.copy()

    def get_loaded_files(self) -> List[str]:
        """获取已加载的文件列表"""
        return self._loaded_files.copy()

    def set_enable_hooks(self, enable: bool) -> None:
        """设置是否启用hook

        Args:
            enable: 是否启用hook
        """
        self._enable_hooks = enable

    def clear(self) -> None:
        """清除所有已加载的变量"""
        self._variables.clear()
        self._loaded_files.clear()


# 创建全局YAML变量管理器实例
yaml_vars = YAMLVariableManager()
