"""远程服务器变量桥接模块

该模块提供了变量桥接机制，让远程服务器中的关键字能够无缝访问客户端同步的变量。
通过hook机制拦截变量访问，实现变量的透明传递。
"""

import logging
from typing import Any, Optional
from pytest_dsl.remote.hook_manager import register_startup_hook, register_before_keyword_hook
from pytest_dsl.core.yaml_vars import yaml_vars
from pytest_dsl.core.global_context import global_context

logger = logging.getLogger(__name__)


class VariableBridge:
    """变量桥接器，负责在远程服务器中桥接客户端同步的变量"""
    
    def __init__(self):
        self.shared_variables = {}  # 引用远程服务器的shared_variables
        self.original_yaml_get_variable = None
        self.original_global_get_variable = None
        self._bridge_installed = False
    
    def install_bridge(self, shared_variables: dict):
        """安装变量桥接机制
        
        Args:
            shared_variables: 远程服务器的共享变量字典
        """
        if self._bridge_installed:
            return
            
        self.shared_variables = shared_variables
        
        # 备份原始方法
        self.original_yaml_get_variable = yaml_vars.get_variable
        self.original_global_get_variable = global_context.get_variable
        
        # 安装桥接方法
        yaml_vars.get_variable = self._bridged_yaml_get_variable
        global_context.get_variable = self._bridged_global_get_variable
        
        self._bridge_installed = True
        logger.info("变量桥接机制已安装")
    
    def _bridged_yaml_get_variable(self, name: str) -> Optional[Any]:
        """桥接的YAML变量获取方法
        
        优先级：
        1. 原始YAML变量
        2. 客户端同步的变量
        """
        # 首先尝试从原始YAML变量获取
        original_value = self.original_yaml_get_variable(name)
        if original_value is not None:
            return original_value
        
        # 如果原始YAML中没有，尝试从同步变量获取
        if name in self.shared_variables:
            logger.debug(f"从同步变量获取YAML变量: {name}")
            return self.shared_variables[name]
        
        return None
    
    def _bridged_global_get_variable(self, name: str) -> Any:
        """桥接的全局变量获取方法
        
        优先级：
        1. 原始全局变量（包括YAML变量）
        2. 客户端同步的变量
        """
        try:
            # 首先尝试从原始全局上下文获取
            original_value = self.original_global_get_variable(name)
            if original_value is not None:
                return original_value
        except:
            # 如果原始方法抛出异常，继续尝试同步变量
            pass
        
        # 如果原始全局变量中没有，尝试从同步变量获取
        if name in self.shared_variables:
            logger.debug(f"从同步变量获取全局变量: {name}")
            return self.shared_variables[name]
        
        # 如果都没有找到，返回None（保持原有行为）
        return None
    
    def uninstall_bridge(self):
        """卸载变量桥接机制"""
        if not self._bridge_installed:
            return
            
        # 恢复原始方法
        if self.original_yaml_get_variable:
            yaml_vars.get_variable = self.original_yaml_get_variable
        if self.original_global_get_variable:
            global_context.get_variable = self.original_global_get_variable
        
        self._bridge_installed = False
        logger.info("变量桥接机制已卸载")


# 全局变量桥接器实例
variable_bridge = VariableBridge()


@register_startup_hook
def setup_variable_bridge(context):
    """服务器启动时安装变量桥接机制"""
    shared_variables = context.get('shared_variables')
    if shared_variables is not None:
        variable_bridge.install_bridge(shared_variables)
        logger.info("变量桥接机制已在服务器启动时安装")
    else:
        logger.warning("无法获取shared_variables，变量桥接机制安装失败")


@register_before_keyword_hook
def ensure_variable_bridge(context):
    """关键字执行前确保变量桥接机制正常工作"""
    # 这个hook主要用于调试和监控
    shared_variables = context.get('shared_variables')
    keyword_name = context.get('keyword_name')
    
    # 只对特定关键字进行调试日志
    if keyword_name in ['HTTP请求', '数据库查询'] and shared_variables:
        synced_count = len(shared_variables)
        if synced_count > 0:
            logger.debug(f"关键字 {keyword_name} 执行前，可用同步变量数量: {synced_count}")


def get_synced_variable(name: str) -> Optional[Any]:
    """直接从同步变量中获取变量值
    
    Args:
        name: 变量名
        
    Returns:
        变量值，如果不存在则返回None
    """
    return variable_bridge.shared_variables.get(name)


def list_synced_variables() -> dict:
    """列出所有同步的变量
    
    Returns:
        同步变量字典的副本
    """
    return variable_bridge.shared_variables.copy()


def has_synced_variable(name: str) -> bool:
    """检查是否存在指定的同步变量
    
    Args:
        name: 变量名
        
    Returns:
        是否存在该同步变量
    """
    return name in variable_bridge.shared_variables
