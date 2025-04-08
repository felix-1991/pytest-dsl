import json
import re
import yaml
import jsonpath_ng.ext as jsonpath
from typing import Dict, List, Any, Union, Optional, Tuple
import lxml.etree as etree
from requests import Response
import allure

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
        
        # 解析YAML配置
        if isinstance(config, str):
            try:
                self.config = yaml.safe_load(config)
            except yaml.YAMLError as e:
                raise ValueError(f"无效的YAML配置: {str(e)}")
    
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
        
        # 提取请求参数
        method = self.config.get('method', 'GET').upper()
        url = self.config.get('url', '')
        
        # 替换URL中可能存在的变量引用
        if isinstance(url, str) and '${' in url:
            from pytest_dsl.keywords.http_keywords import _replace_variables_in_string
            url = _replace_variables_in_string(url)
        
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
        
        # 替换请求参数中的变量引用
        from pytest_dsl.keywords.http_keywords import _replace_variables_in_string
        
        # 处理JSON数据中的变量
        if 'json' in request_kwargs and request_kwargs['json']:
            request_kwargs['json'] = self._replace_variables_in_dict(request_kwargs['json'])
            
        # 处理查询参数中的变量
        if 'params' in request_kwargs and request_kwargs['params']:
            request_kwargs['params'] = self._replace_variables_in_dict(request_kwargs['params'])
            
        # 处理表单数据中的变量
        if 'data' in request_kwargs and request_kwargs['data']:
            request_kwargs['data'] = self._replace_variables_in_dict(request_kwargs['data'])
            
        # 处理请求头中的变量
        if 'headers' in request_kwargs and request_kwargs['headers']:
            request_kwargs['headers'] = self._replace_variables_in_dict(request_kwargs['headers'])
        
        # 过滤掉None值
        request_kwargs = {k: v for k, v in request_kwargs.items() if v is not None}
        
        # 使用Allure记录请求信息
        self._log_request_to_allure(method, url, request_kwargs)
        
        # 发送请求
        self.response = client.make_request(method, url, **request_kwargs)
        
        # 使用Allure记录响应信息
        self._log_response_to_allure(self.response)
        
        # 处理捕获
        self.process_captures()
        
        return self.response
    
    def process_captures(self) -> Dict[str, Any]:
        """处理响应捕获
        
        Returns:
            捕获的值字典
        """
        if not self.response:
            raise ValueError("需要先执行请求才能捕获响应")
            
        captures_config = self.config.get('captures', {})
        
        for var_name, capture_spec in captures_config.items():
            if not isinstance(capture_spec, list):
                raise ValueError(f"无效的捕获规格: {var_name}: {capture_spec}")
            
            extractor_type = capture_spec[0]
            extraction_path = capture_spec[1] if len(capture_spec) > 1 else None
            
            # 检查是否有length参数
            is_length_capture = False
            if len(capture_spec) > 2 and capture_spec[2] == "length":
                is_length_capture = True
                default_value = capture_spec[3] if len(capture_spec) > 3 else None
            else:
                default_value = capture_spec[2] if len(capture_spec) > 2 else None
            
            # 替换提取路径中的变量引用
            if isinstance(extraction_path, str) and '${' in extraction_path:
                from pytest_dsl.keywords.http_keywords import _replace_variables_in_string
                extraction_path = _replace_variables_in_string(extraction_path)
                
            # 替换默认值中的变量引用
            if isinstance(default_value, str) and '${' in default_value:
                from pytest_dsl.keywords.http_keywords import _replace_variables_in_string
                default_value = _replace_variables_in_string(default_value)
            
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
                    # 如果无法计算长度，记录错误但不抛出异常
                    allure.attach(
                        f"变量名: {var_name}\n提取器: {extractor_type}\n路径: {extraction_path}\n错误: 无法计算长度: {str(e)}",
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
        
        return self.captured_values
    
    def process_asserts(self) -> List[Dict[str, Any]]:
        """处理响应断言
        
        Returns:
            断言结果列表
        """
        if not self.response:
            raise ValueError("需要先执行请求才能进行断言")
            
        asserts_config = self.config.get('asserts', [])
        assert_results = []
        
        for assertion in asserts_config:
            if not isinstance(assertion, list) or len(assertion) < 2:
                raise ValueError(f"无效的断言配置: {assertion}")
            
            # 提取断言参数
            extractor_type = assertion[0]
            
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
            
            # 替换expected_value中的变量引用
            if isinstance(expected_value, str) and '${' in expected_value:
                from pytest_dsl.keywords.http_keywords import _replace_variables_in_string
                expected_value = _replace_variables_in_string(expected_value)
            
            # 提取实际值
            actual_value = self._extract_value(extractor_type, extraction_path)
            
            # 特殊处理"length"断言类型
            original_actual_value = actual_value
            if assertion_type == "length" and extractor_type != "response_time" and extractor_type != "status" and extractor_type != "body":
                try:
                    actual_value = len(actual_value)
                except:
                    actual_value = None
            
            # 执行断言
            result = self._perform_assertion(assertion_type, compare_operator, actual_value, expected_value)
            
            # 记录断言结果
            assertion_result = {
                'extractor': extractor_type,
                'path': extraction_path,
                'type': assertion_type,
                'operator': compare_operator,
                'expected': expected_value,
                'actual': original_actual_value if assertion_type == "length" else actual_value,
                'result': result
            }
            assert_results.append(assertion_result)
            
            # 记录断言到Allure
            if result:
                allure.attach(
                    f"提取器: {extractor_type}\n路径: {extraction_path}\n断言类型: {assertion_type}\n操作符: {compare_operator}\n预期值: {expected_value}\n实际值: {original_actual_value if assertion_type == 'length' else actual_value}" + (f"\n长度: {actual_value}" if assertion_type == "length" else ""),
                    name=f"断言成功: {extractor_type} {assertion_type}",
                    attachment_type=allure.attachment_type.TEXT
                )
            else:
                allure.attach(
                    f"提取器: {extractor_type}\n路径: {extraction_path}\n断言类型: {assertion_type}\n操作符: {compare_operator}\n预期值: {expected_value}\n实际值: {original_actual_value if assertion_type == 'length' else actual_value}" + (f"\n长度: {actual_value}" if assertion_type == "length" else ""),
                    name=f"断言失败: {extractor_type} {assertion_type}",
                    attachment_type=allure.attachment_type.TEXT
                )
                raise AssertionError(f"断言失败: {extractor_type}({extraction_path}) {assertion_type} {compare_operator} {expected_value}, 实际值: {original_actual_value if assertion_type == 'length' else actual_value}" + (f", 长度: {actual_value}" if assertion_type == "length" else ""))
        
        return assert_results
    
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
            if isinstance(expected_value, str) and expected_value.isdigit():
                expected_value = int(expected_value)
            elif isinstance(expected_value, str) and expected_value.replace('.', '', 1).isdigit():
                expected_value = float(expected_value)
                
            if isinstance(actual_value, str) and actual_value.isdigit():
                actual_value = int(actual_value)
            elif isinstance(actual_value, str) and actual_value.replace('.', '', 1).isdigit():
                actual_value = float(actual_value)
        
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
            try:
                if actual_value is None:
                    return False
                return bool(re.search(expected_value, str(actual_value)))
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
    
    def _replace_variables_in_dict(self, data):
        """递归替换字典中的变量引用
        
        Args:
            data: 包含变量引用的字典、列表或字符串
            
        Returns:
            替换变量后的数据
        """
        from pytest_dsl.keywords.http_keywords import _replace_variables_in_string
        
        if isinstance(data, dict):
            return {k: self._replace_variables_in_dict(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._replace_variables_in_dict(item) for item in data]
        elif isinstance(data, str) and '${' in data:
            return _replace_variables_in_string(data)
        else:
            return data 