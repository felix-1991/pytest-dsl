"""
pytest-dsl hook管理器

管理插件的注册、发现和调用
"""
import pluggy
from typing import Optional, List, Any
from .hookspecs import DSLHookSpecs


class DSLHookManager:
    """DSL Hook管理器"""
    
    _instance: Optional['DSLHookManager'] = None
    
    def __init__(self):
        self.pm: pluggy.PluginManager = pluggy.PluginManager("pytest_dsl")
        self.pm.add_hookspecs(DSLHookSpecs)
        self._initialized = False
    
    @classmethod
    def get_instance(cls) -> 'DSLHookManager':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def register_plugin(self, plugin: Any, name: Optional[str] = None) -> None:
        """注册插件
        
        Args:
            plugin: 插件实例或模块
            name: 插件名称（可选）
        """
        self.pm.register(plugin, name=name)
    
    def unregister_plugin(self, plugin: Any = None, 
                          name: Optional[str] = None) -> None:
        """注销插件
        
        Args:
            plugin: 插件实例或模块
            name: 插件名称
        """
        self.pm.unregister(plugin=plugin, name=name)
    
    def is_registered(self, plugin: Any) -> bool:
        """检查插件是否已注册"""
        return self.pm.is_registered(plugin)
    
    def load_setuptools_entrypoints(self, group: str = "pytest_dsl") -> int:
        """加载setuptools入口点插件
        
        Args:
            group: 入口点组名
            
        Returns:
            加载的插件数量
        """
        return self.pm.load_setuptools_entrypoints(group)
    
    def get_plugins(self) -> List[Any]:
        """获取所有已注册的插件"""
        return self.pm.get_plugins()
    
    def hook(self) -> Any:
        """获取hook调用器"""
        return self.pm.hook
    
    def initialize(self) -> None:
        """初始化hook管理器"""
        if self._initialized:
            return
        
        # 尝试加载setuptools入口点插件
        try:
            loaded = self.load_setuptools_entrypoints()
            if loaded > 0:
                print(f"加载了 {loaded} 个插件")
        except Exception as e:
            print(f"加载插件时出现错误: {e}")
        
        self._initialized = True


# 全局hook管理器实例
hook_manager = DSLHookManager.get_instance() 