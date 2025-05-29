"""测试无缝变量同步功能

验证客户端变量能够无缝传递到服务端，服务端使用变量时不需要添加前缀。
"""

import pytest
import tempfile
import os
import yaml
from pytest_dsl.remote.keyword_client import RemoteKeywordClient
from pytest_dsl.remote.keyword_server import RemoteKeywordServer
from pytest_dsl.remote.variable_bridge import variable_bridge
from pytest_dsl.core.yaml_vars import yaml_vars
from pytest_dsl.core.global_context import global_context


def test_seamless_variable_sync():
    """测试无缝变量同步功能"""
    print("\n🧪 测试无缝变量同步功能")
    
    try:
        # 1. 准备测试数据
        test_yaml_data = {
            'http_clients': {
                'default': {
                    'base_url': 'https://api.example.com',
                    'timeout': 30
                }
            },
            'test_data': {
                'username': 'testuser',
                'email': 'test@example.com'
            },
            'g_base_url': 'https://global.example.com',
            # 敏感信息应该被过滤
            'password': 'secret123',
            'api_key': 'sk-1234567890'
        }
        
        # 2. 创建临时YAML文件并加载
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_yaml_data, f, allow_unicode=True)
            yaml_file = f.name
        
        try:
            # 清理并加载YAML变量
            yaml_vars.clear()
            yaml_vars.load_yaml_file(yaml_file)
            print(f"✓ 加载YAML变量: {len(yaml_vars.get_all_variables())} 个")
            
            # 3. 设置全局变量
            global_context.set_variable('g_test_var', 'global_test_value')
            print("✓ 设置全局变量")
            
            # 4. 创建客户端并测试变量收集
            client = RemoteKeywordClient()
            
            # 测试全局变量收集
            global_vars = client._collect_global_variables()
            print(f"✓ 收集全局变量: {len(global_vars)} 个")
            assert 'g_test_var' in global_vars
            assert global_vars['g_test_var'] == 'global_test_value'
            
            # 测试YAML变量收集（关键测试：不应该有yaml_前缀）
            yaml_vars_collected = client._collect_yaml_variables()
            print(f"✓ 收集YAML变量: {len(yaml_vars_collected)} 个")
            
            # 验证变量名没有yaml_前缀
            assert 'http_clients' in yaml_vars_collected  # 不是yaml_http_clients
            assert 'test_data' in yaml_vars_collected     # 不是yaml_test_data
            assert 'g_base_url' in yaml_vars_collected    # 不是yaml_g_base_url
            
            # 验证敏感信息被过滤
            assert 'password' not in yaml_vars_collected
            assert 'api_key' not in yaml_vars_collected
            
            print("✓ 变量名无前缀，敏感信息已过滤")
            
            # 5. 创建服务器并测试变量桥接
            server = RemoteKeywordServer()
            
            # 模拟变量同步
            all_variables = {}
            all_variables.update(global_vars)
            all_variables.update(yaml_vars_collected)
            
            result = server.sync_variables_from_client(all_variables)
            assert result['status'] == 'success'
            print(f"✓ 服务器接收变量: {len(all_variables)} 个")
            
            # 6. 测试变量桥接机制
            # 安装变量桥接
            variable_bridge.install_bridge(server.shared_variables)
            print("✓ 安装变量桥接机制")
            
            # 测试通过yaml_vars访问同步的变量
            assert yaml_vars.get_variable('http_clients') is not None
            assert yaml_vars.get_variable('test_data') is not None
            assert yaml_vars.get_variable('g_base_url') == 'https://global.example.com'
            print("✓ 通过yaml_vars无缝访问同步变量")
            
            # 测试通过global_context访问同步的变量
            assert global_context.get_variable('g_test_var') == 'global_test_value'
            assert global_context.get_variable('http_clients') is not None
            print("✓ 通过global_context无缝访问同步变量")
            
            # 7. 测试优先级：本地变量优先于同步变量
            # 在本地设置一个与同步变量同名的变量
            yaml_vars._variables['test_priority'] = 'local_value'
            server.shared_variables['test_priority'] = 'synced_value'
            
            # 本地变量应该优先
            assert yaml_vars.get_variable('test_priority') == 'local_value'
            print("✓ 本地变量优先级正确")
            
            # 8. 测试变量桥接的回退机制
            # 访问只存在于同步变量中的变量
            server.shared_variables['only_synced'] = 'synced_only_value'
            assert yaml_vars.get_variable('only_synced') == 'synced_only_value'
            print("✓ 变量桥接回退机制正常")
            
            print("\n🎉 无缝变量同步功能测试通过！")
            return True
            
        finally:
            # 清理临时文件
            os.unlink(yaml_file)
            # 卸载变量桥接
            variable_bridge.uninstall_bridge()
            # 清理变量
            yaml_vars.clear()
            
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_variable_bridge_isolation():
    """测试变量桥接的隔离性"""
    print("\n🧪 测试变量桥接隔离性")
    
    try:
        # 1. 创建两个独立的服务器实例
        server1 = RemoteKeywordServer()
        server2 = RemoteKeywordServer()
        
        # 2. 为每个服务器设置不同的变量
        server1.shared_variables['server_id'] = 'server1'
        server1.shared_variables['common_var'] = 'value_from_server1'
        
        server2.shared_variables['server_id'] = 'server2'
        server2.shared_variables['common_var'] = 'value_from_server2'
        
        # 3. 测试桥接切换
        # 安装server1的桥接
        variable_bridge.install_bridge(server1.shared_variables)
        assert yaml_vars.get_variable('server_id') == 'server1'
        assert yaml_vars.get_variable('common_var') == 'value_from_server1'
        print("✓ Server1桥接正常")
        
        # 切换到server2的桥接
        variable_bridge.uninstall_bridge()
        variable_bridge.install_bridge(server2.shared_variables)
        assert yaml_vars.get_variable('server_id') == 'server2'
        assert yaml_vars.get_variable('common_var') == 'value_from_server2'
        print("✓ Server2桥接切换正常")
        
        # 4. 卸载桥接后应该无法访问同步变量
        variable_bridge.uninstall_bridge()
        assert yaml_vars.get_variable('server_id') is None
        assert yaml_vars.get_variable('common_var') is None
        print("✓ 桥接卸载后隔离正常")
        
        print("\n🎉 变量桥接隔离性测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        variable_bridge.uninstall_bridge()


if __name__ == "__main__":
    success1 = test_seamless_variable_sync()
    success2 = test_variable_bridge_isolation()
    
    if success1 and success2:
        print("\n🎉 所有测试通过！")
        exit(0)
    else:
        print("\n❌ 部分测试失败！")
        exit(1)
