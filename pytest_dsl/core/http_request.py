import json
import re
import yaml
import jsonpath_ng.ext as jsonpath
from typing import Dict, List, Any, Union, Optional, Tuple
import lxml.etree as etree
from requests import Response
import allure
import requests

from pytest_dsl.core.http_client import http_client_manager


class HTTPRequest:
    """HTTP请求处理类
    
    负责处理HTTP请求、响应捕获和断言
    """
    
    def __init__(self, config: Dict[str, Any], client_name: str = "default", session_name: str = None):
        """初始化HTTP请求
        
        Args:
            config: 请求配置
            client_name: 客户端名称
            session_name: 会话名称（如果需要使用命名会话）
        """
        self.config = config
        self.client_name = client_name
        self.session_name = session_name
        self.response = None
        self.captured_values = {}
    
    def execute(self, disable_auth: bool = False) -> Response:
        """执行HTTP请求
        
        Args:
            disable_auth: 是否禁用认证
            
        Returns:
            Response对象
        """
        # 获取HTTP客户端
        if self.session_name:
            client = http_client_manager.get_session(self.session_name, self.client_name)
        else:
            client = http_client_manager.get_client(self.client_name)
            
        # 验证客户端有效性
        if client is None:
            error_message = f"无法获取HTTP客户端: {self.client_name}"
            allure.attach(
                error_message,
                name="HTTP客户端错误",
                attachment_type=allure.attachment_type.TEXT
            )
            raise ValueError(error_message)
        
        # 提取请求参数
        method = self.config.get('method', 'GET').upper()
        url = self.config.get('url', '')
        
        # 配置中是否禁用认证
        disable_auth = disable_auth or self.config.get('disable_auth', False)
        
        request_config = self.config.get('request', {})
        
        # 构建请求参数
        request_kwargs = {
            'params': request_config.get('params'),
            'headers': request_config.get('headers'),
            'json': request_config.get('json'),
            'data': request_config.get('data'),
            'files': request_config.get('files'),
            'cookies': request_config.get('cookies'),
            'auth': tuple(request_config.get('auth')) if request_config.get('auth') else None,
            'timeout': request_config.get('timeout'),
            'allow_redirects': request_config.get('allow_redirects'),
            'verify': request_config.get('verify'),
            'cert': request_config.get('cert'),
            'proxies': request_config.get('proxies'),
            'disable_auth': disable_auth  # 传递禁用认证标志
        }
        
        # 过滤掉None值
        request_kwargs = {k: v for k, v in request_kwargs.items() if v is not None}
        
        # 使用Allure记录请求信息
        self._log_request_to_allure(method, url, request_kwargs)
        
        try:
            # 发送请求
            self.response = client.make_request(method, url, **request_kwargs)
            
            # 使用Allure记录响应信息
            self._log_response_to_allure(self.response)
            
            # 处理捕获
            self.process_captures()
            
            return self.response
        except requests.exceptions.RequestException as e:
            # 记录请求异常到Allure
            error_message = f"请求异常: {str(e)}"
            allure.attach(
                error_message,
                name=f"HTTP请求失败: {method} {url}",
                attachment_type=allure.attachment_type.TEXT
            )
            
            # 重新抛出更有意义的异常
            raise ValueError(f"HTTP请求失败: {str(e)}") from e
        except Exception as e:
            # 捕获所有其他异常
            error_message = f"未预期的异常: {type(e).__name__}: {str(e)}"
            allure.attach(
                error_message,
                name=f"HTTP请求执行错误: {method} {url}",
                attachment_type=allure.attachment_type.TEXT
            )
            
            # 重新抛出异常
            raise ValueError(f"HTTP请求执行错误: {str(e)}") from e
    
    def process_captures(self) -> Dict[str, Any]:
        """处理响应捕获
        
        Returns:
            捕获的值字典
        """
        if not self.response:
            error_message = "需要先执行请求才能捕获响应"
            # 记录更详细的错误信息到Allure
            debug_info = (
                f"错误详情: self.response 为 None\n"
                f"配置信息: {json.dumps(self.config, indent=2, ensure_ascii=False, default=str)}\n"
                f"当前状态: 客户端名称={self.client_name}, 会话名称={self.session_name}"
            )
            allure.attach(
                debug_info,
                name="捕获失败详情",
                attachment_type=allure.attachment_type.TEXT
            )
            raise ValueError(error_message)
            
        captures_config = self.config.get('captures', {})
        
        for var_name, capture_spec in captures_config.items():
            if not isinstance(capture_spec, list):
                raise ValueError(f"无效的捕获规格: {var_name}: {capture_spec}")
            
            # 提取捕获信息
            try:
                extractor_type = capture_spec[0]
                extraction_path = capture_spec[1] if len(capture_spec) > 1 else None
                
                # 检查是否有length参数
                is_length_capture = False
                if len(capture_spec) > 2 and capture_spec[2] == "length":
                    is_length_capture = True
                    default_value = capture_spec[3] if len(capture_spec) > 3 else None
                else:
                    default_value = capture_spec[2] if len(capture_spec) > 2 else None
                
                # 提取值
                captured_value = self._extract_value(extractor_type, extraction_path, default_value)
                
                # 特殊处理length
                if is_length_capture:
                    try:
                        original_value = captured_value
                        captured_value = len(captured_value)
                        
                        # 记录长度到Allure
                        allure.attach(
                            f"变量名: {var_name}\n提取器: {extractor_type}\n路径: {extraction_path}\n原始值: {str(original_value)}\n长度: {captured_value}",
                            name=f"捕获长度: {var_name}",
                            attachment_type=allure.attachment_type.TEXT
                        )
                    except Exception as e:
                        # 如果无法计算长度，记录错误并添加请求和响应信息
                        error_msg = f"变量名: {var_name}\n提取器: {extractor_type}\n路径: {extraction_path}\n错误: 无法计算长度: {str(e)}"
                        
                        # 添加请求信息
                        error_msg += "\n\n=== 请求信息 ==="
                        error_msg += f"\nMethod: {self.config.get('method', 'GET')}"
                        error_msg += f"\nURL: {self.config.get('url', '')}"
                        if 'headers' in self.config.get('request', {}):
                            error_msg += "\nHeaders: " + str(self.config.get('request', {}).get('headers', {}))
                        if 'params' in self.config.get('request', {}):
                            error_msg += "\nParams: " + str(self.config.get('request', {}).get('params', {}))
                        if 'json' in self.config.get('request', {}):
                            error_msg += "\nJSON Body: " + str(self.config.get('request', {}).get('json', {}))
                        
                        # 添加响应信息
                        error_msg += "\n\n=== 响应信息 ==="
                        error_msg += f"\nStatus: {self.response.status_code} {self.response.reason}"
                        error_msg += f"\nHeaders: {dict(self.response.headers)}"
                        try:
                            if 'application/json' in self.response.headers.get('Content-Type', ''):
                                error_msg += f"\nBody: {json.dumps(self.response.json(), ensure_ascii=False)}"
                            else:
                                error_msg += f"\nBody: {self.response.text}"
                        except:
                            error_msg += "\nBody: <无法解析响应体>"
                        
                        allure.attach(
                            error_msg,
                            name=f"捕获长度失败: {var_name}",
                            attachment_type=allure.attachment_type.TEXT
                        )
                        captured_value = 0  # 默认长度
                else:
                    # 记录捕获到Allure
                    allure.attach(
                        f"变量名: {var_name}\n提取器: {extractor_type}\n路径: {extraction_path}\n提取值: {str(captured_value)}",
                        name=f"捕获变量: {var_name}",
                        attachment_type=allure.attachment_type.TEXT
                    )
                
                self.captured_values[var_name] = captured_value
            except Exception as e:
                error_msg = (
                    f"变量捕获失败: {var_name}\n"
                    f"捕获规格: {capture_spec}\n"
                    f"错误: {type(e).__name__}: {str(e)}"
                )
                allure.attach(
                    error_msg,
                    name=f"变量捕获失败: {var_name}",
                    attachment_type=allure.attachment_type.TEXT
                )
                # 设置默认值
                self.captured_values[var_name] = None
        
        return self.captured_values
    
    def process_asserts(self, specific_asserts=None) -> List[Dict[str, Any]]:
        """处理响应断言
        
        Args:
            specific_asserts: 指定要处理的断言列表，如果为None则处理所有断言
            
        Returns:
            断言结果列表
        """
        if not self.response:
            raise ValueError("需要先执行请求才能进行断言")
            
        asserts_config = self.config.get('asserts', [])
        assert_results = []
        failed_retryable_assertions = []
        
        # 处理断言重试配置
        # 1. 只使用独立的retry_assertions配置
        retry_assertions_config = self.config.get('retry_assertions', {})
        has_dedicated_retry_config = bool(retry_assertions_config)
        
        # 2. 向后兼容: 检查全局retry配置（仅作为默认值使用）
        retry_config = self.config.get('retry', {})
        global_retry_enabled = bool(retry_config)
        
        # 3. 提取重试默认设置
        global_retry_count = retry_assertions_config.get('count', retry_config.get('count', 3))
        global_retry_interval = retry_assertions_config.get('interval', retry_config.get('interval', 1))
        
        # 4. 提取应该重试的断言索引列表
        retry_all_assertions = retry_assertions_config.get('all', global_retry_enabled)
        retry_assertion_indices = retry_assertions_config.get('indices', [])
        
        # 5. 提取特定断言的重试配置
        specific_assertion_configs = retry_assertions_config.get('specific', {})
        
        # 如果传入了specific_asserts，只处理指定的断言
        process_asserts = specific_asserts if specific_asserts is not None else asserts_config
        
        for assertion_idx, assertion in enumerate(process_asserts):
            if not isinstance(assertion, list) or len(assertion) < 2:
                raise ValueError(f"无效的断言配置: {assertion}")
            
            # 提取断言参数
            extractor_type = assertion[0]
            
            # 判断该断言是否应该重试（只使用retry_assertions配置）
            is_retryable = False
            assertion_retry_count = global_retry_count
            assertion_retry_interval = global_retry_interval
            
            # retry_assertions特定配置
            if str(assertion_idx) in specific_assertion_configs:
                spec_config = specific_assertion_configs[str(assertion_idx)]
                is_retryable = True
                if isinstance(spec_config, dict):
                    if 'count' in spec_config:
                        assertion_retry_count = spec_config['count']
                    if 'interval' in spec_config:
                        assertion_retry_interval = spec_config['interval']
            # retry_assertions索引列表
            elif assertion_idx in retry_assertion_indices:
                is_retryable = True
            # retry_assertions全局配置
            elif retry_all_assertions:
                is_retryable = True
            
            # 处理断言参数
            if len(assertion) == 2:  # 存在性断言 ["header", "Location", "exists"]
                extraction_path = assertion[1]
                assertion_type = "exists"
                expected_value = None
                compare_operator = "eq"  # 默认比较操作符
            elif len(assertion) == 3:  # 简单断言 ["status", "eq", 200]
                if extractor_type in ["status", "body", "response_time"]:
                    extraction_path = None
                    assertion_type = "value"  # 标记为简单值比较
                    compare_operator = assertion[1]  # 比较操作符
                    expected_value = assertion[2]  # 预期值
                else:
                    extraction_path = assertion[1]
                    assertion_type = assertion[2]
                    compare_operator = "eq"  # 默认比较操作符
                    expected_value = None
            elif len(assertion) == 4:  # 带操作符的断言 ["jsonpath", "$.id", "eq", 1]
                extraction_path = assertion[1]
                if assertion[2] in ["eq", "neq", "lt", "lte", "gt", "gte"]:
                    # 这是带比较操作符的断言
                    assertion_type = "value"  # 标记为值比较
                    compare_operator = assertion[2]  # 比较操作符
                    expected_value = assertion[3]  # 预期值
                else:
                    # 其他类型的断言，比如特殊断言
                    assertion_type = assertion[2]
                    compare_operator = "eq"  # 默认比较操作符
                    expected_value = assertion[3]
            else:  # 5个参数，例如 ["jsonpath", "$", "length", "eq", 10]
                extraction_path = assertion[1]
                assertion_type = assertion[2]
                compare_operator = assertion[3]
                expected_value = assertion[4]
            
            # 提取实际值
            actual_value = self._extract_value(extractor_type, extraction_path)
            
            # 特殊处理"length"断言类型
            original_actual_value = actual_value
            if assertion_type == "length" and extractor_type != "response_time" and extractor_type != "status" and extractor_type != "body":
                try:
                    actual_value = len(actual_value)
                except Exception as e:
                    # 长度计算失败的信息已在_extract_value中记录
                    actual_value = 0
            
            # 执行断言
            assertion_result = {
                'type': extractor_type,
                'path': extraction_path,
                'assertion_type': assertion_type,
                'operator': compare_operator,
                'actual_value': actual_value,
                'expected_value': expected_value,
                'original_value': original_actual_value if assertion_type == "length" else None,
                'retryable': is_retryable,
                'retry_count': assertion_retry_count,
                'retry_interval': assertion_retry_interval,
                'index': assertion_idx  # 记录断言在原始列表中的索引
            }
            
            try:
                # 验证断言
                result = self._perform_assertion(assertion_type, compare_operator, actual_value, expected_value)
                assertion_result['result'] = result
                assertion_result['passed'] = True
                
                # 使用Allure记录断言成功
                allure.attach(
                    self._format_assertion_details(assertion_result),
                    name=f"断言成功: {extractor_type}",
                    attachment_type=allure.attachment_type.TEXT
                )
            except AssertionError as e:
                assertion_result['result'] = False
                assertion_result['passed'] = False
                assertion_result['error'] = str(e)
                
                # 使用Allure记录断言失败
                allure.attach(
                    self._format_assertion_details(assertion_result) + f"\n\n错误: {str(e)}",
                    name=f"断言失败: {extractor_type}",
                    attachment_type=allure.attachment_type.TEXT
                )
                
                # 如果断言可重试，添加到失败且需要重试的断言列表
                if is_retryable:
                    failed_retryable_assertions.append(assertion_result)
                
                # 抛出异常（会在外层捕获）
                raise AssertionError(f"断言失败 [{extractor_type}]: {str(e)}")
            
            assert_results.append(assertion_result)
        
        # 返回断言结果和需要重试的断言
        return assert_results, failed_retryable_assertions
    
    def _format_assertion_details(self, assertion_result: Dict[str, Any]) -> str:
        """格式化断言详情，用于Allure报告
        
        Args:
            assertion_result: 断言结果字典
            
        Returns:
            格式化的断言详情字符串
        """
        details = f"类型: {assertion_result['type']}\n"
        if assertion_result['path']:
            details += f"路径: {assertion_result['path']}\n"
        
        if assertion_result['assertion_type'] == 'length':
            details += f"原始值: {assertion_result['original_value']}\n"
            details += f"长度: {assertion_result['actual_value']}\n"
        else:
            details += f"实际值: {assertion_result['actual_value']}\n"
            
        details += f"操作符: {assertion_result['operator']}\n"
        
        if assertion_result['expected_value'] is not None:
            details += f"预期值: {assertion_result['expected_value']}\n"
            
        details += f"结果: {'通过' if assertion_result['passed'] else '失败'}"
        
        return details
    
    def _extract_value(self, extractor_type: str, extraction_path: str = None, default_value: Any = None) -> Any:
        """从响应提取值
        
        Args:
            extractor_type: 提取器类型
            extraction_path: 提取路径
            default_value: 默认值
            
        Returns:
            提取的值
        """
        if not self.response:
            return default_value
        
        try:
            if extractor_type == "jsonpath":
                return self._extract_jsonpath(extraction_path, default_value)
            elif extractor_type == "xpath":
                return self._extract_xpath(extraction_path, default_value)
            elif extractor_type == "regex":
                return self._extract_regex(extraction_path, default_value)
            elif extractor_type == "header":
                return self._extract_header(extraction_path, default_value)
            elif extractor_type == "cookie":
                return self._extract_cookie(extraction_path, default_value)
            elif extractor_type == "status":
                return self.response.status_code
            elif extractor_type == "body":
                return self.response.text
            elif extractor_type == "response_time":
                return self.response.elapsed.total_seconds() * 1000
            else:
                raise ValueError(f"不支持的提取器类型: {extractor_type}")
        except Exception as e:
            if default_value is not None:
                return default_value
            raise ValueError(f"提取值失败({extractor_type}, {extraction_path}): {str(e)}")
    
    def _extract_jsonpath(self, path: str, default_value: Any = None) -> Any:
        """使用JSONPath从JSON响应提取值
        
        Args:
            path: JSONPath表达式
            default_value: 默认值
            
        Returns:
            提取的值
        """
        try:
            json_data = self.response.json()
            
            jsonpath_expr = jsonpath.parse(path)
            matches = [match.value for match in jsonpath_expr.find(json_data)]
            
            if not matches:
                return default_value
            elif len(matches) == 1:
                return matches[0]
            else:
                return matches
        except Exception as e:
            if default_value is not None:
                return default_value
            raise ValueError(f"JSONPath提取失败: {str(e)}")
    
    def _extract_xpath(self, path: str, default_value: Any = None) -> Any:
        """使用XPath从HTML/XML响应提取值
        
        Args:
            path: XPath表达式
            default_value: 默认值
            
        Returns:
            提取的值
        """
        try:
            # 尝试解析响应内容
            parser = etree.HTMLParser()
            tree = etree.fromstring(self.response.content, parser)
            
            # 执行XPath
            result = tree.xpath(path)
            
            if not result:
                return default_value
            elif len(result) == 1:
                return result[0]
            else:
                return result
        except Exception as e:
            if default_value is not None:
                return default_value
            raise ValueError(f"XPath提取失败: {str(e)}")
    
    def _extract_regex(self, pattern: str, default_value: Any = None) -> Any:
        """使用正则表达式从响应提取值
        
        Args:
            pattern: 正则表达式模式
            default_value: 默认值
            
        Returns:
            提取的值
        """
        try:
            # 如果响应是JSON格式，先转换为字符串
            if 'application/json' in self.response.headers.get('Content-Type', ''):
                text = json.dumps(self.response.json())
            else:
                text = self.response.text
                
            matches = re.findall(pattern, text)
            
            if not matches:
                return default_value
            elif len(matches) == 1:
                return matches[0]
            else:
                return matches
        except Exception as e:
            if default_value is not None:
                return default_value
            raise ValueError(f"正则表达式提取失败: {str(e)}")
    
    def _extract_header(self, header_name: str, default_value: Any = None) -> Any:
        """从响应头提取值
        
        Args:
            header_name: 响应头名称
            default_value: 默认值
            
        Returns:
            提取的值
        """
        header_value = self.response.headers.get(header_name)
        return header_value if header_value is not None else default_value
    
    def _extract_cookie(self, cookie_name: str, default_value: Any = None) -> Any:
        """从响应Cookie提取值
        
        Args:
            cookie_name: Cookie名称
            default_value: 默认值
            
        Returns:
            提取的值
        """
        cookie = self.response.cookies.get(cookie_name)
        return cookie if cookie is not None else default_value
    
    def _perform_assertion(self, assertion_type: str, operator: str, actual_value: Any, expected_value: Any = None) -> bool:
        """执行断言
        
        Args:
            assertion_type: 断言类型
            operator: 比较操作符
            actual_value: 实际值
            expected_value: 预期值
            
        Returns:
            断言结果
        """
        # 类型转换
        if operator in ["eq", "neq", "lt", "lte", "gt", "gte"] and expected_value is not None:
            if isinstance(expected_value, str):
                # 去除空白字符和换行符后再判断
                clean_expected = expected_value.strip()
                if clean_expected.isdigit():
                    expected_value = int(clean_expected)
                elif clean_expected.replace('.', '', 1).isdigit():
                    expected_value = float(clean_expected)
                
            if isinstance(actual_value, str):
                # 去除空白字符和换行符后再判断
                clean_actual = actual_value.strip()
                if clean_actual.isdigit():
                    actual_value = int(clean_actual)
                elif clean_actual.replace('.', '', 1).isdigit():
                    actual_value = float(clean_actual)
        
        # 基于断言类型执行断言
        if assertion_type == "value" or assertion_type == "length":
            # 直接使用操作符进行比较
            return self._compare_values(actual_value, expected_value, operator)
        elif assertion_type == "exists":
            return actual_value is not None
        elif assertion_type == "not_exists":
            return actual_value is None
        elif assertion_type == "type":
            if expected_value == "string":
                return isinstance(actual_value, str)
            elif expected_value == "number":
                return isinstance(actual_value, (int, float))
            elif expected_value == "boolean":
                return isinstance(actual_value, bool)
            elif expected_value == "array":
                return isinstance(actual_value, list)
            elif expected_value == "object":
                return isinstance(actual_value, dict)
            elif expected_value == "null":
                return actual_value is None
            return False
        elif assertion_type == "contains":
            if isinstance(actual_value, str) and isinstance(expected_value, str):
                return expected_value in actual_value
            elif isinstance(actual_value, (list, tuple, dict)):
                return expected_value in actual_value
            return False
        elif assertion_type == "startswith":
            return isinstance(actual_value, str) and actual_value.startswith(expected_value)
        elif assertion_type == "endswith":
            return isinstance(actual_value, str) and actual_value.endswith(expected_value)
        elif assertion_type == "matches":
            if not isinstance(actual_value, str) or not isinstance(expected_value, str):
                return False
            try:
                import re
                return bool(re.search(expected_value, actual_value))
            except:
                return False
        elif assertion_type == "in":
            return actual_value in expected_value
        elif assertion_type == "not_in":
            return actual_value not in expected_value
        elif assertion_type == "schema":
            try:
                from jsonschema import validate
                validate(instance=actual_value, schema=expected_value)
                return True
            except:
                return False
        else:
            raise ValueError(f"不支持的断言类型: {assertion_type}")
    
    def _compare_values(self, actual_value: Any, expected_value: Any, operator: str) -> bool:
        """比较两个值
        
        Args:
            actual_value: 实际值
            expected_value: 预期值
            operator: 比较操作符
            
        Returns:
            比较结果
        """
        if operator == "eq":
            return actual_value == expected_value
        elif operator == "neq":
            return actual_value != expected_value
        elif operator == "lt":
            return actual_value < expected_value
        elif operator == "lte":
            return actual_value <= expected_value
        elif operator == "gt":
            return actual_value > expected_value
        elif operator == "gte":
            return actual_value >= expected_value
        elif operator == "in":
            return actual_value in expected_value
        elif operator == "not_in":
            return actual_value not in expected_value
        elif operator == "contains":
            if isinstance(actual_value, str) and isinstance(expected_value, str):
                return expected_value in actual_value
            elif isinstance(actual_value, (list, tuple, dict)):
                return expected_value in actual_value
            return False
        elif operator == "not_contains":
            if isinstance(actual_value, str) and isinstance(expected_value, str):
                return expected_value not in actual_value
            elif isinstance(actual_value, (list, tuple, dict)):
                return expected_value not in actual_value
            return True
        elif operator == "matches":
            if not isinstance(actual_value, str) or not isinstance(expected_value, str):
                return False
            try:
                import re
                return bool(re.search(expected_value, actual_value))
            except:
                return False
        else:
            raise ValueError(f"不支持的比较操作符: {operator}")
    
    def _log_request_to_allure(self, method: str, url: str, request_kwargs: Dict[str, Any]) -> None:
        """使用Allure记录请求信息
        
        Args:
            method: HTTP方法
            url: 请求URL
            request_kwargs: 请求参数
        """
        # 创建请求信息摘要
        request_summary = f"{method} {url}"
        
        # 创建详细请求信息
        request_details = [f"Method: {method}", f"URL: {url}"]
        
        # 添加请求头
        if "headers" in request_kwargs and request_kwargs["headers"]:
            # 隐藏敏感信息
            safe_headers = {}
            for key, value in request_kwargs["headers"].items():
                if key.lower() in ["authorization", "x-api-key", "token", "api-key"]:
                    safe_headers[key] = "***REDACTED***"
                else:
                    safe_headers[key] = value
            request_details.append("Headers:")
            for key, value in safe_headers.items():
                request_details.append(f"  {key}: {value}")
        
        # 添加查询参数
        if "params" in request_kwargs and request_kwargs["params"]:
            request_details.append("Query Parameters:")
            for key, value in request_kwargs["params"].items():
                request_details.append(f"  {key}: {value}")
        
        # 添加请求体
        if "json" in request_kwargs and request_kwargs["json"]:
            request_details.append("JSON Body:")
            try:
                request_details.append(json.dumps(request_kwargs["json"], indent=2, ensure_ascii=False))
            except:
                request_details.append(str(request_kwargs["json"]))
        elif "data" in request_kwargs and request_kwargs["data"]:
            request_details.append("Form Data:")
            for key, value in request_kwargs["data"].items():
                request_details.append(f"  {key}: {value}")
        
        # 添加文件信息
        if "files" in request_kwargs and request_kwargs["files"]:
            request_details.append("Files:")
            for key, value in request_kwargs["files"].items():
                request_details.append(f"  {key}: <File object>")
        
        # 记录到Allure
        allure.attach(
            "\n".join(request_details),
            name=f"HTTP请求: {request_summary}",
            attachment_type=allure.attachment_type.TEXT
        )
    
    def _log_response_to_allure(self, response: Response) -> None:
        """使用Allure记录响应信息
        
        Args:
            response: 响应对象
        """
        # 创建响应信息摘要
        response_summary = f"{response.status_code} {response.reason} ({response.elapsed.total_seconds() * 1000:.2f}ms)"
        
        # 创建详细响应信息
        response_details = [
            f"Status: {response.status_code} {response.reason}",
            f"Response Time: {response.elapsed.total_seconds() * 1000:.2f}ms"
        ]
        
        # 添加响应头
        response_details.append("Headers:")
        for key, value in response.headers.items():
            response_details.append(f"  {key}: {value}")
        
        # 添加响应体
        response_details.append("Body:")
        try:
            if 'application/json' in response.headers.get('Content-Type', ''):
                response_details.append(json.dumps(response.json(), indent=2, ensure_ascii=False))
            elif len(response.content) < 10240:  # 限制大小
                response_details.append(response.text)
            else:
                response_details.append(f"<{len(response.content)} bytes>")
        except Exception as e:
            response_details.append(f"<Error parsing body: {str(e)}>")
        
        # 记录到Allure
        allure.attach(
            "\n".join(response_details),
            name=f"HTTP响应: {response_summary}",
            attachment_type=allure.attachment_type.TEXT
        ) 