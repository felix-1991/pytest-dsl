import allure
import time
import random
import string
import subprocess
import datetime
import logging
from pytest_dsl.core.keyword_manager import keyword_manager


@keyword_manager.register('打印', [
    {'name': '内容', 'mapping': 'content', 'description': '要打印的文本内容'}
], category='系统/调试', tags=['输出', '调试'])
def print_content(**kwargs):
    content = kwargs.get('content')
    print(f"内容: {content}")


@keyword_manager.register('返回结果', [
    {'name': '结果', 'mapping': 'result', 'description': '要返回的结果值'}
], category='系统/调试', tags=['返回'])
def return_result(**kwargs):
    return kwargs.get('result')


@keyword_manager.register('等待', [
    {'name': '秒数', 'mapping': 'seconds',
     'description': '等待的秒数，可以是小数', 'default': 1}
], category='系统/通用', tags=['等待', '延迟'])
def wait_seconds(**kwargs):
    """等待指定的时间

    Args:
        seconds: 等待的秒数，默认为1秒
    """
    seconds = float(kwargs.get('seconds', 1))

    with allure.step(f"等待 {seconds} 秒"):
        time.sleep(seconds)
        allure.attach(
            f"等待时间: {seconds} 秒",
            name="等待完成",
            attachment_type=allure.attachment_type.TEXT
        )


@keyword_manager.register('获取当前时间', [
    {'name': '格式', 'mapping': 'format',
     'description': '时间格式，例如 "%Y-%m-%d %H:%M:%S"', 'default': 'timestamp'},
    {'name': '时区', 'mapping': 'timezone',
     'description': '时区，例如 "Asia/Shanghai"', 'default': 'Asia/Shanghai'}
], category='系统/通用', tags=['时间', '获取'])
def get_current_time(**kwargs):
    """获取当前时间

    Args:
        format: 时间格式，如果设置为'timestamp'则返回时间戳
        timezone: 时区，默认为Asia/Shanghai

    Returns:
        str/float: 格式化的时间字符串或时间戳
    """
    format_str = kwargs.get('format', 'timestamp')
    timezone_str = kwargs.get('timezone', 'Asia/Shanghai')

    # 获取当前时间
    if timezone_str and timezone_str != 'local':
        import pytz
        try:
            tz = pytz.timezone(timezone_str)
            current_time = datetime.datetime.now(tz)
        except Exception as e:
            allure.attach(
                f"时区设置异常: {str(e)}，使用本地时区",
                name="时区设置异常",
                attachment_type=allure.attachment_type.TEXT
            )
            current_time = datetime.datetime.now()
    else:
        current_time = datetime.datetime.now()

    # 格式化时间
    if format_str and format_str != 'timestamp':
        try:
            result = current_time.strftime(format_str)
        except Exception as e:
            allure.attach(
                f"时间格式化异常: {str(e)}，返回默认格式",
                name="时间格式化异常",
                attachment_type=allure.attachment_type.TEXT
            )
            result = current_time.strftime('%Y-%m-%d %H:%M:%S')
    else:
        # 返回时间戳
        result = int(current_time.timestamp())

    return result


@keyword_manager.register('生成随机字符串', [
    {'name': '长度', 'mapping': 'length',
     'description': '随机字符串的长度', 'default': 8},
    {'name': '类型', 'mapping': 'type',
     'description': '字符类型：字母(letters)、数字(digits)、字母数字(alphanumeric)、全部(all)',
     'default': 'alphanumeric'}
], category='系统/通用', tags=['随机', '字符串'])
def generate_random_string(**kwargs):
    """生成指定长度和类型的随机字符串

    Args:
        length: 字符串长度
        type: 字符类型

    Returns:
        str: 生成的随机字符串
    """
    length = int(kwargs.get('length', 8))
    char_type = kwargs.get('type', 'alphanumeric').lower()

    # 根据类型选择字符集
    if char_type == 'letters':
        chars = string.ascii_letters
    elif char_type == 'digits':
        chars = string.digits
    elif char_type == 'alphanumeric':
        chars = string.ascii_letters + string.digits
    elif char_type == 'all':
        chars = string.ascii_letters + string.digits + string.punctuation
    else:
        # 默认使用字母数字
        chars = string.ascii_letters + string.digits

    # 生成随机字符串
    result = ''.join(random.choice(chars) for _ in range(length))

    with allure.step(f"生成随机字符串: 长度={length}, 类型={char_type}"):
        allure.attach(
            f"生成的随机字符串: {result}",
            name="随机字符串",
            attachment_type=allure.attachment_type.TEXT
        )

    return result


@keyword_manager.register('生成随机数', [
    {'name': '最小值', 'mapping': 'min',
     'description': '随机数的最小值', 'default': 0},
    {'name': '最大值', 'mapping': 'max',
     'description': '随机数的最大值', 'default': 100},
    {'name': '小数位数', 'mapping': 'decimals',
     'description': '小数位数，0表示整数', 'default': 0}
], category='系统/通用', tags=['随机', '数字'])
def generate_random_number(**kwargs):
    """生成指定范围内的随机数

    Args:
        min: 随机数的最小值
        max: 随机数的最大值
        decimals: 小数位数，0表示整数

    Returns:
        int/float: 生成的随机数
    """
    min_value = float(kwargs.get('min', 0))
    max_value = float(kwargs.get('max', 100))
    decimals = int(kwargs.get('decimals', 0))

    if decimals <= 0:
        # 生成整数
        result = random.randint(int(min_value), int(max_value))
    else:
        # 生成浮点数
        result = round(random.uniform(min_value, max_value), decimals)

    with allure.step(f"生成随机数: 范围=[{min_value}, {max_value}], 小数位数={decimals}"):
        allure.attach(
            f"生成的随机数: {result}",
            name="随机数",
            attachment_type=allure.attachment_type.TEXT
        )

    return result


@keyword_manager.register('字符串操作', [
    {'name': '操作', 'mapping': 'operation',
     'description': '操作类型：拼接(concat)、替换(replace)、分割(split)、'
                   '大写(upper)、小写(lower)、去空格(strip)',
     'default': 'strip'},
    {'name': '字符串', 'mapping': 'string', 'description': '要操作的字符串'},
    {'name': '参数1', 'mapping': 'param1',
     'description': '操作参数1，根据操作类型不同而不同', 'default': ''},
    {'name': '参数2', 'mapping': 'param2',
     'description': '操作参数2，根据操作类型不同而不同', 'default': ''}
], category='系统/通用', tags=['字符串', '操作'])
def string_operation(**kwargs):
    """字符串操作

    Args:
        operation: 操作类型，默认为strip（去空格）
        string: 要操作的字符串
        param1: 操作参数1，默认为空字符串
        param2: 操作参数2，默认为空字符串

    Returns:
        str: 操作结果
    """
    operation = kwargs.get('operation', 'strip').lower()
    string = str(kwargs.get('string', ''))
    param1 = kwargs.get('param1', '')
    param2 = kwargs.get('param2', '')

    result = string

    if operation == 'concat':
        # 拼接字符串
        result = string + str(param1)
    elif operation == 'replace':
        # 替换字符串
        result = string.replace(str(param1), str(param2))
    elif operation == 'split':
        # 分割字符串
        if param1:  # 如果提供了分隔符
            result = string.split(str(param1))
            if param2 and param2.isdigit():
                # 如果提供了索引，返回指定位置的元素
                index = int(param2)
                if 0 <= index < len(result):
                    result = result[index]
        else:
            # 默认按空格分割
            result = string.split()
    elif operation == 'upper':
        # 转大写
        result = string.upper()
    elif operation == 'lower':
        # 转小写
        result = string.lower()
    elif operation == 'strip':
        # 去空格（默认操作）
        result = string.strip()
    else:
        # 未知操作，返回原字符串
        allure.attach(
            f"未知的字符串操作: {operation}，使用默认操作strip",
            name="字符串操作错误",
            attachment_type=allure.attachment_type.TEXT
        )
        result = string.strip()

    with allure.step(f"字符串操作: {operation}"):
        allure.attach(
            f"原字符串: {string}\n操作: {operation}\n参数1: {param1}\n"
            f"参数2: {param2}\n结果: {result}",
            name="字符串操作结果",
            attachment_type=allure.attachment_type.TEXT
        )

    return result


@keyword_manager.register('日志', [
    {'name': '级别', 'mapping': 'level',
     'description': '日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL',
     'default': 'INFO'},
    {'name': '消息', 'mapping': 'message', 'description': '日志消息内容'}
], category='系统/调试', tags=['日志'])
def log_message(**kwargs):
    """记录日志

    Args:
        level: 日志级别
        message: 日志消息内容
    """
    level = kwargs.get('level', 'INFO').upper()
    message = kwargs.get('message', '')

    # 获取日志级别
    log_level = getattr(logging, level, logging.INFO)

    # 记录日志
    logging.log(log_level, message)

    with allure.step(f"记录日志: [{level}] {message}"):
        allure.attach(
            f"日志级别: {level}\n日志消息: {message}",
            name="日志记录",
            attachment_type=allure.attachment_type.TEXT
        )

    return True


@keyword_manager.register('执行命令', [
    {'name': '命令', 'mapping': 'command', 'description': '要执行的系统命令'},
    {'name': '超时', 'mapping': 'timeout',
     'description': '命令执行超时时间（秒）', 'default': 60},
    {'name': '捕获输出', 'mapping': 'capture_output',
     'description': '是否捕获命令输出', 'default': True}
], category='系统/通用', tags=['命令', '执行'])
def execute_command(**kwargs):
    """执行系统命令

    Args:
        command: 要执行的系统命令
        timeout: 命令执行超时时间（秒）
        capture_output: 是否捕获命令输出

    Returns:
        dict: 包含返回码、标准输出和标准错误的字典
    """
    command = kwargs.get('command', '')
    timeout = float(kwargs.get('timeout', 60))
    capture_output = kwargs.get('capture_output', True)

    with allure.step(f"执行命令: {command}"):
        try:
            # 执行命令
            result = subprocess.run(
                command,
                shell=True,
                timeout=timeout,
                capture_output=capture_output,
                text=True
            )

            # 构建结果字典
            command_result = {
                'returncode': result.returncode,
                'stdout': result.stdout if capture_output else '',
                'stderr': result.stderr if capture_output else ''
            }

            # 记录执行结果
            allure.attach(
                f"命令: {command}\n返回码: {result.returncode}\n"
                f"标准输出: {result.stdout if capture_output else '未捕获'}\n"
                f"标准错误: {result.stderr if capture_output else '未捕获'}",
                name="命令执行结果",
                attachment_type=allure.attachment_type.TEXT
            )

            return command_result

        except subprocess.TimeoutExpired:
            # 命令执行超时
            allure.attach(
                f"命令执行超时: {command} (超时: {timeout}秒)",
                name="命令执行超时",
                attachment_type=allure.attachment_type.TEXT
            )
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': f'Command timed out after {timeout} seconds'
            }
        except Exception as e:
            # 其他异常
            allure.attach(
                f"命令执行异常: {str(e)}",
                name="命令执行异常",
                attachment_type=allure.attachment_type.TEXT
            )
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': str(e)
            }


@keyword_manager.register('求和', [
    {'name': '数据', 'mapping': 'data', 'description': '要求和的数字列表或可迭代对象'},
    {'name': '起始值', 'mapping': 'start', 'description': '求和的起始值', 'default': 0}
], category='系统/通用', tags=['数学', '求和'])
def sum_values(**kwargs):
    """计算数字列表的总和

    Args:
        data: 要求和的数字列表
        start: 求和的起始值，默认为0

    Returns:
        数字总和
    """
    data = kwargs.get('data', [])
    start = kwargs.get('start', 0)

    # 确保data是可迭代的
    if not hasattr(data, '__iter__') or isinstance(data, str):
        raise ValueError("数据必须是可迭代的数字列表")

    try:
        result = sum(data, start)

        with allure.step(f"求和计算: 数据长度={len(data)}, 起始值={start}"):
            allure.attach(
                f"输入数据: {data}\n起始值: {start}\n结果: {result}",
                name="求和结果",
                attachment_type=allure.attachment_type.TEXT
            )

        return result
    except Exception as e:
        allure.attach(
            f"求和计算失败: {str(e)}",
            name="求和错误",
            attachment_type=allure.attachment_type.TEXT
        )
        raise


@keyword_manager.register('获取长度', [
    {'name': '对象', 'mapping': 'obj', 'description': '要获取长度的对象（字符串、列表、字典等）'}
], category='系统/通用', tags=['数学', '长度'])
def get_length(**kwargs):
    """获取对象的长度

    Args:
        obj: 要获取长度的对象

    Returns:
        int: 对象的长度
    """
    obj = kwargs.get('obj')

    if obj is None:
        return 0

    try:
        result = len(obj)

        with allure.step(f"获取长度: 对象类型={type(obj).__name__}"):
            allure.attach(
                f"对象: {obj}\n类型: {type(obj).__name__}\n长度: {result}",
                name="长度计算结果",
                attachment_type=allure.attachment_type.TEXT
            )

        return result
    except Exception as e:
        allure.attach(
            f"获取长度失败: {str(e)}",
            name="长度计算错误",
            attachment_type=allure.attachment_type.TEXT
        )
        raise


@keyword_manager.register('获取最大值', [
    {'name': '数据', 'mapping': 'data', 'description': '要比较的数据列表或多个参数'},
    {'name': '默认值', 'mapping': 'default',
     'description': '当数据为空时的默认值', 'default': None}
], category='系统/通用', tags=['数学', '最大值'])
def get_max_value(**kwargs):
    """获取最大值

    Args:
        data: 要比较的数据
        default: 当数据为空时的默认值

    Returns:
        最大值
    """
    data = kwargs.get('data')
    default = kwargs.get('default')

    if data is None:
        if default is not None:
            return default
        raise ValueError("数据不能为空")

    try:
        # 如果data不是可迭代的，将其转换为列表
        if not hasattr(data, '__iter__') or isinstance(data, str):
            data = [data]

        if len(data) == 0:
            if default is not None:
                return default
            raise ValueError("数据列表为空")

        result = max(data)

        with allure.step(f"获取最大值: 数据长度={len(data)}"):
            allure.attach(
                f"输入数据: {data}\n最大值: {result}",
                name="最大值计算结果",
                attachment_type=allure.attachment_type.TEXT
            )

        return result
    except Exception as e:
        allure.attach(
            f"获取最大值失败: {str(e)}",
            name="最大值计算错误",
            attachment_type=allure.attachment_type.TEXT
        )
        raise


@keyword_manager.register('获取最小值', [
    {'name': '数据', 'mapping': 'data', 'description': '要比较的数据列表或多个参数'},
    {'name': '默认值', 'mapping': 'default',
     'description': '当数据为空时的默认值', 'default': None}
], category='系统/通用', tags=['数学', '最小值'])
def get_min_value(**kwargs):
    """获取最小值

    Args:
        data: 要比较的数据
        default: 当数据为空时的默认值

    Returns:
        最小值
    """
    data = kwargs.get('data')
    default = kwargs.get('default')

    if data is None:
        if default is not None:
            return default
        raise ValueError("数据不能为空")

    try:
        # 如果data不是可迭代的，将其转换为列表
        if not hasattr(data, '__iter__') or isinstance(data, str):
            data = [data]

        if len(data) == 0:
            if default is not None:
                return default
            raise ValueError("数据列表为空")

        result = min(data)

        with allure.step(f"获取最小值: 数据长度={len(data)}"):
            allure.attach(
                f"输入数据: {data}\n最小值: {result}",
                name="最小值计算结果",
                attachment_type=allure.attachment_type.TEXT
            )

        return result
    except Exception as e:
        allure.attach(
            f"获取最小值失败: {str(e)}",
            name="最小值计算错误",
            attachment_type=allure.attachment_type.TEXT
        )
        raise


@keyword_manager.register('绝对值', [
    {'name': '数值', 'mapping': 'number', 'description': '要计算绝对值的数字'}
], category='系统/通用', tags=['数学', '绝对值'])
def get_absolute_value(**kwargs):
    """计算数字的绝对值

    Args:
        number: 要计算绝对值的数字

    Returns:
        数字的绝对值
    """
    number = kwargs.get('number')

    if number is None:
        raise ValueError("数值不能为空")

    try:
        result = abs(number)

        with allure.step(f"计算绝对值: {number}"):
            allure.attach(
                f"输入数值: {number}\n绝对值: {result}",
                name="绝对值计算结果",
                attachment_type=allure.attachment_type.TEXT
            )

        return result
    except Exception as e:
        allure.attach(
            f"计算绝对值失败: {str(e)}",
            name="绝对值计算错误",
            attachment_type=allure.attachment_type.TEXT
        )
        raise


@keyword_manager.register('四舍五入', [
    {'name': '数值', 'mapping': 'number', 'description': '要四舍五入的数字'},
    {'name': '小数位数', 'mapping': 'ndigits',
     'description': '保留的小数位数', 'default': 0}
], category='系统/通用', tags=['数学', '四舍五入'])
def round_number(**kwargs):
    """对数字进行四舍五入

    Args:
        number: 要四舍五入的数字
        ndigits: 保留的小数位数，默认为0（整数）

    Returns:
        四舍五入后的数字
    """
    number = kwargs.get('number')
    ndigits = kwargs.get('ndigits', 0)

    if number is None:
        raise ValueError("数值不能为空")

    try:
        if ndigits == 0:
            result = round(number)
        else:
            result = round(number, int(ndigits))

        with allure.step(f"四舍五入: {number} -> {ndigits}位小数"):
            allure.attach(
                f"输入数值: {number}\n小数位数: {ndigits}\n结果: {result}",
                name="四舍五入结果",
                attachment_type=allure.attachment_type.TEXT
            )

        return result
    except Exception as e:
        allure.attach(
            f"四舍五入失败: {str(e)}",
            name="四舍五入错误",
            attachment_type=allure.attachment_type.TEXT
        )
        raise


@keyword_manager.register('转换为字符串', [
    {'name': '值', 'mapping': 'value', 'description': '要转换为字符串的值'}
], category='系统/通用', tags=['转换', '字符串'])
def convert_to_string(**kwargs):
    """将值转换为字符串

    Args:
        value: 要转换的值

    Returns:
        str: 转换后的字符串
    """
    value = kwargs.get('value')

    try:
        result = str(value)

        with allure.step(f"转换为字符串: {type(value).__name__} -> str"):
            allure.attach(
                f"原始值: {value}\n原始类型: {type(value).__name__}\n"
                f"转换结果: {result}\n结果类型: {type(result).__name__}",
                name="字符串转换结果",
                attachment_type=allure.attachment_type.TEXT
            )

        return result
    except Exception as e:
        allure.attach(
            f"转换为字符串失败: {str(e)}",
            name="字符串转换错误",
            attachment_type=allure.attachment_type.TEXT
        )
        raise


@keyword_manager.register('转换为整数', [
    {'name': '值', 'mapping': 'value', 'description': '要转换为整数的值'},
    {'name': '进制', 'mapping': 'base',
     'description': '数字进制（当值为字符串时）', 'default': 10}
], category='系统/通用', tags=['转换', '整数'])
def convert_to_integer(**kwargs):
    """将值转换为整数

    Args:
        value: 要转换的值
        base: 数字进制（当值为字符串时），默认为10

    Returns:
        int: 转换后的整数
    """
    value = kwargs.get('value')
    base = kwargs.get('base', 10)

    if value is None:
        raise ValueError("值不能为空")

    try:
        # 如果指定了非10进制，将值转换为字符串再进行进制转换
        if int(base) != 10:
            value_str = str(value)
            result = int(value_str, int(base))
        else:
            result = int(value)

        with allure.step(f"转换为整数: {type(value).__name__} -> int"):
            allure.attach(
                f"原始值: {value}\n原始类型: {type(value).__name__}\n"
                f"进制: {base}\n转换结果: {result}\n结果类型: {type(result).__name__}",
                name="整数转换结果",
                attachment_type=allure.attachment_type.TEXT
            )

        return result
    except Exception as e:
        allure.attach(
            f"转换为整数失败: {str(e)}",
            name="整数转换错误",
            attachment_type=allure.attachment_type.TEXT
        )
        raise


@keyword_manager.register('转换为浮点数', [
    {'name': '值', 'mapping': 'value', 'description': '要转换为浮点数的值'}
], category='系统/通用', tags=['转换', '浮点数'])
def convert_to_float(**kwargs):
    """将值转换为浮点数

    Args:
        value: 要转换的值

    Returns:
        float: 转换后的浮点数
    """
    value = kwargs.get('value')

    if value is None:
        raise ValueError("值不能为空")

    try:
        result = float(value)

        with allure.step(f"转换为浮点数: {type(value).__name__} -> float"):
            allure.attach(
                f"原始值: {value}\n原始类型: {type(value).__name__}\n"
                f"转换结果: {result}\n结果类型: {type(result).__name__}",
                name="浮点数转换结果",
                attachment_type=allure.attachment_type.TEXT
            )

        return result
    except Exception as e:
        allure.attach(
            f"转换为浮点数失败: {str(e)}",
            name="浮点数转换错误",
            attachment_type=allure.attachment_type.TEXT
        )
        raise


@keyword_manager.register('转换为布尔值', [
    {'name': '值', 'mapping': 'value', 'description': '要转换为布尔值的值'}
], category='系统/通用', tags=['转换', '布尔'])
def convert_to_boolean(**kwargs):
    """将值转换为布尔值

    Args:
        value: 要转换的值

    Returns:
        bool: 转换后的布尔值
    """
    value = kwargs.get('value')

    try:
        result = bool(value)

        with allure.step(f"转换为布尔值: {type(value).__name__} -> bool"):
            allure.attach(
                f"原始值: {value}\n原始类型: {type(value).__name__}\n"
                f"转换结果: {result}\n结果类型: {type(result).__name__}",
                name="布尔值转换结果",
                attachment_type=allure.attachment_type.TEXT
            )

        return result
    except Exception as e:
        allure.attach(
            f"转换为布尔值失败: {str(e)}",
            name="布尔值转换错误",
            attachment_type=allure.attachment_type.TEXT
        )
        raise
