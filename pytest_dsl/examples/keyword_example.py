"""
示例: 如何在您的项目中创建自定义关键字

将该文件放在您项目的 keywords 目录下，
例如: my_project/keywords/my_keywords.py

pytest-dsl 会自动导入这些关键字。
"""

from pytest_dsl.core.keyword_manager import keyword_manager

# 示例1: 简单关键字
@keyword_manager.register('打印消息', [
    {'name': '消息', 'mapping': 'message', 'description': '要打印的消息内容'},
])
def print_message(**kwargs):
    """打印一条消息到控制台
    
    Args:
        message: 要打印的消息
        context: 测试上下文 (自动传入)
    """
    message = kwargs.get('message', '')
    print(f"自定义关键字消息: {message}")
    return True

# 示例2: 带返回值的关键字
@keyword_manager.register('生成随机数', [
    {'name': '最小值', 'mapping': 'min_value', 'description': '随机数范围最小值'},
    {'name': '最大值', 'mapping': 'max_value', 'description': '随机数范围最大值'},
])
def generate_random(**kwargs):
    """生成指定范围内的随机整数
    
    Args:
        min_value: 最小值
        max_value: 最大值
        context: 测试上下文 (自动传入)
        
    Returns:
        随机整数
    """
    import random
    min_value = int(kwargs.get('min_value', 1))
    max_value = int(kwargs.get('max_value', 100))
    
    result = random.randint(min_value, max_value)
    return result

# 示例3: 操作上下文的关键字
@keyword_manager.register('保存到上下文', [
    {'name': '键名', 'mapping': 'key', 'description': '保存在上下文中的键名'},
    {'name': '值', 'mapping': 'value', 'description': '要保存的值'},
])
def save_to_context(**kwargs):
    """将值保存到测试上下文中
    
    Args:
        key: 键名
        value: 要保存的值
        context: 测试上下文 (自动传入)
    """
    key = kwargs.get('key')
    value = kwargs.get('value')
    context = kwargs.get('context')
    
    if key and context:
        context.set(key, value)
        return True
    return False 