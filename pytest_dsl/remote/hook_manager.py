"""远程服务器Hook管理器

该模块提供了远程服务器的hook机制，支持在服务器生命周期的关键点执行自定义逻辑。
"""

import logging
from typing import Dict, List, Callable, Any
from enum import Enum

logger = logging.getLogger(__name__)


class HookType(Enum):
    """Hook类型枚举"""
    SERVER_STARTUP = "server_startup"
    SERVER_SHUTDOWN = "server_shutdown"
    BEFORE_KEYWORD_EXECUTION = "before_keyword_execution"
    AFTER_KEYWORD_EXECUTION = "after_keyword_execution"


class HookContext:
    """Hook执行上下文"""
    
    def __init__(self, hook_type: HookType, **kwargs):
        self.hook_type = hook_type
        self.data = kwargs
        self.shared_variables = kwargs.get('shared_variables', {})
        
    def get(self, key: str, default=None):
        """获取上下文数据"""
        return self.data.get(key, default)
        
    def set(self, key: str, value: Any):
        """设置上下文数据"""
        self.data[key] = value
        
    def get_shared_variable(self, name: str, default=None):
        """获取共享变量"""
        return self.shared_variables.get(name, default)


class HookManager:
    """Hook管理器"""
    
    def __init__(self):
        self._hooks: Dict[HookType, List[Callable]] = {
            HookType.SERVER_STARTUP: [],
            HookType.SERVER_SHUTDOWN: [],
            HookType.BEFORE_KEYWORD_EXECUTION: [],
            HookType.AFTER_KEYWORD_EXECUTION: []
        }
        
    def register_hook(self, hook_type: HookType, hook_func: Callable):
        """注册hook函数
        
        Args:
            hook_type: Hook类型
            hook_func: Hook函数，接收HookContext参数
        """
        if hook_type not in self._hooks:
            raise ValueError(f"不支持的hook类型: {hook_type}")
            
        self._hooks[hook_type].append(hook_func)
        logger.info(f"注册hook: {hook_type.value} -> {hook_func.__name__}")
        
    def execute_hooks(self, hook_type: HookType, **context_data) -> HookContext:
        """执行指定类型的所有hook
        
        Args:
            hook_type: Hook类型
            **context_data: 传递给hook的上下文数据
            
        Returns:
            HookContext: 执行后的上下文
        """
        context = HookContext(hook_type, **context_data)
        
        hooks = self._hooks.get(hook_type, [])
        if not hooks:
            logger.debug(f"没有注册的hook: {hook_type.value}")
            return context
            
        logger.debug(f"执行{len(hooks)}个hook: {hook_type.value}")
        
        for hook_func in hooks:
            try:
                logger.debug(f"执行hook: {hook_func.__name__}")
                hook_func(context)
            except Exception as e:
                logger.error(f"Hook执行失败 {hook_func.__name__}: {str(e)}")
                # 继续执行其他hook，不因为一个hook失败而中断
                
        return context
        
    def get_registered_hooks(self, hook_type: HookType = None) -> Dict[HookType, List[str]]:
        """获取已注册的hook信息
        
        Args:
            hook_type: 指定hook类型，None表示获取所有
            
        Returns:
            Dict: hook类型到函数名列表的映射
        """
        result = {}
        
        if hook_type:
            hooks = self._hooks.get(hook_type, [])
            result[hook_type] = [hook.__name__ for hook in hooks]
        else:
            for ht, hooks in self._hooks.items():
                result[ht] = [hook.__name__ for hook in hooks]
                
        return result
        
    def clear_hooks(self, hook_type: HookType = None):
        """清除hook
        
        Args:
            hook_type: 指定hook类型，None表示清除所有
        """
        if hook_type:
            self._hooks[hook_type] = []
            logger.info(f"清除hook: {hook_type.value}")
        else:
            for ht in self._hooks:
                self._hooks[ht] = []
            logger.info("清除所有hook")


# 全局hook管理器实例
hook_manager = HookManager()


def register_startup_hook(func: Callable):
    """装饰器：注册服务器启动hook"""
    hook_manager.register_hook(HookType.SERVER_STARTUP, func)
    return func


def register_shutdown_hook(func: Callable):
    """装饰器：注册服务器关闭hook"""
    hook_manager.register_hook(HookType.SERVER_SHUTDOWN, func)
    return func


def register_before_keyword_hook(func: Callable):
    """装饰器：注册关键字执行前hook"""
    hook_manager.register_hook(HookType.BEFORE_KEYWORD_EXECUTION, func)
    return func


def register_after_keyword_hook(func: Callable):
    """装饰器：注册关键字执行后hook"""
    hook_manager.register_hook(HookType.AFTER_KEYWORD_EXECUTION, func)
    return func
