import os
import json
import tempfile
import allure
from typing import Dict, Any, Optional
from filelock import FileLock
from .request_variables import current_request_variables


class GlobalContext:
    """全局上下文管理器，支持多进程环境下的变量共享"""

    def __init__(self, storage_dir=None):
        # Standalone runs start fresh. pytest points all xdist workers at the
        # same session directory; embedders can explicitly share a directory.
        self._owned_storage = None
        if storage_dir is None:
            self._owned_storage = tempfile.TemporaryDirectory(prefix='pytest-dsl-globals-')
            storage_dir = self._owned_storage.name
        self.configure_storage(storage_dir)
        try:
            self._lock_timeout = float(os.getenv(
                "PYTEST_DSL_GLOBAL_LOCK_TIMEOUT", "30"))
        except (TypeError, ValueError):
            self._lock_timeout = 30.0

        # 初始化变量提供者（延迟加载，避免循环导入）
        self._yaml_provider = None

    def configure_storage(self, storage_dir):
        """Select a run-owned store before starting execution or worker RPCs."""
        self._storage_dir = os.fspath(storage_dir)
        os.makedirs(self._storage_dir, exist_ok=True)
        self._storage_file = os.path.join(self._storage_dir, 'global_vars.json')
        self._lock_file = os.path.join(self._storage_dir, 'global_vars.lock')

    def _lock(self, timeout: Optional[float] = None):
        """Create a bounded lock so callers cannot wait forever.

        A caller-specific timeout lets an outer RPC deadline reserve enough
        time to serialize and return a structured error response.
        """
        effective_timeout = self._lock_timeout if timeout is None else timeout
        return FileLock(self._lock_file, timeout=effective_timeout)

    def _get_yaml_provider(self):
        """延迟获取YAML变量提供者，避免循环导入"""
        if self._yaml_provider is None:
            try:
                from .variable_providers import YAMLVariableProvider
                self._yaml_provider = YAMLVariableProvider()
            except ImportError:
                # 如果变量提供者不可用，创建一个空的提供者
                self._yaml_provider = _EmptyProvider()
        return self._yaml_provider

    def set_variable(self, name: str, value: Any) -> None:
        """设置全局变量"""
        request = current_request_variables()
        if request is not None:
            request.set(name, value)
            if request.isolated:
                return
        with self._lock():
            variables = self._load_variables()
            variables[name] = value
            self._save_variables(variables)

        allure.attach(
            f"全局变量: {name}\n值: {value}",
            name="全局变量设置",
            attachment_type=allure.attachment_type.TEXT
        )

    def set_variables(self, values: Dict[str, Any], attach: bool = True,
                      lock_timeout: Optional[float] = None) -> bool:
        """Set multiple variables with one bounded lock and at most one write.

        Returns ``True`` when the persisted values changed. Repeated remote
        context synchronization can therefore avoid an unnecessary fsync.
        """
        if not values:
            return False

        request = current_request_variables()
        if request is not None:
            changed = any(name not in request.values or request.values[name] != value
                          for name, value in values.items())
            for name, value in values.items():
                request.set(name, value)
            if request.isolated:
                return changed

        with self._lock(timeout=lock_timeout):
            variables = self._load_variables()
            changed = any(
                name not in variables or variables[name] != value
                for name, value in values.items()
            )
            if not changed:
                return False
            variables.update(values)
            self._save_variables(variables)

        if attach:
            names = list(values.keys())
            preview = ", ".join(names[:20])
            if len(names) > 20:
                preview += ", ..."
            allure.attach(
                f"批量设置全局变量: {len(values)} 项\n变量: {preview}",
                name="全局变量批量设置",
                attachment_type=allure.attachment_type.TEXT,
            )
        return True

    def get_variable(self, name: str) -> Any:
        """获取全局变量，优先从YAML变量中获取"""
        request = current_request_variables()
        if request is not None:
            if name in request.deleted:
                return None
            if name in request.values:
                return request.values[name]
            if request.isolated:
                return self._get_yaml_provider().get_variable(name)
        # 首先尝试从YAML变量中获取（通过变量提供者）
        yaml_provider = self._get_yaml_provider()
        yaml_value = yaml_provider.get_variable(name)
        if yaml_value is not None:
            return yaml_value

        # 如果YAML中没有，则从全局变量存储中获取
        with self._lock():
            variables = self._load_variables()
            return variables.get(name)

    def has_variable(self, name: str) -> bool:
        """检查全局变量是否存在（包括YAML变量）"""
        request = current_request_variables()
        if request is not None:
            if name in request.deleted:
                return False
            if name in request.values:
                return True
            if request.isolated:
                return self._get_yaml_provider().has_variable(name)
        # 首先检查YAML变量（通过变量提供者）
        yaml_provider = self._get_yaml_provider()
        if yaml_provider.has_variable(name):
            return True

        # 然后检查全局变量存储
        with self._lock():
            variables = self._load_variables()
            return name in variables

    def delete_variable(self, name: str) -> None:
        """删除全局变量（仅删除存储的变量，不影响YAML变量）"""
        request = current_request_variables()
        if request is not None:
            request.delete(name)
            if request.isolated:
                return
        with self._lock():
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
        request = current_request_variables()
        if request is not None and request.isolated:
            for name in request.global_names:
                request.delete(name)
            return
        with self._lock():
            self._save_variables({})

        # 清除YAML变量（通过变量提供者）
        yaml_provider = self._get_yaml_provider()
        if hasattr(yaml_provider, 'clear'):
            yaml_provider.clear()

        allure.attach(
            "清除所有全局变量",
            name="全局变量清除",
            attachment_type=allure.attachment_type.TEXT
        )

    def get_stored_variables(self, lock_timeout=None) -> Dict[str, Any]:
        """Read the current global source without caching it in local context."""
        request = current_request_variables()
        if request is not None and request.isolated:
            return {name: value for name, value in request.values.items()
                    if name in request.global_names}
        with self._lock(timeout=lock_timeout):
            return self._load_variables()

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
        fd, temp_path = tempfile.mkstemp(
            prefix="global_vars_", suffix=".json", dir=self._storage_dir)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(variables, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, self._storage_file)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class _EmptyProvider:
    """空的变量提供者，用作后备方案"""

    def get_variable(self, key: str) -> Optional[Any]:
        return None

    def has_variable(self, key: str) -> bool:
        return False

    def clear(self):
        pass


# 创建全局上下文管理器实例
global_context = GlobalContext()
