class TestContext:
    def __init__(self):
        self._data = {}

    def set(self, key: str, value: any) -> None:
        """设置上下文变量"""
        self._data[key] = value

    def get(self, key: str, default=None) -> any:
        """获取上下文变量，如果不存在返回默认值"""
        return self._data.get(key, default)

    def has(self, key: str) -> bool:
        """检查上下文变量是否存在"""
        return key in self._data

    def clear(self) -> None:
        """清空上下文"""
        self._data.clear()

    def get_local_variables(self) -> dict:
        """获取所有本地变量"""
        return self._data 