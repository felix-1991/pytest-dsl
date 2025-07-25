"""
远程关键字返回处理器模块

提供通用的返回数据处理机制，支持插件化扩展
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class RemoteReturnHandler(ABC):
    """远程关键字返回处理器基类"""
    
    @abstractmethod
    def can_handle(self, return_data: Dict[str, Any]) -> bool:
        """判断是否能处理此返回数据
        
        Args:
            return_data: 远程关键字返回的数据
            
        Returns:
            bool: 是否能处理
        """
        pass
    
    @abstractmethod
    def process(self, return_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
        """处理返回数据
        
        Args:
            return_data: 远程关键字返回的数据
            context: 执行上下文（可选）
            
        Returns:
            处理后的数据
        """
        pass
    
    @property
    @abstractmethod
    def priority(self) -> int:
        """处理器优先级，数字越小优先级越高"""
        pass


class HTTPReturnHandler(RemoteReturnHandler):
    """HTTP请求关键字返回处理器"""

    def can_handle(self, return_data: Dict[str, Any]) -> bool:
        """检查是否为HTTP请求关键字的返回格式"""
        return (isinstance(return_data, dict) and
                return_data.get('metadata', {}).get('keyword_type') == 'http_request')

    def process(self, return_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
        """处理HTTP请求关键字的返回数据"""
        logger.debug("使用HTTP返回处理器处理数据")

        # HTTP关键字已经使用新格式，直接返回
        return return_data

    @property
    def priority(self) -> int:
        return 10


class AssertionReturnHandler(RemoteReturnHandler):
    """断言关键字返回处理器"""

    def can_handle(self, return_data: Dict[str, Any]) -> bool:
        """检查是否为断言关键字的返回格式"""
        return (isinstance(return_data, dict) and
                'metadata' in return_data and
                'jsonpath' in return_data.get('metadata', {}))

    def process(self, return_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
        """处理断言关键字的返回数据"""
        logger.debug("使用断言返回处理器处理数据")

        # 如果已经是新格式，直接返回
        if 'side_effects' in return_data:
            return return_data

        # 转换旧格式为新格式
        side_effects = {}

        # 处理变量捕获
        if 'captures' in return_data:
            side_effects['variables'] = return_data['captures']

        return {
            'result': return_data.get('result'),
            'side_effects': side_effects,
            'metadata': return_data.get('metadata', {})
        }

    @property
    def priority(self) -> int:
        return 20


class DefaultReturnHandler(RemoteReturnHandler):
    """默认返回处理器，处理简单格式"""
    
    def can_handle(self, return_data: Dict[str, Any]) -> bool:
        """总是能处理，作为兜底处理器"""
        return True
    
    def process(self, return_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
        """处理简单的返回数据"""
        logger.debug("使用默认返回处理器处理数据")
        
        if isinstance(return_data, dict):
            if 'result' in return_data:
                return {
                    'result': return_data['result'],
                    'side_effects': {},
                    'metadata': return_data.get('metadata', {})
                }
            else:
                return {
                    'result': return_data,
                    'side_effects': {},
                    'metadata': {}
                }
        else:
            return {
                'result': return_data,
                'side_effects': {},
                'metadata': {}
            }
    
    @property
    def priority(self) -> int:
        return 100  # 最低优先级


class ReturnHandlerRegistry:
    """返回处理器注册表"""
    
    def __init__(self):
        self._handlers: List[RemoteReturnHandler] = []
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """注册默认处理器"""
        self.register(HTTPReturnHandler())
        self.register(AssertionReturnHandler())
        self.register(DefaultReturnHandler())
    
    def register(self, handler: RemoteReturnHandler):
        """注册返回处理器
        
        Args:
            handler: 返回处理器实例
        """
        self._handlers.append(handler)
        # 按优先级排序
        self._handlers.sort(key=lambda h: h.priority)
        logger.debug(f"注册返回处理器: {handler.__class__.__name__}")
    
    def process(self, return_data: Any, context: Any = None) -> Any:
        """处理返回数据
        
        Args:
            return_data: 返回数据
            context: 执行上下文
            
        Returns:
            处理后的数据
        """
        if not isinstance(return_data, dict):
            return return_data
            
        # 按优先级查找合适的处理器
        for handler in self._handlers:
            if handler.can_handle(return_data):
                logger.debug(f"使用处理器: {handler.__class__.__name__}")
                return handler.process(return_data, context)
        
        # 理论上不会到这里，因为DefaultReturnHandler总是能处理
        logger.warning("没有找到合适的返回处理器")
        return return_data


# 全局注册表实例
return_handler_registry = ReturnHandlerRegistry()


def register_return_handler(handler: RemoteReturnHandler):
    """注册返回处理器的便捷函数
    
    Args:
        handler: 返回处理器实例
    """
    return_handler_registry.register(handler)
