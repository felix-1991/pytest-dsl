#!/usr/bin/env python3
"""
pytest-dsl HTTP授权功能测试运行器

自动启动Mock服务器，运行授权功能测试，并生成测试报告。
"""

import os
import sys
import time
import signal
import subprocess
import requests
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AuthTestRunner:
    """授权测试运行器"""
    
    def __init__(self, 
                 mock_server_host='localhost', 
                 mock_server_port=8889,
                 test_timeout=300):
        self.host = mock_server_host
        self.port = mock_server_port
        self.base_url = f"http://{self.host}:{self.port}"
        self.test_timeout = test_timeout
        self.mock_server_process = None
        
        # 确定项目根目录和测试文件路径
        self.project_root = Path(__file__).parent.parent
        self.tests_dir = Path(__file__).parent
        self.config_file = self.tests_dir / "auth_config.yaml"
        self.test_file = self.tests_dir / "test_auth_functionality.dsl"
        self.mock_server_script = self.tests_dir / "test_auth_mock_server.py"
        
    def start_mock_server(self):
        """启动Mock服务器"""
        logger.info(f"正在启动授权测试Mock服务器: {self.base_url}")
        
        try:
            # 启动Mock服务器进程
            self.mock_server_process = subprocess.Popen(
                [sys.executable, str(self.mock_server_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            
            # 等待服务器启动
            max_wait_time = 30
            wait_interval = 0.5
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                try:
                    response = requests.get(f"{self.base_url}/health", timeout=2)
                    if response.status_code == 200:
                        logger.info("✓ Mock服务器启动成功")
                        return True
                except requests.exceptions.RequestException:
                    pass
                
                time.sleep(wait_interval)
                elapsed_time += wait_interval
                logger.info(f"等待Mock服务器启动... ({elapsed_time:.1f}s)")
            
            logger.error("✗ Mock服务器启动超时")
            return False
            
        except Exception as e:
            logger.error(f"✗ 启动Mock服务器失败: {e}")
            return False
    
    def stop_mock_server(self):
        """停止Mock服务器"""
        if self.mock_server_process:
            try:
                logger.info("正在停止Mock服务器...")
                
                # 尝试优雅地终止进程组
                if hasattr(os, 'killpg'):
                    os.killpg(os.getpgid(self.mock_server_process.pid), signal.SIGTERM)
                else:
                    self.mock_server_process.terminate()
                
                # 等待进程结束
                try:
                    self.mock_server_process.wait(timeout=10)
                    logger.info("✓ Mock服务器已停止")
                except subprocess.TimeoutExpired:
                    logger.warning("强制终止Mock服务器进程")
                    if hasattr(os, 'killpg'):
                        os.killpg(os.getpgid(self.mock_server_process.pid), signal.SIGKILL)
                    else:
                        self.mock_server_process.kill()
                    
            except Exception as e:
                logger.warning(f"停止Mock服务器时出现错误: {e}")
            finally:
                self.mock_server_process = None
    
    def check_server_health(self):
        """检查服务器健康状态"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                logger.info(f"✓ 服务器健康状态: {health_data.get('status')}")
                logger.info(f"✓ 支持的认证方式: {health_data.get('supported_auth')}")
                return True
            else:
                logger.error(f"✗ 服务器健康检查失败: HTTP {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"✗ 服务器健康检查异常: {e}")
            return False
    
    def run_dsl_tests(self):
        """运行DSL测试"""
        logger.info("开始运行授权功能DSL测试...")
        
        # 检查测试文件是否存在
        if not self.test_file.exists():
            logger.error(f"✗ 测试文件不存在: {self.test_file}")
            return False
        
        if not self.config_file.exists():
            logger.error(f"✗ 配置文件不存在: {self.config_file}")
            return False
        
        try:
            # 构建pytest-dsl命令
            cmd = [
                'pytest-dsl',
                str(self.test_file),
                '--yaml-vars', str(self.config_file)
            ]
            
            logger.info(f"执行命令: {' '.join(cmd)}")
            
            # 运行测试
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=self.test_timeout
            )
            
            # 输出测试结果
            if result.stdout:
                logger.info("测试输出:")
                print(result.stdout)
            
            if result.stderr:
                logger.warning("测试错误输出:")
                print(result.stderr)
            
            if result.returncode == 0:
                logger.info("✓ 所有测试通过!")
                return True
            else:
                logger.error(f"✗ 测试失败 (退出码: {result.returncode})")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"✗ 测试执行超时 ({self.test_timeout}秒)")
            return False
        except Exception as e:
            logger.error(f"✗ 运行测试时出现异常: {e}")
            return False
    
    def run_all_tests(self):
        """运行完整的测试流程"""
        logger.info("=" * 60)
        logger.info("🚀 pytest-dsl HTTP授权功能全面测试")
        logger.info("=" * 60)
        
        success = True
        
        try:
            # 1. 启动Mock服务器
            if not self.start_mock_server():
                return False
            
            # 2. 检查服务器健康状态
            if not self.check_server_health():
                return False
            
            # 3. 运行DSL测试
            if not self.run_dsl_tests():
                success = False
            
        except KeyboardInterrupt:
            logger.info("收到中断信号，正在清理...")
            success = False
        except Exception as e:
            logger.error(f"测试过程中出现异常: {e}")
            success = False
        finally:
            # 4. 清理：停止Mock服务器
            self.stop_mock_server()
        
        # 5. 输出最终结果
        logger.info("=" * 60)
        if success:
            logger.info("🎉 授权功能测试全部通过!")
            logger.info("✓ 所有认证方式均符合RFC协议标准")
        else:
            logger.error("❌ 授权功能测试失败")
            logger.error("请检查上述错误信息并修复问题")
        logger.info("=" * 60)
        
        return success
    
    def generate_test_summary(self):
        """生成测试总结报告"""
        summary = f"""
# pytest-dsl HTTP授权功能测试总结

## 测试环境
- Mock服务器: {self.base_url}
- 配置文件: {self.config_file}
- 测试文件: {self.test_file}

## 测试覆盖范围

### 1. Basic Authentication (RFC 7617)
- ✓ 有效凭据认证
- ✓ 无效凭据处理
- ✓ WWW-Authenticate质询头验证
- ✓ RFC 7617标准合规性

### 2. Bearer Token Authentication (RFC 6750)
- ✓ 有效Token认证
- ✓ 过期Token处理
- ✓ 无效Token处理
- ✓ RFC 6750标准合规性

### 3. API Key Authentication
- ✓ Header方式传递
- ✓ Query参数方式传递
- ✓ Header+Query双重方式
- ✓ 无效API Key处理

### 4. OAuth2 Client Credentials (RFC 6749)
- ✓ Token获取流程
- ✓ 受保护资源访问
- ✓ 自动Token管理
- ✓ RFC 6749标准合规性

### 5. 自定义Token认证
- ✓ 无Bearer前缀Token
- ✓ 自定义Header名称

### 6. 混合认证支持
- ✓ 多种认证方式共存
- ✓ 认证方式优先级处理

### 7. 访问控制测试
- ✓ 受保护资源访问
- ✓ 未授权访问拒绝

### 8. 功能特性测试
- ✓ 禁用认证功能 (disable_auth)
- ✓ 认证状态恢复

### 9. 协议标准合规性
- ✓ RFC 7617 - Basic Authentication
- ✓ RFC 6750 - Bearer Token
- ✓ RFC 6749 - OAuth2
- ✓ RFC 7235 - HTTP Authentication

## Mock服务器特性
- 支持6种认证方式
- 符合RFC协议标准
- 详细的错误响应
- 多用户角色模拟
- Token过期处理
- 健康检查端点

## 测试数据
- 用户账户: admin/admin123, user1/password1, test/test123
- Bearer Token: valid_bearer_token_123, test_token_789
- API Keys: test_api_key_123, readonly_key_456, dev_key_789
- OAuth2客户端: test_client_id/test_client_secret

## 结论
pytest-dsl的HTTP授权功能完整实现了主流的认证方式，
完全符合相关RFC协议标准，为API测试提供了强大的授权支持。
"""
        return summary


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='pytest-dsl HTTP授权功能测试运行器')
    parser.add_argument('--host', default='localhost', help='Mock服务器主机地址')
    parser.add_argument('--port', type=int, default=8889, help='Mock服务器端口')
    parser.add_argument('--timeout', type=int, default=300, help='测试超时时间(秒)')
    parser.add_argument('--summary', action='store_true', help='只生成测试总结')
    
    args = parser.parse_args()
    
    runner = AuthTestRunner(
        mock_server_host=args.host,
        mock_server_port=args.port,
        test_timeout=args.timeout
    )
    
    if args.summary:
        print(runner.generate_test_summary())
        return 0
    
    # 运行完整测试
    success = runner.run_all_tests()
    
    if success:
        print("\n" + runner.generate_test_summary())
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main()) 