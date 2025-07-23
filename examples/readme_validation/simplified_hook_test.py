#!/usr/bin/env python3
"""
简化的Hook机制测试

使用DSLExecutor原生的Hook支持进行测试
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pytest_dsl.core.hookspecs import hookimpl
from pytest_dsl.core.hook_manager import hook_manager
from pytest_dsl.core.dsl_executor import DSLExecutor


class SimplifiedTestPlugin:
    """简化的测试插件"""
    
    def __init__(self):
        self.call_log = []
        
    @hookimpl
    def dsl_register_custom_keywords(self, project_id=None):
        """注册自定义关键字"""
        self.call_log.append("dsl_register_custom_keywords")
        print("🔧 Hook调用: dsl_register_custom_keywords")
        
        # 注册一个测试关键字
        test_keyword_dsl = """function 简化测试关键字 (message="默认消息") do
    [打印], 内容: "简化Hook关键字: ${message}"
end"""
        
        try:
            # 通过DSLExecutor的hookable_keyword_manager注册
            from pytest_dsl.core.hookable_keyword_manager import hookable_keyword_manager
            hookable_keyword_manager.register_hook_keyword(
                "简化测试关键字", 
                test_keyword_dsl,
                {
                    'source_type': 'simplified_test',
                    'source_name': '简化测试插件',
                    'description': '简化Hook测试关键字'
                }
            )
            print("✅ 成功注册Hook关键字: 简化测试关键字")
        except Exception as e:
            print(f"❌ 注册Hook关键字失败: {e}")
        
    @hookimpl
    def dsl_load_content(self, dsl_id):
        """加载DSL内容"""
        self.call_log.append(f"dsl_load_content:{dsl_id}")
        print(f"📄 Hook调用: dsl_load_content({dsl_id})")
        
        if dsl_id == "simplified_test":
            content = """@name: "简化Hook测试"
@description: "使用DSLExecutor原生Hook支持的测试"

[打印], 内容: "开始简化测试"
[简化测试关键字], message: "Hello from Simplified Hook!"
[打印], 内容: "简化测试完成"
"""
            print(f"✅ 返回DSL内容: {dsl_id}")
            return content
        
        return None
        
    @hookimpl
    def dsl_before_execution(self, dsl_id, context):
        """执行前Hook"""
        self.call_log.append(f"dsl_before_execution:{dsl_id}")
        print(f"🚀 Hook调用: dsl_before_execution({dsl_id})")
        
    @hookimpl
    def dsl_after_execution(self, dsl_id, context, result, exception=None):
        """执行后Hook"""
        self.call_log.append(f"dsl_after_execution:{dsl_id}")
        print(f"🏁 Hook调用: dsl_after_execution({dsl_id})")
        if exception:
            print(f"   执行异常: {exception}")
        else:
            print(f"   执行成功")


def test_dsl_executor_native_hooks():
    """测试DSLExecutor原生Hook支持"""
    print("=" * 60)
    print("🧪 测试DSLExecutor原生Hook支持")
    print("=" * 60)
    
    # 1. 创建插件
    plugin = SimplifiedTestPlugin()
    
    # 2. 注册插件
    print("\n📝 注册插件...")
    hook_manager.register_plugin(plugin, name="simplified_test")
    
    # 3. 创建DSLExecutor（自动启用Hook）
    print("\n🔧 创建DSLExecutor...")
    executor = DSLExecutor(enable_hooks=True)
    
    print(f"   Hook启用: {executor.enable_hooks}")
    print(f"   Hook管理器: {hasattr(executor, 'hook_manager') and executor.hook_manager is not None}")
    
    # 4. 测试通过Hook加载和执行DSL
    print("\n🚀 测试Hook加载和执行...")
    try:
        result = executor.execute_from_content(
            content="",  # 空内容，通过Hook加载
            dsl_id="simplified_test"
        )
        print("✅ Hook DSL执行成功")
        success1 = True
    except Exception as e:
        print(f"❌ Hook DSL执行失败: {e}")
        success1 = False
    
    # 5. 测试直接执行包含Hook关键字的DSL
    print("\n🔧 测试直接执行Hook关键字...")
    direct_dsl = """@name: "直接测试"

[打印], 内容: "直接测试开始"
[简化测试关键字], message: "Direct Message"
[打印], 内容: "直接测试完成"
"""
    
    try:
        result = executor.execute_from_content(direct_dsl, "direct_test")
        print("✅ 直接DSL执行成功")
        success2 = True
    except Exception as e:
        print(f"❌ 直接DSL执行失败: {e}")
        success2 = False
    
    # 6. 检查插件调用日志
    print(f"\n📋 插件调用日志 (共{len(plugin.call_log)}次):")
    for i, call in enumerate(plugin.call_log, 1):
        print(f"   {i}. {call}")
    
    return success1 and success2


def test_dsl_executor_without_hooks():
    """测试DSLExecutor禁用Hook"""
    print("\n" + "=" * 60)
    print("🔧 测试DSLExecutor禁用Hook")
    print("=" * 60)
    
    executor = DSLExecutor(enable_hooks=False)
    print(f"   Hook启用: {executor.enable_hooks}")
    
    basic_dsl = """@name: "基本测试"

[打印], 内容: "基本功能测试"
"""
    
    try:
        result = executor.execute_from_content(basic_dsl, "basic_test")
        print("✅ 基本DSL执行成功（无Hook）")
        return True
    except Exception as e:
        print(f"❌ 基本DSL执行失败: {e}")
        return False


def test_multiple_executors():
    """测试多个执行器实例"""
    print("\n" + "=" * 60)
    print("🔄 测试多个执行器实例")
    print("=" * 60)
    
    # 创建多个执行器
    executor1 = DSLExecutor(enable_hooks=True)
    executor2 = DSLExecutor(enable_hooks=True)
    executor3 = DSLExecutor(enable_hooks=False)
    
    print(f"   执行器1 Hook: {executor1.enable_hooks}")
    print(f"   执行器2 Hook: {executor2.enable_hooks}")
    print(f"   执行器3 Hook: {executor3.enable_hooks}")
    
    # 测试它们是否都能正常工作
    test_dsl = """@name: "多实例测试"

[打印], 内容: "多实例测试"
"""
    
    success_count = 0
    
    for i, executor in enumerate([executor1, executor2, executor3], 1):
        try:
            result = executor.execute_from_content(test_dsl, f"multi_test_{i}")
            print(f"✅ 执行器{i}执行成功")
            success_count += 1
        except Exception as e:
            print(f"❌ 执行器{i}执行失败: {e}")
    
    return success_count == 3


def main():
    """主函数"""
    print("🚀 开始简化Hook机制测试")
    
    # 加载内置关键字
    print("\n🔧 加载内置关键字...")
    try:
        from pytest_dsl.core.keyword_loader import load_all_keywords
        load_all_keywords()
        print("✅ 内置关键字加载完成")
    except Exception as e:
        print(f"❌ 内置关键字加载失败: {e}")
    
    # 运行测试
    test_results = []
    
    test_results.append(("DSLExecutor原生Hook支持", test_dsl_executor_native_hooks()))
    test_results.append(("DSLExecutor禁用Hook", test_dsl_executor_without_hooks()))
    test_results.append(("多执行器实例", test_multiple_executors()))
    
    # 输出结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    # 结论
    print("\n" + "=" * 60)
    print("📋 测试结论")
    print("=" * 60)
    
    if passed == total:
        print("🎉 DSLExecutor原生Hook支持完全正常!")
        print("\n✅ 验证结果:")
        print("   - DSLExecutor原生支持Hook机制")
        print("   - Hook关键字注册和执行正常")
        print("   - 多实例支持良好")
        print("   - 禁用Hook模式正常")
        print("\n💡 结论: DSLExecutor是唯一需要的执行器!")
        return 0
    else:
        print("⚠️ 存在问题需要修复")
        return 1


if __name__ == "__main__":
    sys.exit(main())
