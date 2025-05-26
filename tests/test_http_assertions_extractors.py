#!/usr/bin/env python3
"""
测试HTTP请求关键字的断言和提取器功能
验证API文档和实现之间的一致性
"""

import pytest
import json
from unittest.mock import Mock, patch
from pytest_dsl.core.http_request import HTTPRequest
from pytest_dsl.core.context import TestContext


class TestHTTPExtractors:
    """测试HTTP提取器功能"""

    def setup_method(self):
        """设置测试环境"""
        self.context = TestContext()

        # 创建模拟响应
        self.mock_response = Mock()
        self.mock_response.status_code = 200
        self.mock_response.headers = {
            'Content-Type': 'application/json',
            'Location': 'https://api.example.com/users/123',
            'X-Custom-Header': 'custom-value'
        }
        self.mock_response.cookies = {'session_id': 'abc123', 'user_pref': 'dark'}
        self.mock_response.text = '{"id": 123, "name": "John", "items": [1, 2, 3], "active": true}'
        self.mock_response.json.return_value = {
            "id": 123,
            "name": "John",
            "items": [1, 2, 3],
            "active": True
        }
        self.mock_response.elapsed.total_seconds.return_value = 0.5
        self.mock_response.content = b'<html><h1>Herman Melville</h1><p>Some text</p></html>'

    def test_jsonpath_extractor(self):
        """测试JSONPath提取器"""
        config = {
            'captures': {
                'user_id': ['jsonpath', '$.id'],
                'user_name': ['jsonpath', '$.name'],
                'item_count': ['jsonpath', '$.items.length()'],
                'first_item': ['jsonpath', '$.items[0]'],
                'all_items': ['jsonpath', '$.items[*]']
            }
        }

        http_req = HTTPRequest(config)
        http_req.response = self.mock_response
        http_req.process_captures()

        assert http_req.captured_values['user_id'] == 123
        assert http_req.captured_values['user_name'] == "John"
        assert http_req.captured_values['first_item'] == 1
        assert http_req.captured_values['all_items'] == [1, 2, 3]

    def test_header_extractor(self):
        """测试Header提取器"""
        config = {
            'captures': {
                'location': ['header', 'Location'],
                'content_type': ['header', 'Content-Type'],
                'custom_header': ['header', 'X-Custom-Header'],
                'missing_header': ['header', 'X-Missing', 'default_value']
            }
        }

        http_req = HTTPRequest(config)
        http_req.response = self.mock_response
        http_req.process_captures()

        assert http_req.captured_values['location'] == 'https://api.example.com/users/123'
        assert http_req.captured_values['content_type'] == 'application/json'
        assert http_req.captured_values['custom_header'] == 'custom-value'
        assert http_req.captured_values['missing_header'] == 'default_value'

    def test_cookie_extractor(self):
        """测试Cookie提取器"""
        config = {
            'captures': {
                'session': ['cookie', 'session_id'],
                'preference': ['cookie', 'user_pref'],
                'missing_cookie': ['cookie', 'missing', 'default']
            }
        }

        http_req = HTTPRequest(config)
        http_req.response = self.mock_response
        http_req.process_captures()

        assert http_req.captured_values['session'] == 'abc123'
        assert http_req.captured_values['preference'] == 'dark'
        assert http_req.captured_values['missing_cookie'] == 'default'

    def test_status_extractor(self):
        """测试Status提取器"""
        config = {
            'captures': {
                'status_code': ['status']
            }
        }

        http_req = HTTPRequest(config)
        http_req.response = self.mock_response
        http_req.process_captures()

        assert http_req.captured_values['status_code'] == 200

    def test_body_extractor(self):
        """测试Body提取器"""
        config = {
            'captures': {
                'response_body': ['body']
            }
        }

        http_req = HTTPRequest(config)
        http_req.response = self.mock_response
        http_req.process_captures()

        assert http_req.captured_values['response_body'] == '{"id": 123, "name": "John", "items": [1, 2, 3], "active": true}'

    def test_response_time_extractor(self):
        """测试ResponseTime提取器"""
        config = {
            'captures': {
                'response_time': ['response_time']
            }
        }

        http_req = HTTPRequest(config)
        http_req.response = self.mock_response
        http_req.process_captures()

        assert http_req.captured_values['response_time'] == 500.0  # 0.5秒 = 500毫秒

    def test_regex_extractor(self):
        """测试Regex提取器"""
        config = {
            'captures': {
                'user_id_regex': ['regex', r'"id":\s*(\d+)'],
                'name_regex': ['regex', r'"name":\s*"([^"]+)"']
            }
        }

        http_req = HTTPRequest(config)
        http_req.response = self.mock_response
        http_req.process_captures()

        assert http_req.captured_values['user_id_regex'] == '123'
        assert http_req.captured_values['name_regex'] == 'John'

    @patch('lxml.etree.fromstring')
    def test_xpath_extractor(self, mock_fromstring):
        """测试XPath提取器"""
        # 模拟XPath解析
        mock_tree = Mock()
        mock_tree.xpath.return_value = ['Herman Melville']
        mock_fromstring.return_value = mock_tree

        config = {
            'captures': {
                'title': ['xpath', '//h1/text()']
            }
        }

        http_req = HTTPRequest(config)
        http_req.response = self.mock_response
        http_req.process_captures()

        assert http_req.captured_values['title'] == 'Herman Melville'


class TestHTTPAssertions:
    """测试HTTP断言功能"""

    def setup_method(self):
        """设置测试环境"""
        self.context = TestContext()

        # 创建模拟响应
        self.mock_response = Mock()
        self.mock_response.status_code = 200
        self.mock_response.headers = {'Content-Type': 'application/json'}
        self.mock_response.text = '{"id": 123, "name": "John", "items": [1, 2, 3], "active": true}'
        self.mock_response.json.return_value = {
            "id": 123,
            "name": "John",
            "items": [1, 2, 3],
            "active": True
        }
        self.mock_response.elapsed.total_seconds.return_value = 0.5

    def test_basic_assertions(self):
        """测试基本断言"""
        config = {
            'asserts': [
                ['status', 'eq', 200],
                ['jsonpath', '$.id', 'eq', 123],
                ['jsonpath', '$.name', 'eq', 'John'],
                ['jsonpath', '$.active', 'eq', True]
            ]
        }

        http_req = HTTPRequest(config)
        http_req.response = self.mock_response
        results, failed = http_req.process_asserts()

        assert len(results) == 4
        assert all(result['result'] for result in results)
        assert len(failed) == 0

    def test_comparison_assertions(self):
        """测试比较断言"""
        config = {
            'asserts': [
                ['jsonpath', '$.id', 'gt', 100],
                ['jsonpath', '$.id', 'lt', 200],
                ['jsonpath', '$.id', 'gte', 123],
                ['jsonpath', '$.id', 'lte', 123],
                ['jsonpath', '$.id', 'neq', 456]
            ]
        }

        http_req = HTTPRequest(config)
        http_req.response = self.mock_response
        results, failed = http_req.process_asserts()

        assert len(results) == 5
        assert all(result['result'] for result in results)
        assert len(failed) == 0

    def test_string_assertions(self):
        """测试字符串断言"""
        config = {
            'asserts': [
                ['jsonpath', '$.name', 'contains', 'oh'],
                ['jsonpath', '$.name', 'startswith', 'Jo'],
                ['jsonpath', '$.name', 'endswith', 'hn'],
                ['body', 'matches', r'"name":\s*"John"']
            ]
        }

        http_req = HTTPRequest(config)
        http_req.response = self.mock_response
        results, failed = http_req.process_asserts()

        assert len(results) == 4
        assert all(result['result'] for result in results)
        assert len(failed) == 0

    def test_string_assertions_as_operators(self):
        """测试字符串断言作为操作符使用"""
        config = {
            'asserts': [
                ['jsonpath', '$.name', 'contains', 'oh'],
                ['jsonpath', '$.name', 'startswith', 'Jo'],
                ['jsonpath', '$.name', 'endswith', 'hn'],
                ['jsonpath', '$.name', 'not_contains', 'xyz']
            ]
        }

        http_req = HTTPRequest(config)
        http_req.response = self.mock_response
        results, failed = http_req.process_asserts()

        assert len(results) == 4
        assert all(result['result'] for result in results)
        assert len(failed) == 0

    def test_existence_assertions(self):
        """测试存在性断言"""
        config = {
            'asserts': [
                ['jsonpath', '$.id', 'exists'],
                ['jsonpath', '$.missing_field', 'not_exists'],
                ['header', 'Content-Type', 'exists']
            ]
        }

        http_req = HTTPRequest(config)
        http_req.response = self.mock_response
        results, failed = http_req.process_asserts()

        assert len(results) == 3
        assert all(result['result'] for result in results)
        assert len(failed) == 0

    def test_type_assertions(self):
        """测试类型断言"""
        config = {
            'asserts': [
                ['jsonpath', '$.id', 'type', 'number'],
                ['jsonpath', '$.name', 'type', 'string'],
                ['jsonpath', '$.active', 'type', 'boolean'],
                ['jsonpath', '$.items', 'type', 'array']
            ]
        }

        http_req = HTTPRequest(config)
        http_req.response = self.mock_response
        results, failed = http_req.process_asserts()

        assert len(results) == 4
        assert all(result['result'] for result in results)
        assert len(failed) == 0

    def test_length_assertions(self):
        """测试长度断言"""
        config = {
            'asserts': [
                ['jsonpath', '$.items', 'length', 3],
                ['jsonpath', '$.name', 'length', 4],
                ['body', 'length', 'gt', 50]  # 这个应该通过，因为JSON字符串长度大于50
            ]
        }

        http_req = HTTPRequest(config)
        http_req.response = self.mock_response
        results, failed = http_req.process_asserts()

        assert len(results) == 3
        assert all(result['result'] for result in results)
        assert len(failed) == 0

    def test_in_assertions(self):
        """测试in断言"""
        config = {
            'asserts': [
                ['status', 'in', [200, 201, 204]],
                ['jsonpath', '$.id', 'not_in', [1, 2, 3]]
            ]
        }

        http_req = HTTPRequest(config)
        http_req.response = self.mock_response
        results, failed = http_req.process_asserts()

        assert len(results) == 2
        assert all(result['result'] for result in results)
        assert len(failed) == 0

    def test_schema_assertion(self):
        """测试Schema断言"""
        schema = {
            "type": "object",
            "properties": {
                "id": {"type": "number"},
                "name": {"type": "string"},
                "active": {"type": "boolean"}
            },
            "required": ["id", "name"]
        }

        config = {
            'asserts': [
                ['body', 'schema', schema]
            ]
        }

        http_req = HTTPRequest(config)
        http_req.response = self.mock_response

        with patch('jsonschema.validate') as mock_validate:
            mock_validate.return_value = None  # 验证成功
            results, failed = http_req.process_asserts()

            assert len(results) == 1
            assert results[0]['result'] == True
            assert len(failed) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
