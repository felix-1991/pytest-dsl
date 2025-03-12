from typing import Any
from core.keyword_manager import keyword_manager

# 用于存储计算结果的变量
_result = None

@keyword_manager.register('计算加法', [
    {'name': '第一个数', 'mapping': 'a', 'description': '第一个操作数'},
    {'name': '第二个数', 'mapping': 'b', 'description': '第二个操作数'}
])
def add(**kwargs) -> float:
    """
    计算两个数的和
    
    Args:
        kwargs: 包含 a 和 b 两个参数的字典
        
    Returns:
        float: 计算结果
    """
    global _result
    try:
        a = kwargs.get('a')
        b = kwargs.get('b')
        _result = float(a) + float(b)
        return _result
    except (ValueError, TypeError) as e:
        raise ValueError(f"无效的输入: {e}")

@keyword_manager.register('计算减法', [
    {'name': '第一个数', 'mapping': 'a', 'description': '被减数'},
    {'name': '第二个数', 'mapping': 'b', 'description': '减数'}
])
def subtract(**kwargs) -> float:
    """
    计算两个数的差
    
    Args:
        kwargs: 包含 a 和 b 两个参数的字典
        
    Returns:
        float: 计算结果
    """
    global _result
    try:
        a = kwargs.get('a')
        b = kwargs.get('b')
        _result = float(a) - float(b)
        return _result
    except (ValueError, TypeError) as e:
        raise ValueError(f"无效的输入: {e}")

@keyword_manager.register('获取计算结果', [])
def get_result(**kwargs) -> float:
    """
    获取最近一次计算的结果
    
    Returns:
        float: 最近一次计算的结果
    """
    global _result
    if _result is None:
        raise ValueError("还没有进行任何计算")
    return _result

