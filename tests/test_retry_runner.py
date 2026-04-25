#!/usr/bin/env python3
"""
重试功能测试运行器

用于验证重试功能是否正常工作
"""

import subprocess
import time

try:
    from .test_mock_server import MockServer
except ImportError:
    from test_mock_server import MockServer


def run_dsl_test(dsl_file):
    """运行DSL测试文件"""
    try:
        result = subprocess.run([
            'pytest-dsl',
            '--yaml-vars', 'mock_config.yaml',
            dsl_file
        ], capture_output=True, text=True, timeout=60)
        
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "测试超时"


def main():
    """主函数"""
    # 启动mock服务器
    server = MockServer()
    server.start()
    
    try:
        # 等待服务器启动
        time.sleep(1)
        
        # 运行重试功能测试
        print("🧪 运行重试功能综合测试...")
        success, stdout, stderr = run_dsl_test('test_retry_functionality.dsl')
        
        if success:
            print("✅ 重试功能测试通过！")
        else:
            print("❌ 重试功能测试失败！")
            if stdout:
                print("标准输出:")
                print(stdout)
            if stderr:
                print("标准错误:")
                print(stderr)
    
    finally:
        # 停止服务器
        server.stop()


if __name__ == "__main__":
    main()
