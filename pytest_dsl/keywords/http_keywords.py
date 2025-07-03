"""HTTP请求关键字模块

该模块提供了用于发送HTTP请求、捕获响应和断言的关键字。
"""

import allure
import re
import yaml
import json
import os
import time
import logging
from typing import Dict, Any, Union

from pytest_dsl.core.keyword_manager import keyword_manager
from pytest_dsl.core.http_request import HTTPRequest
from pytest_dsl.core.context import TestContext

# 配置日志
logger = logging.getLogger(__name__)


def _process_file_reference(reference: Union[str, Dict[str, Any]],
                            allow_vars: bool = True,
                            test_context: TestContext = None) -> Any:
    """处理文件引用，加载外部文件内容

    支持两种语法:
    1. 简单语法: "@file:/path/to/file.json" 或 "@file_template:/path/to/file.json"
    2. 详细语法: 使用file_ref结构提供更多的配置选项

    Args:
        reference: 文件引用字符串或配置字典
        allow_vars: 是否允许在文件内容中替换变量

    Returns:
        加载并处理后的文件内容
    """
    # 处理简单语法
    if isinstance(reference, str):
        # 匹配简单文件引用语法
        file_ref_pattern = r'^@file(?:_template)?:(.+)$'
        match = re.match(file_ref_pattern, reference.strip())

        if match:
            file_path = match.group(1).strip()
            is_template = '_template' in reference[:15]  # 检查是否为模板
            return _load_file_content(file_path, is_template, 'auto', 'utf-8',
                                      test_context)

    # 处理详细语法
    elif isinstance(reference, dict) and 'file_ref' in reference:
        file_ref = reference['file_ref']

        if isinstance(file_ref, str):
            # 如果file_ref是字符串，使用默认配置
            return _load_file_content(file_ref, allow_vars, 'auto', 'utf-8',
                                      test_context)
        elif isinstance(file_ref, dict):
            # 如果file_ref是字典，使用自定义配置
            file_path = file_ref.get('path')
            if not file_path:
                raise ValueError("file_ref必须包含path字段")

            template = file_ref.get('template', allow_vars)
            file_type = file_ref.get('type', 'auto')
            encoding = file_ref.get('encoding', 'utf-8')

            return _load_file_content(file_path, template, file_type, encoding,
                                      test_context)

    # 如果不是文件引用，返回原始值
    return reference


def _load_file_content(file_path: str, is_template: bool = False,
                       file_type: str = 'auto', encoding: str = 'utf-8',
                       test_context: TestContext = None) -> Any:
    """加载文件内容

    Args:
        file_path: 文件路径
        is_template: 是否作为模板处理（替换变量引用）
        file_type: 文件类型 (auto, json, yaml, text)
        encoding: 文件编码

    Returns:
        加载并处理后的文件内容
    """
    # 验证文件存在
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"找不到引用的文件: {file_path}")

    # 读取文件内容
    with open(file_path, 'r', encoding=encoding) as f:
        content = f.read()

    # 如果是模板，处理变量替换
    if is_template:
        from pytest_dsl.core.variable_utils import VariableReplacer
        replacer = VariableReplacer(test_context=test_context)
        content = replacer.replace_in_string(content)

    # 根据文件类型处理内容
    if file_type == 'auto':
        # 根据文件扩展名自动检测类型
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext in ['.json']:
            file_type = 'json'
        elif file_ext in ['.yaml', '.yml']:
            file_type = 'yaml'
        else:
            file_type = 'text'

    # 处理不同类型的文件
    if file_type == 'json':
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"无效的JSON文件 {file_path}: {str(e)}")
    elif file_type == 'yaml':
        try:
            return yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ValueError(f"无效的YAML文件 {file_path}: {str(e)}")
    else:
        # 文本文件直接返回内容
        return content


def _process_request_config(config: Dict[str, Any],
                            test_context: TestContext = None) -> \
        Dict[str, Any]:
    """处理请求配置，检查并处理文件引用

    Args:
        config: 请求配置

    Returns:
        处理后的请求配置
    """
    if not isinstance(config, dict):
        return config

    # 处理request部分
    if 'request' in config and isinstance(config['request'], dict):
        request = config['request']

        # 处理json字段
        if 'json' in request:
            request['json'] = _process_file_reference(
                request['json'], test_context=test_context)

        # 处理data字段
        if 'data' in request:
            request['data'] = _process_file_reference(
                request['data'], test_context=test_context)

        # 处理headers字段
        if 'headers' in request:
            request['headers'] = _process_file_reference(
                request['headers'], test_context=test_context)

    return config


def _normalize_retry_config(config, assert_retry_count=None,
                            assert_retry_interval=None):
    """标准化断言重试配置

    将不同来源的重试配置（命令行参数、retry配置、retry_assertions配置）
    统一转换为标准化的重试配置对象。

    Args:
        config: 原始配置字典
        assert_retry_count: 命令行级别的重试次数参数
        assert_retry_interval: 命令行级别的重试间隔参数

    Returns:
        标准化的重试配置字典，格式为:
        {
            'enabled': 是否启用重试,
            'count': 重试次数,
            'interval': 重试间隔,
            'all': 是否重试所有断言,
            'indices': 要重试的断言索引列表,
            'specific': 特定断言的重试配置
        }
    """
    # 初始化标准重试配置
    standard_retry_config = {
        'enabled': False,
        'count': 3,          # 默认重试3次
        'interval': 1.0,     # 默认间隔1秒
        'all': False,        # 默认不重试所有断言
        'indices': [],       # 默认不指定要重试的断言索引
        'specific': {}       # 默认不指定特定断言的重试配置
    }

    # 处理命令行参数
    if assert_retry_count and int(assert_retry_count) > 0:
        standard_retry_config['enabled'] = True
        standard_retry_config['count'] = int(assert_retry_count)
        standard_retry_config['all'] = True  # 命令行参数会重试所有断言
        if assert_retry_interval:
            standard_retry_config['interval'] = float(assert_retry_interval)

    # 处理专用retry_assertions配置
    if 'retry_assertions' in config and config['retry_assertions']:
        retry_assertions = config['retry_assertions']
        standard_retry_config['enabled'] = True

        if 'count' in retry_assertions:
            standard_retry_config['count'] = retry_assertions['count']
        if 'interval' in retry_assertions:
            standard_retry_config['interval'] = retry_assertions['interval']
        if 'all' in retry_assertions:
            standard_retry_config['all'] = retry_assertions['all']
        if 'indices' in retry_assertions:
            standard_retry_config['indices'] = retry_assertions['indices']
        if 'specific' in retry_assertions:
            # 确保specific配置中的整数键被转换为字符串键，保持兼容性
            specific_config = {}
            for key, value in retry_assertions['specific'].items():
                # 同时支持整数键和字符串键
                specific_config[str(key)] = value
                # 保留原始键类型以便查找
                if isinstance(key, int):
                    specific_config[key] = value
            standard_retry_config['specific'] = specific_config

    # 处理传统retry配置（如果专用配置不存在）
    elif 'retry' in config and config['retry']:
        retry_config = config['retry']
        if 'count' in retry_config and retry_config['count'] > 0:
            standard_retry_config['enabled'] = True
            standard_retry_config['count'] = retry_config['count']
            standard_retry_config['all'] = True  # 传统配置会重试所有断言
            if 'interval' in retry_config:
                standard_retry_config['interval'] = retry_config['interval']

    return standard_retry_config


@keyword_manager.register('HTTP请求', [
    {'name': '客户端', 'mapping': 'client',
     'description': '客户端名称，对应YAML变量文件中的客户端配置',
     'default': 'default'},
    {'name': '配置', 'mapping': 'config',
     'description': '包含请求、捕获和断言的YAML配置'},
    {'name': '会话', 'mapping': 'session',
     'description': '会话名称，用于在多个请求间保持会话状态'},
    {'name': '保存响应', 'mapping': 'save_response',
     'description': '将完整响应保存到指定变量名中'},
    {'name': '禁用授权', 'mapping': 'disable_auth',
     'description': '禁用客户端配置中的授权机制', 'default': False},
    {'name': '模板', 'mapping': 'template',
     'description': '使用YAML变量文件中定义的请求模板'},
    {'name': '断言重试次数', 'mapping': 'assert_retry_count',
     'description': '断言失败时的重试次数', 'default': 0},
    {'name': '断言重试间隔', 'mapping': 'assert_retry_interval',
     'description': '断言重试间隔时间（秒）', 'default': 1}
], category='系统/接口测试', tags=['接口', '请求'])
def http_request(context, **kwargs):
    """执行HTTP请求

    根据YAML配置发送HTTP请求，支持客户端配置、会话管理、响应捕获和断言。

    Args:
        context: 测试上下文
        client: 客户端名称
        config: YAML配置
        session: 会话名称
        save_response: 保存响应的变量名
        disable_auth: 禁用客户端配置中的授权机制
        template: 模板名称
        assert_retry_count: 断言失败时的重试次数
        assert_retry_interval: 断言重试间隔时间（秒）

    Returns:
        捕获的变量字典或响应对象
    """
    client_name = kwargs.get('client', 'default')
    config = kwargs.get('config', '{}')
    session_name = kwargs.get('session')
    save_response = kwargs.get('save_response')
    disable_auth = kwargs.get('disable_auth', False)
    template_name = kwargs.get('template')
    assert_retry_count = kwargs.get('assert_retry_count')
    assert_retry_interval = kwargs.get('assert_retry_interval')

    # 添加调试信息，检查客户端配置是否可用
    print(f"🌐 HTTP请求 - 客户端: {client_name}")

    # 从context获取http_clients配置（统一的变量获取方式）
    http_clients_config = context.get("http_clients")
    if http_clients_config:
        print(f"✓ 找到http_clients配置，包含 {len(http_clients_config)} 个客户端")
        if client_name in http_clients_config:
            print(f"✓ 找到客户端 '{client_name}' 的配置")
            client_config = http_clients_config[client_name]
            print(f"  - base_url: {client_config.get('base_url', 'N/A')}")
            print(f"  - timeout: {client_config.get('timeout', 'N/A')}")
        else:
            print(f"⚠️ 未找到客户端 '{client_name}' 的配置")
            print(f"  可用客户端: {list(http_clients_config.keys())}")
    else:
        print("⚠️ 未找到http_clients配置")

    with allure.step(f"发送HTTP请求 (客户端: {client_name}"
                     f"{', 会话: ' + session_name if session_name else ''})"):

        # 确保http_client_manager有正确的context引用
        from pytest_dsl.core.http_client import http_client_manager
        http_client_manager.set_context(context)

        # 处理模板
        if template_name:
            # 从context获取模板配置（统一的变量获取方式）
            http_templates = context.get("http_templates") or {}
            template = http_templates.get(template_name)

            if not template:
                raise ValueError(f"未找到名为 '{template_name}' 的HTTP请求模板")

            # 解析配置并合并模板
            if isinstance(config, str):
                # 先进行变量替换，再解析YAML
                from pytest_dsl.core.variable_utils import VariableReplacer
                replacer = VariableReplacer(test_context=context)
                config = replacer.replace_in_string(config)
                try:
                    user_config = yaml.safe_load(config) if config else {}

                    # 深度合并
                    merged_config = _deep_merge(template.copy(), user_config)
                    config = merged_config
                except yaml.YAMLError as e:
                    raise ValueError(f"无效的YAML配置: {str(e)}")
        else:
            # 如果没有使用模板，直接对配置字符串进行变量替换
            if isinstance(config, str):
                from pytest_dsl.core.variable_utils import VariableReplacer
                replacer = VariableReplacer(test_context=context)
                config = replacer.replace_in_string(config)

        # 解析YAML配置
        if isinstance(config, str):
            try:
                config = yaml.safe_load(config)
            except yaml.YAMLError as e:
                raise ValueError(f"无效的YAML配置: {str(e)}")

        # 统一处理重试配置
        retry_config = _normalize_retry_config(config, assert_retry_count,
                                               assert_retry_interval)

        # 为了兼容性，将标准化后的重试配置写回到配置中
        if retry_config['enabled']:
            config['retry_assertions'] = {
                'count': retry_config['count'],
                'interval': retry_config['interval'],
                'all': retry_config['all'],
                'indices': retry_config['indices'],
                'specific': retry_config['specific']
            }

        config = _process_request_config(config, test_context=context)

        # 创建HTTP请求对象
        http_req = HTTPRequest(config, client_name, session_name)

        # 执行请求
        response = http_req.execute(disable_auth=disable_auth)

        # 统一处理断言逻辑
        with allure.step("执行断言验证"):
            if retry_config['enabled']:
                # 使用统一的重试处理函数
                _process_assertions_with_unified_retry(http_req, retry_config,
                                                       disable_auth)
            else:
                # 不需要重试，直接断言
                http_req.process_asserts()

        # 在断言完成后获取最终的捕获值（可能在重试期间被更新）
        captured_values = http_req.captured_values

        # 将捕获的变量注册到上下文
        for var_name, value in captured_values.items():
            context.set(var_name, value)

        # 保存完整响应（如果需要）
        if save_response:
            context.set(save_response, response)

        # 获取会话状态（如果使用了会话）
        session_state = None
        if session_name:
            try:
                from pytest_dsl.core.http_client import http_client_manager
                session_client = http_client_manager.get_session(
                    session_name, client_name)
                if session_client and session_client._session:
                    session_state = {
                        "cookies": dict(session_client._session.cookies),
                        "headers": dict(session_client._session.headers)
                    }
            except Exception as e:
                # 会话状态获取失败不影响主要功能
                logger.warning(f"获取会话状态失败: {str(e)}")

        # 准备响应数据（如果需要保存响应）
        response_data = None
        if save_response:
            # 确保响应数据是可序列化的
            try:
                import json
                json.dumps(response.__dict__)
                response_data = response.__dict__
            except (TypeError, AttributeError):
                # 如果无法序列化，转换为基本信息
                response_data = {
                    "status_code": getattr(response, 'status_code', None),
                    "headers": dict(getattr(response, 'headers', {})),
                    "text": getattr(response, 'text', ''),
                    "url": getattr(response, 'url', '')
                }

        # 统一返回格式 - 支持远程关键字模式
        return {
            "result": captured_values,  # 主要返回值保持兼容
            "captures": captured_values,  # 明确的捕获变量
            "session_state": ({session_name: session_state}
                              if session_state else {}),
            "response": response_data,  # 完整响应（如果需要）
            "metadata": {
                "response_time": getattr(response, 'elapsed', None),
                "status_code": getattr(response, 'status_code', None),
                "url": getattr(response, 'url', '')
            }
        }


def _deep_merge(dict1, dict2):
    """深度合并两个字典

    Args:
        dict1: 基础字典（会被修改）
        dict2: 要合并的字典（优先级更高）

    Returns:
        合并后的字典
    """
    for key in dict2:
        if (key in dict1 and isinstance(dict1[key], dict) and
                isinstance(dict2[key], dict)):
            _deep_merge(dict1[key], dict2[key])
        else:
            dict1[key] = dict2[key]
    return dict1


def _process_assertions_with_unified_retry(http_req, retry_config,
                                           disable_auth=False):
    """使用统一的重试配置处理断言

    Args:
        http_req: HTTP请求对象
        retry_config: 标准化的重试配置
    """
    # 初始尝试执行所有断言
    try:
        results, failed_retryable_assertions = http_req.process_asserts()
        # 如果没有失败的断言，直接返回
        return results
    except AssertionError as e:
        # 记录初始断言失败的详细错误信息
        allure.attach(
            str(e),
            name="断言验证失败详情",
            attachment_type=allure.attachment_type.TEXT
        )

        # 添加一个特殊的标记到配置中，表示我们只想收集失败的断言而不抛出异常
        original_config = (http_req.config.copy()
                           if isinstance(http_req.config, dict) else {})

        # 创建一个临时副本
        temp_config = original_config.copy()

        # 添加特殊标记，用于指示http_request.py中的process_asserts在处理fail时不抛出异常
        # 注意：这需要对应修改HTTPRequest.process_asserts方法
        temp_config['_collect_failed_assertions_only'] = True

        try:
            # 临时替换配置
            http_req.config = temp_config

            # 确保在收集失败断言之前，response和captures是可用的
            if not http_req.response:
                # 如果response为空，重新执行一次请求
                http_req.execute(disable_auth=disable_auth)

            # 重新运行断言，这次只收集失败的断言而不抛出异常
            _, failed_retryable_assertions = http_req.process_asserts()
        except Exception as collect_err:
            # 出现意外错误时记录
            allure.attach(
                f"收集失败断言时出错: {type(collect_err).__name__}: "
                f"{str(collect_err)}",
                name="断言收集错误",
                attachment_type=allure.attachment_type.TEXT
            )
            failed_retryable_assertions = []
        finally:
            # 恢复原始配置
            http_req.config = original_config

        # 有断言失败，判断是否有需要重试的断言
        if not failed_retryable_assertions:
            # 没有可重试的断言，重新抛出原始异常
            raise

        # 过滤需要重试的断言
        retryable_assertions = []

        for failed_assertion in failed_retryable_assertions:
            assertion_idx = failed_assertion['index']

            # 判断该断言是否应该重试
            should_retry = False
            specific_retry_count = retry_config['count']
            specific_retry_interval = retry_config['interval']

            # 检查特定断言配置
            if str(assertion_idx) in retry_config['specific']:
                should_retry = True
                spec_config = retry_config['specific'][str(assertion_idx)]
                if isinstance(spec_config, dict):
                    if 'count' in spec_config:
                        specific_retry_count = spec_config['count']
                    if 'interval' in spec_config:
                        specific_retry_interval = spec_config['interval']
            # 检查索引列表
            elif assertion_idx in retry_config['indices']:
                should_retry = True
            # 检查是否重试所有
            elif retry_config['all']:
                should_retry = True

            # 如果应该重试，添加到可重试断言列表
            if should_retry:
                # 添加重试配置到断言对象
                failed_assertion['retry_count'] = specific_retry_count
                failed_assertion['retry_interval'] = specific_retry_interval
                retryable_assertions.append(failed_assertion)

        # 如果没有可重试的断言，重新抛出异常
        if not retryable_assertions:
            raise

        # 记录哪些断言会被重试
        retry_info = "\n".join([
            f"{i+1}. {a['type']} " +
            (f"[{a['path']}]" if a['path'] else "") +
            f": 重试 {a['retry_count']} 次，间隔 {a['retry_interval']} 秒"
            for i, a in enumerate(retryable_assertions)
        ])

        allure.attach(
            f"找到 {len(retryable_assertions)} 个可重试的断言:\n\n{retry_info}",
            name="重试断言列表",
            attachment_type=allure.attachment_type.TEXT
        )

        # 开始重试循环
        max_retry_count = retry_config['count']

        # 找出所有断言中最大的重试次数
        for retryable_assertion in retryable_assertions:
            max_retry_count = max(max_retry_count,
                                  retryable_assertion.get('retry_count', 3))

        # 进行断言重试
        for attempt in range(1, max_retry_count + 1):
            # 等待重试间隔
            with allure.step(f"断言重试 (尝试 {attempt}/{max_retry_count})"):
                # 确定本次重试的间隔时间（使用每个断言中最长的间隔时间）
                retry_interval = retry_config['interval']
                for assertion in retryable_assertions:
                    retry_interval = max(retry_interval,
                                         assertion.get('retry_interval', 1.0))

                allure.attach(
                    f"重试 {len(retryable_assertions)} 个断言\n"
                    f"等待间隔: {retry_interval}秒",
                    name="断言重试信息",
                    attachment_type=allure.attachment_type.TEXT
                )

                time.sleep(retry_interval)

                # 重新发送请求
                try:
                    http_req.execute(disable_auth=disable_auth)
                except Exception as exec_error:
                    # 如果重新执行请求失败，记录错误并继续重试
                    allure.attach(
                        f"重试执行请求失败: {type(exec_error).__name__}: "
                        f"{str(exec_error)}",
                        name=f"重试请求执行失败 #{attempt}",
                        attachment_type=allure.attachment_type.TEXT
                    )
                    continue

                # 过滤出仍在重试范围内的断言
                still_retryable_assertions = []
                for assertion in retryable_assertions:
                    assertion_retry_count = assertion.get('retry_count', 3)

                    # 如果断言的重试次数大于当前尝试次数，继续重试该断言
                    if attempt < assertion_retry_count:
                        still_retryable_assertions.append(assertion)

                # 如果没有可以继续重试的断言，跳出循环
                if not still_retryable_assertions:
                    break

                # 只重试那些仍在重试范围内的断言
                try:
                    # 从原始断言配置中提取出需要重试的断言
                    retry_assertion_indexes = [
                        a['index'] for a in still_retryable_assertions]
                    retry_assertions = [
                        http_req.config.get('asserts', [])[idx]
                        for idx in retry_assertion_indexes]

                    # 创建索引映射：新索引 -> 原始索引
                    index_mapping = {
                        new_idx: orig_idx for new_idx, orig_idx in
                        enumerate(retry_assertion_indexes)}

                    # 只处理需要重试的断言，传递索引映射
                    results, new_failed_assertions = http_req.process_asserts(
                        specific_asserts=retry_assertions,
                        index_mapping=index_mapping)

                    # 如果所有断言都通过了，检查全部断言
                    if not new_failed_assertions:
                        # 执行一次完整的断言检查，确保所有断言都通过
                        try:
                            results, _ = http_req.process_asserts()
                            allure.attach(
                                "所有断言重试后验证通过",
                                name="重试成功",
                                attachment_type=allure.attachment_type.TEXT
                            )
                            return results
                        except AssertionError as final_err:
                            # 记录最终错误，然后继续重试
                            allure.attach(
                                f"重试后的完整断言验证仍有失败: {str(final_err)}",
                                name="完整断言仍失败",
                                attachment_type=allure.attachment_type.TEXT
                            )
                            continue

                    # 更新失败的可重试断言列表
                    retryable_assertions = new_failed_assertions

                except AssertionError as retry_err:
                    # 重试时断言失败，记录后继续重试
                    allure.attach(
                        f"第 {attempt} 次重试断言失败: {str(retry_err)}",
                        name=f"重试断言失败 #{attempt}",
                        attachment_type=allure.attachment_type.TEXT
                    )
                    continue

        # 重试次数用完，执行一次完整的断言以获取最终结果和错误
        # 这会抛出异常，如果仍然有断言失败
        allure.attach(
            "所有重试次数已用完，执行最终断言验证",
            name="重试完成",
            attachment_type=allure.attachment_type.TEXT
        )

        try:
            # 确保在最终断言之前重新执行一次请求
            http_req.execute(disable_auth=disable_auth)
            results, _ = http_req.process_asserts()
            return results
        except AssertionError as final_err:
            # 重新格式化错误消息，添加重试信息
            enhanced_error = (
                f"断言验证失败 (已重试 {max_retry_count} 次):\n\n"
                f"{str(final_err)}"
            )
            allure.attach(
                enhanced_error,
                name="重试后仍失败的断言",
                attachment_type=allure.attachment_type.TEXT
            )
            raise AssertionError(enhanced_error) from final_err


# 注意：旧的重试函数已被移除，现在使用统一的重试机制
