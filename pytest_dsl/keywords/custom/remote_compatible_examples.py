"""
远程兼容关键字示例

这个模块展示了如何创建既能在本地执行又能在远程服务器上执行的关键字。
所有关键字都遵循远程与本地适配的最佳实践。
"""

from pytest_dsl.core.keyword_manager import keyword_manager


@keyword_manager.register('远程兼容文件操作', [
    {'name': '操作类型', 'mapping': 'operation', 'description': '操作类型：read/write/delete/exists'},
    {'name': '文件路径', 'mapping': 'file_path', 'description': '文件路径'},
    {'name': '文件内容', 'mapping': 'content', 'description': '文件内容（写入时使用）', 'default': None},
    {'name': '编码格式', 'mapping': 'encoding', 'description': '文件编码格式', 'default': 'utf-8'}
], category='数据/文件', tags=['远程兼容', '文件操作'])
def remote_compatible_file_operation(**kwargs):
    """远程兼容的文件操作关键字"""
    from pathlib import Path
    import os
    
    operation = kwargs.get('operation')
    file_path = kwargs.get('file_path')
    content = kwargs.get('content')
    encoding = kwargs.get('encoding', 'utf-8')
    
    # 处理路径，确保在远程环境中也能正确工作
    if not os.path.isabs(file_path):
        file_path = Path.cwd() / file_path
    else:
        file_path = Path(file_path)
    
    try:
        if operation == 'read':
            if not file_path.exists():
                return {
                    'success': False,
                    'error': f'文件不存在: {file_path}',
                    'file_path': str(file_path)
                }
            
            content = file_path.read_text(encoding=encoding)
            return {
                'success': True,
                'content': content,
                'size': len(content),
                'file_path': str(file_path),
                'encoding': encoding
            }
        
        elif operation == 'write':
            if content is None:
                return {
                    'success': False,
                    'error': '写入操作需要提供文件内容',
                    'file_path': str(file_path)
                }
            
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding=encoding)
            
            return {
                'success': True,
                'message': f'文件写入成功: {file_path}',
                'size': len(content),
                'file_path': str(file_path),
                'encoding': encoding
            }
        
        elif operation == 'delete':
            if not file_path.exists():
                return {
                    'success': False,
                    'error': f'文件不存在: {file_path}',
                    'file_path': str(file_path)
                }
            
            file_path.unlink()
            return {
                'success': True,
                'message': f'文件删除成功: {file_path}',
                'file_path': str(file_path)
            }
        
        elif operation == 'exists':
            exists = file_path.exists()
            return {
                'success': True,
                'exists': exists,
                'file_path': str(file_path),
                'is_file': file_path.is_file() if exists else False,
                'is_directory': file_path.is_dir() if exists else False
            }
        
        else:
            return {
                'success': False,
                'error': f'不支持的操作类型: {operation}',
                'supported_operations': ['read', 'write', 'delete', 'exists']
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'operation': operation,
            'file_path': str(file_path)
        }


@keyword_manager.register('远程兼容数据处理', [
    {'name': '数据', 'mapping': 'data', 'description': '要处理的数据'},
    {'name': '处理类型', 'mapping': 'process_type', 'description': '处理类型：format/validate/transform'},
    {'name': '处理参数', 'mapping': 'process_params', 'description': '处理参数字典', 'default': {}},
    {'name': '调试模式', 'mapping': 'debug_mode', 'description': '是否启用调试模式', 'default': False}
], category='数据/处理', tags=['远程兼容', '数据处理'])
def remote_compatible_data_processing(**kwargs):
    """远程兼容的数据处理关键字"""
    import json
    from datetime import datetime
    
    data = kwargs.get('data')
    process_type = kwargs.get('process_type')
    process_params = kwargs.get('process_params', {})
    debug_mode = kwargs.get('debug_mode', False)
    
    # 调试信息
    debug_info = {
        'timestamp': datetime.now().isoformat(),
        'process_type': process_type,
        'process_params': process_params,
        'data_type': type(data).__name__
    }
    
    try:
        if process_type == 'format':
            # 格式化数据
            template = process_params.get('template', '{data}')
            formatted_data = template.format(data=data)
            
            result = {
                'success': True,
                'original_data': data,
                'formatted_data': formatted_data,
                'template': template
            }
        
        elif process_type == 'validate':
            # 验证数据
            validation_rules = process_params.get('rules', {})
            validation_results = {}
            
            for rule_name, rule_config in validation_rules.items():
                if rule_name == 'not_empty':
                    validation_results[rule_name] = data is not None and str(data).strip() != ''
                elif rule_name == 'type_check':
                    expected_type = rule_config.get('type')
                    validation_results[rule_name] = type(data).__name__ == expected_type
                elif rule_name == 'length_check':
                    min_length = rule_config.get('min', 0)
                    max_length = rule_config.get('max', float('inf'))
                    data_length = len(str(data))
                    validation_results[rule_name] = min_length <= data_length <= max_length
            
            all_passed = all(validation_results.values())
            
            result = {
                'success': True,
                'data': data,
                'validation_passed': all_passed,
                'validation_results': validation_results,
                'validation_rules': validation_rules
            }
        
        elif process_type == 'transform':
            # 转换数据
            transform_type = process_params.get('type', 'string')
            
            if transform_type == 'string':
                transformed_data = str(data)
            elif transform_type == 'upper':
                transformed_data = str(data).upper()
            elif transform_type == 'lower':
                transformed_data = str(data).lower()
            elif transform_type == 'json':
                if isinstance(data, (dict, list)):
                    transformed_data = json.dumps(data, ensure_ascii=False, indent=2)
                else:
                    transformed_data = json.dumps(data, ensure_ascii=False)
            elif transform_type == 'reverse':
                transformed_data = str(data)[::-1]
            else:
                return {
                    'success': False,
                    'error': f'不支持的转换类型: {transform_type}',
                    'supported_types': ['string', 'upper', 'lower', 'json', 'reverse']
                }
            
            result = {
                'success': True,
                'original_data': data,
                'transformed_data': transformed_data,
                'transform_type': transform_type
            }
        
        else:
            return {
                'success': False,
                'error': f'不支持的处理类型: {process_type}',
                'supported_types': ['format', 'validate', 'transform']
            }
        
        debug_info['success'] = True
        debug_info['result_keys'] = list(result.keys())
        
        if debug_mode:
            result['debug_info'] = debug_info
        
        return result
    
    except Exception as e:
        debug_info['success'] = False
        debug_info['error'] = str(e)
        
        result = {
            'success': False,
            'error': str(e),
            'process_type': process_type,
            'data': data
        }
        
        if debug_mode:
            result['debug_info'] = debug_info
        
        return result


@keyword_manager.register('远程兼容HTTP请求', [
    {'name': '请求地址', 'mapping': 'url', 'description': 'HTTP请求地址'},
    {'name': '请求方法', 'mapping': 'method', 'description': 'HTTP方法', 'default': 'GET'},
    {'name': '请求头', 'mapping': 'headers', 'description': '请求头字典', 'default': {}},
    {'name': '请求数据', 'mapping': 'data', 'description': '请求数据', 'default': None},
    {'name': '超时时间', 'mapping': 'timeout', 'description': '超时时间（秒）', 'default': 30},
    {'name': '验证SSL', 'mapping': 'verify_ssl', 'description': '是否验证SSL证书', 'default': True}
], category='网络/HTTP', tags=['远程兼容', 'HTTP请求'])
def remote_compatible_http_request(**kwargs):
    """远程兼容的HTTP请求关键字"""
    url = kwargs.get('url')
    method = kwargs.get('method', 'GET').upper()
    headers = kwargs.get('headers', {})
    data = kwargs.get('data')
    timeout = kwargs.get('timeout', 30)
    verify_ssl = kwargs.get('verify_ssl', True)
    
    # 在函数内部导入，确保远程服务器也能访问
    try:
        import requests
    except ImportError:
        return {
            'success': False,
            'error': 'requests库未安装，请在远程服务器上安装requests库',
            'url': url
        }
    
    try:
        # 准备请求参数
        request_kwargs = {
            'method': method,
            'url': url,
            'headers': headers,
            'timeout': timeout,
            'verify': verify_ssl
        }
        
        # 处理请求数据
        if data is not None:
            if isinstance(data, dict) and headers.get('Content-Type', '').startswith('application/json'):
                request_kwargs['json'] = data
            else:
                request_kwargs['data'] = data
        
        # 发送请求
        response = requests.request(**request_kwargs)
        
        # 构建响应结果
        result = {
            'success': True,
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'text': response.text,
            'url': response.url,
            'method': method,
            'response_time': response.elapsed.total_seconds()
        }
        
        # 尝试解析JSON响应
        try:
            result['json'] = response.json()
        except (ValueError, requests.exceptions.JSONDecodeError):
            result['json'] = None
        
        return result
    
    except requests.exceptions.Timeout:
        return {
            'success': False,
            'error': f'请求超时（{timeout}秒）',
            'url': url,
            'timeout': timeout
        }
    except requests.exceptions.ConnectionError as e:
        return {
            'success': False,
            'error': f'连接错误: {str(e)}',
            'url': url
        }
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': f'请求异常: {str(e)}',
            'url': url
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'未知错误: {str(e)}',
            'url': url
        }
