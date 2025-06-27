class TestContext:
    def __init__(self):
        self._data = {}
        self._external_providers = []  # 外部变量提供者列表

    def set(self, key: str, value: any) -> None:
        """设置上下文变量"""
        self._data[key] = value

    def get(self, key: str, default=None) -> any:
        """获取上下文变量，遵循变量优先级：本地变量 > 外部提供者变量"""
        # 1. 首先检查本地变量
        if key in self._data:
            return self._data[key]

        # 2. 检查外部提供者（按注册顺序）
        for provider in self._external_providers:
            if hasattr(provider, 'get_variable'):
                value = provider.get_variable(key)
                if value is not None:
                    return value

        # 3. 返回默认值
        return default

    def has(self, key: str) -> bool:
        """检查上下文变量是否存在（包括外部提供者）"""
        # 检查本地变量
        if key in self._data:
            return True

        # 检查外部提供者
        for provider in self._external_providers:
            if hasattr(provider, 'get_variable'):
                value = provider.get_variable(key)
                if value is not None:
                    return True

        return False

    def clear(self) -> None:
        """清空上下文"""
        self._data.clear()

    def get_local_variables(self) -> dict:
        """获取所有本地变量"""
        return self._data

    def get_all_context_variables(self) -> dict:
        """获取所有上下文变量，包括本地变量和外部提供者变量
        
        Returns:
            包含所有上下文变量的字典，本地变量优先级高于外部变量
        """
        all_variables = {}
        
        # 1. 先添加外部提供者的变量
        for provider in self._external_providers:
            if hasattr(provider, 'get_all_variables'):
                try:
                    external_vars = provider.get_all_variables()
                    if isinstance(external_vars, dict):
                        all_variables.update(external_vars)
                except Exception as e:
                    print(f"警告：获取外部变量提供者变量时发生错误: {e}")
        
        # 2. 再添加本地变量（覆盖同名的外部变量）
        all_variables.update(self._data)
        
        return all_variables

    def register_external_variable_provider(self, provider) -> None:
        """注册外部变量提供者

        Args:
            provider: 变量提供者，需要实现get_variable(key)方法
        """
        if provider not in self._external_providers:
            self._external_providers.append(provider)

    def sync_variables_from_external_sources(self) -> None:
        """将外部变量提供者中的常用变量同步到本地缓存中，提高访问性能

        这个方法会调用所有外部提供者的get_all_variables方法，
        将常用变量缓存到本地_data字典中，以提高后续访问的性能。
        注意：本地变量的优先级仍然高于外部变量。
        """
        for provider in self._external_providers:
            if hasattr(provider, 'get_all_variables'):
                try:
                    # 获取提供者的所有变量
                    external_vars = provider.get_all_variables()
                    if isinstance(external_vars, dict):
                        # 只同步那些本地还没有的变量，保持本地变量的优先级
                        for key, value in external_vars.items():
                            if key not in self._data:
                                self._data[key] = value
                except Exception as e:
                    # 如果某个提供者同步失败，记录警告但继续处理其他提供者
                    print(f"警告：同步外部变量提供者变量时发生错误: {e}")
