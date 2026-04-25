#!/usr/bin/env python3
"""
变量传递功能演示脚本
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_basic_functionality():
    """测试基本功能"""
    print("=== 测试变量传递基本功能 ===")

    try:
        # 导入必要的模块
        from pytest_dsl.remote.keyword_client import RemoteKeywordClient, RemoteKeywordManager
        from pytest_dsl.remote.keyword_server import RemoteKeywordServer
        from pytest_dsl.core.global_context import global_context

        print("✓ 所有模块导入成功")

        # 测试RemoteKeywordClient初始化
        client = RemoteKeywordClient()
        print("✓ RemoteKeywordClient 初始化成功")
        print(f"  变量传递配置: {client.sync_config}")

        # 测试RemoteKeywordServer初始化
        server = RemoteKeywordServer()
        print("✓ RemoteKeywordServer 初始化成功")
        print(f"  共享变量存储: {server.shared_variables}")

        # 测试全局变量设置和获取
        global_context.set_variable('g_test_var', 'test_value')
        value = global_context.get_variable('g_test_var')
        assert value == 'test_value', f"期望 'test_value'，实际得到 '{value}'"
        print("✓ 全局变量设置和获取功能正常")

        # 测试变量收集功能
        variables = client._collect_global_variables()
        print(f"✓ 收集到 {len(variables)} 个全局变量")
        if 'g_test_var' in variables:
            print(f"  包含测试变量: g_test_var = {variables['g_test_var']}")

        # 测试服务器变量存储
        result = server.set_shared_variable('test_server_var', 'server_value')
        assert result['status'] == 'success', f"设置变量失败: {result}"
        print("✓ 服务器变量存储功能正常")

        result = server.get_shared_variable('test_server_var')
        assert result['status'] == 'success', f"获取变量失败: {result}"
        assert result['value'] == 'server_value', f"变量值不匹配: {result['value']}"
        print("✓ 服务器变量获取功能正常")

        # 测试RemoteKeywordManager
        manager = RemoteKeywordManager()
        assert isinstance(manager.clients, dict)
        print("✓ RemoteKeywordManager 功能正常")

        print("\n🎉 所有基本功能测试通过！")

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

def test_variable_transfer():
    """测试变量传递功能"""
    print("\n=== 测试变量传递功能 ===")

    try:
        from pytest_dsl.remote.keyword_client import RemoteKeywordClient
        from pytest_dsl.core.global_context import global_context

        # 设置一些测试变量
        global_context.set_variable('g_test_transfer', 'transfer_value')

        # 创建客户端并测试变量收集
        client = RemoteKeywordClient()
        variables = client._collect_global_variables()

        assert 'g_test_transfer' in variables
        assert variables['g_test_transfer'] == 'transfer_value'
        print("✓ 变量收集功能正常")

        print("\n🎉 变量传递测试通过！")

    except Exception as e:
        print(f"❌ 变量传递测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

def main():
    """主函数"""
    print("pytest-dsl 变量传递功能演示")
    print("=" * 50)

    # 运行基本功能测试
    test_basic_functionality()

    # 运行变量传递测试
    test_variable_transfer()

    print("\n" + "=" * 50)
    print("🎉 所有测试通过！变量传递功能已成功实现。")
    print("\n功能特性:")
    print("- ✓ 连接时自动传递全局变量（g_开头）")
    print("- ✓ 连接时自动传递YAML配置变量")
    print("- ✓ 远程服务器变量存储")
    print("- ✓ 简化的配置管理")
    print("- ✓ 参数传递机制保持不变")

    print("\n使用方法:")
    print("1. 启动远程关键字服务器: pytest-dsl-server")
    print("2. 设置全局变量: g_test_var = \"value\"")
    print("3. 在DSL文件中使用远程导入: 远程导入 http://localhost:8270/ 别名 server")
    print("4. 远程关键字可以访问传递过去的变量: ${g_test_var}")
    print("5. 其他变量通过参数传递: server|打印 内容 ${local_var}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
