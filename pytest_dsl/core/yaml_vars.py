import os
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path


class YAMLVariableManager:
    """管理YAML格式的变量文件"""

    def __init__(self):
        self._loaded_files: List[str] = []
        self._variables: Dict[str, Any] = {}

    def has_variable(self, name: str) -> bool:
        """检查变量是否存在
        
        Args:
            name: 变量名
            
        Returns:
            bool: 变量是否存在
        """
        return name in self._variables

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
        """获取变量值"""
        return self._variables.get(name)

    def get_all_variables(self) -> Dict[str, Any]:
        """获取所有已加载的变量"""
        return self._variables.copy()

    def get_loaded_files(self) -> List[str]:
        """获取已加载的文件列表"""
        return self._loaded_files.copy()

    def clear(self) -> None:
        """清除所有已加载的变量"""
        self._variables.clear()
        self._loaded_files.clear()


# 创建全局YAML变量管理器实例
yaml_vars = YAMLVariableManager() 