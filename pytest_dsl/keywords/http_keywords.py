"""HTTP请求关键字模块

该模块提供了用于发送HTTP请求、捕获响应和断言的关键字。
"""

import allure
import re
import yaml
import json
import os
import time
from typing import Dict, Any, Union

from pytest_dsl.core.keyword_manager import keyword_manager
from pytest_dsl.core.http_request import HTTPRequest
from pytest_dsl.core.yaml_vars import yaml_vars
from pytest_dsl.core.context import TestContext

def _process_file_reference(reference: Union[str, Dict[str, Any]], allow_vars: bool = True, test_context: TestContext = None) -> Any:
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
            return _load_file_content(file_path, is_template, 'auto', 'utf-8', test_context)
    
    # 处理详细语法
    elif isinstance(reference, dict) and 'file_ref' in reference:
        file_ref = reference['file_ref']
        
        if isinstance(file_ref, str):
            # 如果file_ref是字符串，使用默认配置
            return _load_file_content(file_ref, allow_vars, 'auto', 'utf-8', test_context)
        elif isinstance(file_ref, dict):
            # 如果file_ref是字典，使用自定义配置
            file_path = file_ref.get('path')
            if not file_path:
                raise ValueError("file_ref必须包含path字段")
                
            template = file_ref.get('template', allow_vars)
            file_type = file_ref.get('type', 'auto')
            encoding = file_ref.get('encoding', 'utf-8')
            
            return _load_file_content(file_path, template, file_type, encoding, test_context)
    
    # 如果不是文件引用，返回原始值
    return reference


def _load_file_content(file_path: str, is_template: bool = False, 
                       file_type: str = 'auto', encoding: str = 'utf-8', test_context: TestContext = None) -> Any:
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


def _process_request_config(config: Dict[str, Any], test_context: TestContext = None) -> Dict[str, Any]:
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
            request['json'] = _process_file_reference(request['json'], test_context=test_context)
            
        # 处理data字段
        if 'data' in request:
            request['data'] = _process_file_reference(request['data'], test_context=test_context)
            
        # 处理headers字段
        if 'headers' in request:
            request['headers'] = _process_file_reference(request['headers'], test_context=test_context)
    
    return config


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
            http_templates = yaml_vars.get_variable("http_templates") or {}
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
        
        config = _process_request_config(config, test_context=context)
            
        
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


def _deep_merge(dict1, dict2):
    """深度合并两个字典
    
    Args:
        dict1: 基础字典（会被修改）
        dict2: 要合并的字典（优先级更高）
        
    Returns:
        合并后的字典
    """
    for key in dict2:
        if key in dict1 and isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
            _deep_merge(dict1[key], dict2[key])
        else:
            dict1[key] = dict2[key]
    return dict1


def _process_assertions_with_retry(http_req, retry_count, retry_interval):
    """处理断言并支持重试
    
    Args:
        http_req: HTTP请求对象
        retry_count: 重试次数
        retry_interval: 重试间隔（秒）
    """
    
    for attempt in range(retry_count + 1):
        try:
            # 尝试执行断言
            with allure.step(f"断言验证 (尝试 {attempt + 1}/{retry_count + 1})"):
                results = http_req.process_asserts()
                # 断言成功，直接返回
                return
        except AssertionError as e:
            # 如果还有重试机会，等待后重试
            if attempt < retry_count:
                with allure.step(f"断言失败，等待 {retry_interval} 秒后重试"):
                    allure.attach(
                        str(e),
                        name="断言失败详情",
                        attachment_type=allure.attachment_type.TEXT
                    )
                    time.sleep(retry_interval)
                    # 重新发送请求
                    http_req.execute()
            else:
                # 重试次数用完，重新抛出异常
                raise 