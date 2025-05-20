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
])
def print_content(**kwargs):
    content = kwargs.get('content')
    print(f"内容: {content}")


@keyword_manager.register('返回结果', [
    {'name': '结果', 'mapping': 'result', 'description': '要返回的结果值'}
])
def return_result(**kwargs):
    return kwargs.get('result')


@keyword_manager.register('等待', [
    {'name': '秒数', 'mapping': 'seconds', 'description': '等待的秒数，可以是小数'}
])
def wait_seconds(**kwargs):
    """等待指定的秒数

    Args:
        seconds: 等待的秒数，可以是小数表示毫秒级等待
    """
    seconds = float(kwargs.get('seconds', 0))
    with allure.step(f"等待 {seconds} 秒"):
        time.sleep(seconds)
    return True


@keyword_manager.register('获取当前时间', [
    {'name': '格式', 'mapping': 'format', 'description': '时间格式，例如 "%Y-%m-%d %H:%M:%S"，默认返回时间戳'},
    {'name': '时区', 'mapping': 'timezone', 'description': '时区，例如 "Asia/Shanghai"，默认为本地时区'}
])
def get_current_time(**kwargs):
    """获取当前时间

    Args:
        format: 时间格式，如果不提供则返回时间戳
        timezone: 时区，默认为本地时区

    Returns:
        str: 格式化的时间字符串或时间戳
    """
    time_format = kwargs.get('format')
    timezone = kwargs.get('timezone')

    # 获取当前时间
    if timezone:
        import pytz
        try:
            tz = pytz.timezone(timezone)
            current_time = datetime.datetime.now(tz)
        except Exception as e:
            allure.attach(
                f"时区设置异常: {str(e)}",
                name="时区设置异常",
                attachment_type=allure.attachment_type.TEXT
            )
            current_time = datetime.datetime.now()
    else:
        current_time = datetime.datetime.now()

    # 格式化时间
    if time_format:
        try:
            result = current_time.strftime(time_format)
        except Exception as e:
            allure.attach(
                f"时间格式化异常: {str(e)}",
                name="时间格式化异常",
                attachment_type=allure.attachment_type.TEXT
            )
            result = str(current_time)
    else:
        # 返回时间戳
        result = str(int(current_time.timestamp()))

    return result


@keyword_manager.register('生成随机字符串', [
    {'name': '长度', 'mapping': 'length', 'description': '随机字符串的长度，默认为8'},
    {'name': '类型', 'mapping': 'type',
        'description': '字符类型：字母(letters)、数字(digits)、字母数字(alphanumeric)、全部(all)，默认为字母数字'}
])
def generate_random_string(**kwargs):
    """生成随机字符串

    Args:
        length: 随机字符串的长度
        type: 字符类型：字母、数字、字母数字、全部

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
    {'name': '最小值', 'mapping': 'min', 'description': '随机数的最小值，默认为0'},
    {'name': '最大值', 'mapping': 'max', 'description': '随机数的最大值，默认为100'},
    {'name': '小数位数', 'mapping': 'decimals', 'description': '小数位数，默认为0（整数）'}
])
def generate_random_number(**kwargs):
    """生成随机数

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
        'description': '操作类型：拼接(concat)、替换(replace)、分割(split)、大写(upper)、小写(lower)、去空格(strip)'},
    {'name': '字符串', 'mapping': 'string', 'description': '要操作的字符串'},
    {'name': '参数1', 'mapping': 'param1', 'description': '操作参数1，根据操作类型不同而不同'},
    {'name': '参数2', 'mapping': 'param2', 'description': '操作参数2，根据操作类型不同而不同'}
])
def string_operation(**kwargs):
    """字符串操作

    Args:
        operation: 操作类型
        string: 要操作的字符串
        param1: 操作参数1
        param2: 操作参数2

    Returns:
        str: 操作结果
    """
    operation = kwargs.get('operation', '').lower()
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
        result = string.split(str(param1))
        if param2 and param2.isdigit():
            # 如果提供了索引，返回指定位置的元素
            index = int(param2)
            if 0 <= index < len(result):
                result = result[index]
    elif operation == 'upper':
        # 转大写
        result = string.upper()
    elif operation == 'lower':
        # 转小写
        result = string.lower()
    elif operation == 'strip':
        # 去空格
        result = string.strip()
    else:
        # 未知操作，返回原字符串
        allure.attach(
            f"未知的字符串操作: {operation}",
            name="字符串操作错误",
            attachment_type=allure.attachment_type.TEXT
        )

    with allure.step(f"字符串操作: {operation}"):
        allure.attach(
            f"原字符串: {string}\n操作: {operation}\n参数1: {param1}\n参数2: {param2}\n结果: {result}",
            name="字符串操作结果",
            attachment_type=allure.attachment_type.TEXT
        )

    return result


@keyword_manager.register('日志', [
    {'name': '级别', 'mapping': 'level',
        'description': '日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL，默认为INFO'},
    {'name': '消息', 'mapping': 'message', 'description': '日志消息内容'}
])
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
    {'name': '超时', 'mapping': 'timeout', 'description': '命令执行超时时间（秒），默认为60秒'},
    {'name': '捕获输出', 'mapping': 'capture_output', 'description': '是否捕获命令输出，默认为True'}
])
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
