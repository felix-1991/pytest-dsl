"""HTTP请求关键字模块

该模块提供了用于发送HTTP请求、捕获响应和断言的关键字。
"""

import allure
import re
import yaml
from typing import Dict, Any, List, Optional

from pytest_dsl.core.keyword_manager import keyword_manager
from pytest_dsl.core.http_request import HTTPRequest
from pytest_dsl.core.http_client import http_client_manager
from pytest_dsl.core.global_context import global_context


@keyword_manager.register('HTTP请求', [
    {'name': '客户端', 'mapping': 'client', 'description': '客户端名称，对应YAML变量文件中的客户端配置'},
    {'name': '配置', 'mapping': 'config', 'description': '包含请求、捕获和断言的YAML配置'},
    {'name': '会话', 'mapping': 'session', 'description': '会话名称，用于在多个请求间保持会话状态'},
    {'name': '保存响应', 'mapping': 'save_response', 'description': '将完整响应保存到指定变量名中'},
    {'name': '重试次数', 'mapping': 'retry_count', 'description': '请求失败时的重试次数'},
    {'name': '重试间隔', 'mapping': 'retry_interval', 'description': '重试间隔时间（秒）'},
    {'name': '模板', 'mapping': 'template', 'description': '使用YAML变量文件中定义的请求模板'},
    {'name': '断言重试次数', 'mapping': 'assert_retry_count', 'description': '断言失败时的重试次数'},
    {'name': '断言重试间隔', 'mapping': 'assert_retry_interval', 'description': '断言重试间隔时间（秒）'}
])
def http_request(context, **kwargs):
    """执行HTTP请求
    
    根据YAML配置发送HTTP请求，支持客户端配置、会话管理、响应捕获和断言。
    
    Args:
        context: 测试上下文
        client: 客户端名称
        config: YAML配置
        session: 会话名称
        save_response: 保存响应的变量名
        retry_count: 重试次数
        retry_interval: 重试间隔
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
    retry_count = kwargs.get('retry_count')
    retry_interval = kwargs.get('retry_interval')
    template_name = kwargs.get('template')
    assert_retry_count = kwargs.get('assert_retry_count')
    assert_retry_interval = kwargs.get('assert_retry_interval')
    
    with allure.step(f"发送HTTP请求 (客户端: {client_name}{', 会话: ' + session_name if session_name else ''})"):
        # 处理模板
        if template_name:
            # 从YAML变量中获取模板
            from pytest_dsl.core.yaml_vars import yaml_vars
            http_templates = yaml_vars.get_variable("http_templates") or {}
            template = http_templates.get(template_name)
            
            if not template:
                raise ValueError(f"未找到名为 '{template_name}' 的HTTP请求模板")
            
            # 解析配置并合并模板
            # 先进行变量替换，再解析YAML
            config = _replace_variables_in_string(config)
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
                config = _replace_variables_in_string(config)
        
        # 创建HTTP请求对象
        http_req = HTTPRequest(config, client_name, session_name)
        
        # 执行请求
        response = http_req.execute()
        
        # 处理捕获
        captured_values = http_req.captured_values
        
        # 将捕获的变量注册到上下文
        for var_name, value in captured_values.items():
            context.set(var_name, value)
        
        # 保存完整响应（如果需要）
        if save_response:
            context.set(save_response, response)
        
        # 处理断言（支持重试）
        if assert_retry_count and int(assert_retry_count) > 0:
            _process_assertions_with_retry(http_req, int(assert_retry_count), 
                                        float(assert_retry_interval) if assert_retry_interval else 1.0)
        else:
            # 不需要重试，直接断言
            http_req.process_asserts()
        
        # 返回捕获的变量
        return captured_values


def _replace_variables_in_string(value):
    """替换字符串中的变量引用，包括嵌套的点号引用
    
    Args:
        value: 包含变量引用的字符串
        
    Returns:
        替换后的字符串
    """
    if not isinstance(value, str):
        return value
        
    # 基本变量引用模式: ${variable}
    basic_pattern = r'\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
    
    # 嵌套引用模式: ${variable.field.subfield}
    nested_pattern = r'\$\{([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)+)\}'
    
    # 先处理嵌套引用
    matches = list(re.finditer(nested_pattern, value))
    for match in reversed(matches):
        var_ref = match.group(1)  # 例如: "api_test_data.user_id"
        parts = var_ref.split('.')
        
        # 获取根变量
        root_var_name = parts[0]
        if context_has_variable(root_var_name):
            root_var = get_variable(root_var_name)
            
            # 递归访问嵌套属性
            var_value = root_var
            for part in parts[1:]:
                if isinstance(var_value, dict) and part in var_value:
                    var_value = var_value[part]
                else:
                    # 无法解析的属性路径
                    var_value = f"${{{var_ref}}}"  # 保持原样
                    break
            
            # 替换变量引用
            value = value[:match.start()] + str(var_value) + value[match.end():]
    
    # 再处理基本引用
    matches = list(re.finditer(basic_pattern, value))
    for match in reversed(matches):
        var_name = match.group(1)
        if context_has_variable(var_name):
            var_value = get_variable(var_name)
            value = value[:match.start()] + str(var_value) + value[match.end():]
    
    return value


def context_has_variable(var_name):
    """检查变量是否存在于全局上下文"""
    # 先检查YAML变量
    from pytest_dsl.core.yaml_vars import yaml_vars
    if yaml_vars.get_variable(var_name) is not None:
        return True
    
    # 检查测试上下文
    from pytest_dsl.core.keyword_manager import keyword_manager
    current_context = getattr(keyword_manager, 'current_context', None)
    if current_context and current_context.has(var_name):
        return True
    
    # 再检查全局上下文
    return global_context.has_variable(var_name)


def get_variable(var_name):
    """获取变量值，先从YAML变量中获取，再从全局上下文获取"""
    # 先从YAML变量中获取
    from pytest_dsl.core.yaml_vars import yaml_vars
    yaml_value = yaml_vars.get_variable(var_name)
    if yaml_value is not None:
        return yaml_value
    
    # 检查测试上下文
    from pytest_dsl.core.keyword_manager import keyword_manager
    current_context = getattr(keyword_manager, 'current_context', None)
    if current_context and current_context.has(var_name):
        return current_context.get(var_name)
    
    # 再从全局上下文获取
    if global_context.has_variable(var_name):
        return global_context.get_variable(var_name)
    
    # 如果都没有找到，返回变量引用本身
    return f"${{{var_name}}}"


def _deep_merge(base: Dict, override: Dict) -> Dict:
    """深度合并两个字典
    
    Args:
        base: 基础字典
        override: 覆盖字典
        
    Returns:
        合并后的字典
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # 递归合并嵌套字典
            result[key] = _deep_merge(result[key], value)
        elif key in result and isinstance(result[key], list) and isinstance(value, list):
            # 合并列表
            result[key] = result[key] + value
        else:
            # 覆盖或添加值
            result[key] = value
            
    return result 


def _process_assertions_with_retry(http_req, max_retries, retry_interval):
    """处理断言并支持重试
    
    Args:
        http_req: HTTP请求对象
        max_retries: 最大重试次数
        retry_interval: 重试间隔（秒）
    
    Raises:
        AssertionError: 当断言失败且重试次数用尽时
    """
    import time
    import logging
    
    logger = logging.getLogger(__name__)
    
    last_error = None
    for retry in range(max_retries + 1):  # +1表示包括首次尝试
        try:
            # 如果是重试，需要重新发送请求
            if retry > 0:
                logger.info(f"第 {retry} 次重试...")
                http_req.execute()  # 重新发送请求
            # 尝试执行断言
            http_req.process_asserts()
            return  # 如果断言成功，直接返回
        except AssertionError as e:
            last_error = e
            if retry < max_retries:
                logger.warning(f"断言失败，等待 {retry_interval} 秒后重试: {str(e)}")
                time.sleep(retry_interval)
            else:
                logger.error(f"断言失败，已达到最大重试次数 {max_retries}: {str(e)}")
                raise last_error
        except Exception as e:
            logger.error(f"处理断言时发生错误: {str(e)}")
            raise e 