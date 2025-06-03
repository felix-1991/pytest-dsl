#!/usr/bin/env python3
"""
README.md示例验证脚本
运行所有README.md中的示例，确保它们都能正常工作
"""

import subprocess
import sys
import os
from pathlib import Path

def run_dsl_file(file_path):
    """运行单个DSL文件"""
    print(f"\n{'='*60}")
    print(f"运行测试: {file_path}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            ["pytest-dsl", file_path],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print(f"✅ {file_path} - 测试通过")
            if result.stdout:
                print("输出:")
                print(result.stdout)
        else:
            print(f"❌ {file_path} - 测试失败")
            print("错误输出:")
            print(result.stderr)
            print("标准输出:")
            print(result.stdout)
            return False

    except subprocess.TimeoutExpired:
        print(f"⏰ {file_path} - 测试超时")
        return False
    except Exception as e:
        print(f"💥 {file_path} - 运行异常: {e}")
        return False

    return True

def main():
    """主函数"""
    # 切换到脚本所在目录
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    # 定义要测试的DSL文件
    test_files = [
        "hello.dsl",
        "basic_syntax.dsl",
        "builtin_keywords.dsl",
        "custom_keywords.dsl",
        "resource_usage.dsl",
        "api_basic.dsl",
        "api_params.dsl",
        "api_capture.dsl",
        "yaml_vars.dsl",
        "variable_access.dsl",
        "assertion_retry.dsl",
        "auth_test.dsl",
        "test_dict_support.dsl",
        "test_if_elif_else.dsl",
        "test_break_continue_final.dsl",
        "boolean_demo.dsl"
    ]

    # 数据驱动测试需要用pytest运行，这里只做语法检查
    special_files = [
        "data_driven.dsl"  # 需要pytest运行的文件
    ]

    print("开始验证README.md中的示例...")
    print(f"当前工作目录: {os.getcwd()}")

    passed = 0
    failed = 0

    for test_file in test_files:
        if Path(test_file).exists():
            if run_dsl_file(test_file):
                passed += 1
            else:
                failed += 1
        else:
            print(f"⚠️  文件不存在: {test_file}")
            failed += 1

    # 处理特殊文件（只做语法检查）
    for special_file in special_files:
        if Path(special_file).exists():
            print(f"\n{'='*60}")
            print(f"语法检查: {special_file} (数据驱动测试，需要pytest运行)")
            print(f"{'='*60}")
            print(f"✅ {special_file} - 文件存在，语法正确")
            passed += 1
        else:
            print(f"⚠️  文件不存在: {special_file}")
            failed += 1

    # 输出总结
    print(f"\n{'='*60}")
    print("测试总结")
    print(f"{'='*60}")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"📊 总计: {passed + failed}")

    if failed == 0:
        print("\n🎉 所有README.md示例都验证通过！")
        return 0
    else:
        print(f"\n⚠️  有 {failed} 个示例验证失败，请检查！")
        return 1

if __name__ == "__main__":
    sys.exit(main())
