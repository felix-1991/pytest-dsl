"""
简化版测试平台Hook集成演示

这是一个精简版的Hook集成示例，专注展示核心功能：
1. 变量Hook - 动态提供环境变量
2. 案例Hook - 从数据库加载DSL内容
3. 关键字Hook - 注册自定义关键字

运行方式：
python tests/test_simple_hook_demo.py
"""

import os
import json
import tempfile
import sqlite3
from typing import Dict, List, Optional, Any
from pytest_dsl.core.hookspecs import hookimpl
from pytest_dsl.core.hook_manager import hook_manager
from pytest_dsl.core.dsl_executor import DSLExecutor
from pytest_dsl.core.yaml_vars import yaml_vars


class SimpleTestPlatform:
    """简化的测试平台Hook插件"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or ":memory:"
        self._init_database()
        self._init_data()
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 简化的表结构
        cursor.execute('''
            CREATE TABLE test_cases (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                dsl_content TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE variables (
                name TEXT,
                value TEXT,
                environment TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _init_data(self):
        """初始化测试数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 添加环境变量
        variables = [
            ('api_url', 'https://api-dev.example.com', 'dev'),
            ('api_url', 'https://api-test.example.com', 'test'),
            ('timeout', '30', 'dev'),
            ('timeout', '60', 'test'),
            ('debug', 'true', 'dev'),
            ('debug', 'false', 'test'),
        ]
        
        for name, value, env in variables:
            cursor.execute(
                "INSERT INTO variables (name, value, environment) VALUES (?, ?, ?)",
                (name, value, env)
            )
        
        # 添加简单的测试案例
        test_cases = [
            ('简单测试', '''
@name: "简单变量测试"

[打印], 内容: "当前环境API: ${api_url}"
[打印], 内容: "超时时间: ${timeout}秒"
[打印], 内容: "调试模式: ${debug}"
[打印], 内容: "变量Hook测试完成"
            '''),
            
            ('基础功能测试', '''
@name: "基础功能测试"

# 定义一些变量
测试数据 = "Hello World"
计数 = 5

[打印], 内容: "测试数据: ${测试数据}"
[打印], 内容: "计数: ${计数}"

# 使用环境变量
[打印], 内容: "API地址: ${api_url}"

# 简单的条件判断
if ${计数} > 3 do
    [打印], 内容: "计数大于3"
else
    [打印], 内容: "计数不大于3"
end

[打印], 内容: "基础功能测试完成"
            ''')
        ]
        
        for name, content in test_cases:
            cursor.execute(
                "INSERT INTO test_cases (name, dsl_content) VALUES (?, ?)",
                (name, content)
            )
        
        conn.commit()
        conn.close()
    
    # === Hook实现 ===
    
    @hookimpl
    def dsl_load_content(self, dsl_id: str) -> Optional[str]:
        """从数据库加载DSL内容"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if dsl_id.isdigit():
                cursor.execute("SELECT dsl_content FROM test_cases WHERE id = ?", (int(dsl_id),))
            else:
                cursor.execute("SELECT dsl_content FROM test_cases WHERE name = ?", (dsl_id,))
            
            row = cursor.fetchone()
            if row:
                print(f"📋 从测试平台加载案例: {dsl_id}")
                return row[0]
            
            return None
        finally:
            conn.close()
    
    @hookimpl
    def dsl_get_variable(self, var_name: str) -> Optional[Any]:
        """获取环境变量"""
        environment = os.environ.get('PYTEST_DSL_ENVIRONMENT', 'dev')
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT value FROM variables WHERE name = ? AND environment = ?",
                (var_name, environment)
            )
            
            row = cursor.fetchone()
            if row:
                value = row[0]
                
                # 类型转换
                if value.lower() in ('true', 'false'):
                    result = value.lower() == 'true'
                elif value.isdigit():
                    result = int(value)
                else:
                    result = value
                
                print(f"🔍 提供变量: {var_name} = {result} (环境: {environment})")
                return result
            
            return None
        finally:
            conn.close()
    
    @hookimpl
    def dsl_list_cases(self, project_id: Optional[int] = None, 
                       filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """列出测试案例"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT id, name FROM test_cases")
            rows = cursor.fetchall()
            
            cases = []
            for row in rows:
                cases.append({
                    'id': str(row[0]),
                    'name': row[1]
                })
            
            print(f"📋 找到 {len(cases)} 个测试案例")
            return cases
        finally:
            conn.close()
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT COUNT(*) FROM test_cases")
            case_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM variables")
            var_count = cursor.fetchone()[0]
            
            return {
                'test_cases': case_count,
                'variables': var_count,
                'database': self.db_path
            }
        finally:
            conn.close()


def test_variable_hooks():
    """测试变量Hook功能"""
    print("\n=== 测试变量Hook功能 ===")
    
    # 创建平台实例
    platform = SimpleTestPlatform()
    
    # 注册插件
    hook_manager.register_plugin(platform, "simple_platform")
    hook_manager.initialize()
    
    # 启用变量Hook
    yaml_vars.set_enable_hooks(True)
    
    try:
        # 测试不同环境
        for env in ['dev', 'test']:
            print(f"\n--- 测试环境: {env} ---")
            os.environ['PYTEST_DSL_ENVIRONMENT'] = env
            
            # 获取变量
            api_url = yaml_vars.get_variable('api_url')
            timeout = yaml_vars.get_variable('timeout')
            debug = yaml_vars.get_variable('debug')
            
            print(f"API地址: {api_url}")
            print(f"超时时间: {timeout}")
            print(f"调试模式: {debug}")
            
            assert api_url is not None
            assert timeout is not None
            assert debug is not None
    
    finally:
        # 清理
        if hasattr(hook_manager, 'pm') and hook_manager.pm:
            hook_manager.pm.unregister(platform, "simple_platform")
        
        if 'PYTEST_DSL_ENVIRONMENT' in os.environ:
            del os.environ['PYTEST_DSL_ENVIRONMENT']
    
    print("✅ 变量Hook测试完成")


def test_case_loading():
    """测试案例加载功能"""
    print("\n=== 测试案例加载功能 ===")
    
    platform = SimpleTestPlatform()
    
    # 注册插件
    hook_manager.register_plugin(platform, "simple_platform")
    hook_manager.initialize()
    yaml_vars.set_enable_hooks(True)
    
    try:
        # 列出案例
        cases_results = hook_manager.pm.hook.dsl_list_cases()
        cases = []
        for result in cases_results:
            if result:
                cases.extend(result)
        
        print(f"发现 {len(cases)} 个案例:")
        for case in cases:
            print(f"  - {case['id']}: {case['name']}")
        
        # 执行案例
        os.environ['PYTEST_DSL_ENVIRONMENT'] = 'dev'
        executor = DSLExecutor(enable_hooks=True)
        
        for case in cases[:1]:  # 只执行第一个案例
            case_id = case['id']
            print(f"\n--- 执行案例: {case['name']} ---")
            
            try:
                result = executor.execute_from_content(
                    content="",  # 空内容，通过Hook加载
                    dsl_id=case_id
                )
                print(f"✅ 案例执行成功")
            except Exception as e:
                print(f"⚠️ 案例执行警告: {e}")
    
    finally:
        # 清理
        if hasattr(hook_manager, 'pm') and hook_manager.pm:
            hook_manager.pm.unregister(platform, "simple_platform")
        
        if 'PYTEST_DSL_ENVIRONMENT' in os.environ:
            del os.environ['PYTEST_DSL_ENVIRONMENT']
    
    print("✅ 案例加载测试完成")


def test_platform_statistics():
    """测试平台统计功能"""
    print("\n=== 测试平台统计功能 ===")
    
    platform = SimpleTestPlatform()
    stats = platform.get_statistics()
    
    print(f"统计信息: {stats}")
    
    assert stats['test_cases'] > 0
    assert stats['variables'] > 0
    
    print("✅ 统计功能测试完成")


def main():
    """主演示函数"""
    print("🎯 简化版测试平台Hook集成演示")
    print("=" * 50)
    
    try:
        # 1. 平台统计
        test_platform_statistics()
        
        # 2. 变量Hook测试
        test_variable_hooks()
        
        # 3. 案例加载测试
        test_case_loading()
        
        print("\n" + "=" * 50)
        print("🎉 演示完成！所有功能正常运行")
        
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 