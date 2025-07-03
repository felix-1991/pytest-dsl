from pytest_dsl.core.keyword_manager import keyword_manager
from pytest_dsl.core.global_context import global_context


@keyword_manager.register(
    name="设置全局变量",
    parameters=[
        {"name": "变量名", "mapping": "name", "description": "全局变量的名称"},
        {"name": "值", "mapping": "value", "description": "全局变量的值"}
    ],
    category='系统/全局变量',
    tags=['全局', '设置']
)
def set_global_variable(name, value, context):
    """设置全局变量"""
    global_context.set_variable(name, value)

    # 统一返回格式 - 支持远程关键字模式
    return {
        "result": value,  # 主要返回值保持兼容
        "captures": {},
        "session_state": {},
        "metadata": {
            "variable_name": name,
            "operation": "set_global_variable"
        }
    }


@keyword_manager.register(
    name="获取全局变量",
    parameters=[
        {"name": "变量名", "mapping": "name", "description": "全局变量的名称"}
    ],
    category='系统/全局变量',
    tags=['全局', '获取']
)
def get_global_variable(name, context):
    """获取全局变量"""
    value = global_context.get_variable(name)
    if value is None:
        raise Exception(f"全局变量未定义: {name}")

    # 统一返回格式 - 支持远程关键字模式
    return {
        "result": value,  # 主要返回值保持兼容
        "captures": {},
        "session_state": {},
        "metadata": {
            "variable_name": name,
            "operation": "get_global_variable"
        }
    }


@keyword_manager.register(
    name="删除全局变量",
    parameters=[
        {"name": "变量名", "mapping": "name", "description": "全局变量的名称"}
    ],
    category='系统/全局变量',
    tags=['全局', '删除']
)
def delete_global_variable(name, context):
    """删除全局变量"""
    global_context.delete_variable(name)

    # 统一返回格式 - 支持远程关键字模式
    return {
        "result": True,  # 主要返回值保持兼容
        "captures": {},
        "session_state": {},
        "metadata": {
            "variable_name": name,
            "operation": "delete_global_variable"
        }
    }


@keyword_manager.register(
    name="清除所有全局变量",
    parameters=[],
    category='系统/全局变量',
    tags=['全局', '清除']
)
def clear_all_global_variables(context):
    """清除所有全局变量"""
    global_context.clear_all()

    # 统一返回格式 - 支持远程关键字模式
    return {
        "result": True,  # 主要返回值保持兼容
        "captures": {},
        "session_state": {},
        "metadata": {
            "operation": "clear_all_global_variables"
        }
    }
