#!/usr/bin/env python3
"""
远程兼容关键字测试脚本

这个脚本用于测试远程兼容关键字的功能，包括：
1. 本地执行测试
2. 序列化兼容性测试
3. 错误处理测试
"""

import json
import tempfile
import pytest
from pathlib import Path

# 导入远程兼容关键字
from pytest_dsl.keywords.custom.remote_compatible_examples import (
    remote_compatible_file_operation,
    remote_compatible_data_processing,
    remote_compatible_http_request
)


class TestRemoteCompatibleKeywords:
    """远程兼容关键字测试类"""
    
    def test_file_operation_write_read(self):
        """测试文件写入和读取操作"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_content = "测试文件内容"
            
            # 测试写入
            write_result = remote_compatible_file_operation(
                operation="write",
                file_path=str(test_file),
                content=test_content
            )
            
            assert write_result['success'] is True
            assert write_result['size'] == len(test_content)
            assert test_file.exists()
            
            # 测试读取
            read_result = remote_compatible_file_operation(
                operation="read",
                file_path=str(test_file)
            )
            
            assert read_result['success'] is True
            assert read_result['content'] == test_content
            assert read_result['size'] == len(test_content)
    
    def test_file_operation_exists_delete(self):
        """测试文件存在检查和删除操作"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("测试内容")
            
            # 测试存在检查
            exists_result = remote_compatible_file_operation(
                operation="exists",
                file_path=str(test_file)
            )
            
            assert exists_result['success'] is True
            assert exists_result['exists'] is True
            assert exists_result['is_file'] is True
            
            # 测试删除
            delete_result = remote_compatible_file_operation(
                operation="delete",
                file_path=str(test_file)
            )
            
            assert delete_result['success'] is True
            assert not test_file.exists()
    
    def test_file_operation_error_handling(self):
        """测试文件操作的错误处理"""
        # 测试读取不存在的文件
        read_result = remote_compatible_file_operation(
            operation="read",
            file_path="/不存在的路径/不存在的文件.txt"
        )
        
        assert read_result['success'] is False
        assert "文件不存在" in read_result['error']
        
        # 测试不支持的操作
        invalid_result = remote_compatible_file_operation(
            operation="invalid_operation",
            file_path="test.txt"
        )
        
        assert invalid_result['success'] is False
        assert "不支持的操作类型" in invalid_result['error']
    
    def test_data_processing_format(self):
        """测试数据格式化处理"""
        test_data = "Hello World"
        
        result = remote_compatible_data_processing(
            data=test_data,
            process_type="format",
            process_params={"template": "处理后: {data}"}
        )
        
        assert result['success'] is True
        assert result['formatted_data'] == "处理后: Hello World"
        assert result['original_data'] == test_data
    
    def test_data_processing_validate(self):
        """测试数据验证处理"""
        test_data = "test_string"
        validation_rules = {
            "rules": {
                "not_empty": {},
                "type_check": {"type": "str"},
                "length_check": {"min": 5, "max": 20}
            }
        }
        
        result = remote_compatible_data_processing(
            data=test_data,
            process_type="validate",
            process_params=validation_rules
        )
        
        assert result['success'] is True
        assert result['validation_passed'] is True
        assert all(result['validation_results'].values())
    
    def test_data_processing_transform(self):
        """测试数据转换处理"""
        test_data = "Hello World"
        
        # 测试转换为大写
        upper_result = remote_compatible_data_processing(
            data=test_data,
            process_type="transform",
            process_params={"type": "upper"}
        )
        
        assert upper_result['success'] is True
        assert upper_result['transformed_data'] == "HELLO WORLD"
        
        # 测试转换为小写
        lower_result = remote_compatible_data_processing(
            data=test_data,
            process_type="transform",
            process_params={"type": "lower"}
        )
        
        assert lower_result['success'] is True
        assert lower_result['transformed_data'] == "hello world"
    
    def test_data_processing_debug_mode(self):
        """测试数据处理的调试模式"""
        result = remote_compatible_data_processing(
            data="debug_test",
            process_type="format",
            process_params={"template": "Debug: {data}"},
            debug_mode=True
        )
        
        assert result['success'] is True
        assert 'debug_info' in result
        assert result['debug_info']['process_type'] == "format"
    
    def test_serialization_compatibility(self):
        """测试序列化兼容性"""
        # 测试所有关键字的返回值都可以序列化
        
        # 文件操作结果
        file_result = remote_compatible_file_operation(
            operation="exists",
            file_path="test.txt"
        )
        
        # 数据处理结果
        data_result = remote_compatible_data_processing(
            data="test",
            process_type="format",
            process_params={"template": "{data}"}
        )
        
        # 测试序列化
        try:
            json.dumps(file_result)
            json.dumps(data_result)
        except (TypeError, ValueError) as e:
            pytest.fail(f"序列化失败: {e}")
    
    def test_http_request_mock(self):
        """测试HTTP请求（模拟测试，不依赖外部网络）"""
        # 这里只测试参数处理和错误处理逻辑
        # 实际的HTTP请求需要在集成测试中进行
        
        # 测试无效URL的错误处理
        result = remote_compatible_http_request(
            url="http://不存在的域名.invalid",
            timeout=1
        )
        
        # 应该返回错误结果
        assert result['success'] is False
        assert 'error' in result
        assert result['url'] == "http://不存在的域名.invalid"


def run_local_tests():
    """运行本地测试"""
    print("开始运行远程兼容关键字本地测试...")
    
    # 创建测试实例
    test_instance = TestRemoteCompatibleKeywords()
    
    # 运行所有测试方法
    test_methods = [
        test_instance.test_file_operation_write_read,
        test_instance.test_file_operation_exists_delete,
        test_instance.test_file_operation_error_handling,
        test_instance.test_data_processing_format,
        test_instance.test_data_processing_validate,
        test_instance.test_data_processing_transform,
        test_instance.test_data_processing_debug_mode,
        test_instance.test_serialization_compatibility,
        test_instance.test_http_request_mock
    ]
    
    passed = 0
    failed = 0
    
    for test_method in test_methods:
        try:
            test_method()
            print(f"✅ {test_method.__name__} - 通过")
            passed += 1
        except Exception as e:
            print(f"❌ {test_method.__name__} - 失败: {e}")
            failed += 1
    
    print(f"\n测试结果: {passed} 通过, {failed} 失败")
    return failed == 0


if __name__ == "__main__":
    success = run_local_tests()
    exit(0 if success else 1)
