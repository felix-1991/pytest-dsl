from pytest_dsl.core.keyword_manager import keyword_manager
from pytest_dsl.core.global_context import global_context


@keyword_manager.register(
    name="设置全局变量",
    parameters=[
        {"name": "变量名", "mapping": "name", "description": "全局变量的名称"},
        {"name": "值", "mapping": "value", "description": "全局变量的值"}
    ]
)
def set_global_variable(name, value, context):
    """设置全局变量"""
    global_context.set_variable(name, value)
    return value


@keyword_manager.register(
    name="获取全局变量",
    parameters=[
        {"name": "变量名", "mapping": "name", "description": "全局变量的名称"}
    ]
)
def get_global_variable(name, context):
    """获取全局变量"""
    value = global_context.get_variable(name)
    if value is None:
        raise Exception(f"全局变量未定义: {name}")
    return value


@keyword_manager.register(
    name="删除全局变量",
    parameters=[
        {"name": "变量名", "mapping": "name", "description": "全局变量的名称"}
    ]
)
def delete_global_variable(name, context):
    """删除全局变量"""
    global_context.delete_variable(name)
    return True


@keyword_manager.register(
    name="清除所有全局变量",
    parameters=[]
)
def clear_all_global_variables(context):
    """清除所有全局变量"""
    global_context.clear_all()
    return True
