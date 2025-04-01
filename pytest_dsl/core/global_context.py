import os
import json
import tempfile
import allure
from typing import Dict, Any, Optional
from filelock import FileLock
from .yaml_vars import yaml_vars


class GlobalContext:
    """全局上下文管理器，支持多进程环境下的变量共享"""

    def __init__(self):
        # 使用临时目录存储全局变量
        self._storage_dir = os.path.join(
            tempfile.gettempdir(), "pytest_dsl_global_vars")
        os.makedirs(self._storage_dir, exist_ok=True)
        self._storage_file = os.path.join(
            self._storage_dir, "global_vars.json")
        self._lock_file = os.path.join(self._storage_dir, "global_vars.lock")

    def set_variable(self, name: str, value: Any) -> None:
        """设置全局变量"""
        with FileLock(self._lock_file):
            variables = self._load_variables()
            variables[name] = value
            self._save_variables(variables)

        allure.attach(
            f"全局变量: {name}\n值: {value}",
            name="全局变量设置",
            attachment_type=allure.attachment_type.TEXT
        )

    def get_variable(self, name: str) -> Any:
        """获取全局变量，优先从YAML变量中获取"""
        # 首先尝试从YAML变量中获取
        yaml_value = yaml_vars.get_variable(name)
        if yaml_value is not None:
            return yaml_value

        # 如果YAML中没有，则从全局变量存储中获取
        with FileLock(self._lock_file):
            variables = self._load_variables()
            return variables.get(name)

    def has_variable(self, name: str) -> bool:
        """检查全局变量是否存在（包括YAML变量）"""
        # 首先检查YAML变量
        if yaml_vars.get_variable(name) is not None:
            return True

        # 然后检查全局变量存储
        with FileLock(self._lock_file):
            variables = self._load_variables()
            return name in variables

    def delete_variable(self, name: str) -> None:
        """删除全局变量（仅删除存储的变量，不影响YAML变量）"""
        with FileLock(self._lock_file):
            variables = self._load_variables()
            if name in variables:
                del variables[name]
                self._save_variables(variables)

        allure.attach(
            f"删除全局变量: {name}",
            name="全局变量删除",
            attachment_type=allure.attachment_type.TEXT
        )

    def clear_all(self) -> None:
        """清除所有全局变量（包括YAML变量）"""
        with FileLock(self._lock_file):
            self._save_variables({})
        
        # 清除YAML变量
        yaml_vars.clear()

        allure.attach(
            "清除所有全局变量",
            name="全局变量清除",
            attachment_type=allure.attachment_type.TEXT
        )

    def _load_variables(self) -> Dict[str, Any]:
        """从文件加载变量"""
        if not os.path.exists(self._storage_file):
            return {}
        try:
            with open(self._storage_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_variables(self, variables: Dict[str, Any]) -> None:
        """保存变量到文件"""
        with open(self._storage_file, 'w', encoding='utf-8') as f:
            json.dump(variables, f, ensure_ascii=False, indent=2)


# 创建全局上下文管理器实例
global_context = GlobalContext()
