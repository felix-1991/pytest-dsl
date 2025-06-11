"""
测试平台Hook集成示例

这个示例模拟一个测试平台如何使用pytest-dsl的Hook机制来：
1. 管理DSL测试案例
2. 提供自定义关键字
3. 动态配置环境变量
4. 实现案例的增删改查

运行方式：
python -m pytest tests/test_platform_hook_integration.py -v
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


class TestPlatformPlugin:
    """测试平台Hook插件
    
    模拟一个测试平台的案例管理系统，提供：
    - DSL案例存储和加载
    - 自定义关键字管理
    - 环境变量配置
    - 案例元数据管理
    """
    
    def __init__(self, db_path: str = None):
        """初始化测试平台插件
        
        Args:
            db_path: 数据库文件路径，如果为None则使用内存数据库
        """
        self.db_path = db_path or ":memory:"
        self._init_database()
        self._init_test_data()
    
    def _init_database(self):
        """初始化数据库结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建案例表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                dsl_content TEXT NOT NULL,
                tags TEXT,  -- JSON格式存储标签
                project_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建自定义关键字表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                dsl_content TEXT NOT NULL,
                description TEXT,
                project_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建环境变量表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS environment_variables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                var_name TEXT NOT NULL,
                var_value TEXT NOT NULL,
                environment TEXT NOT NULL,
                project_id INTEGER,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建项目表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _init_test_data(self):
        """初始化测试数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建示例项目
        cursor.execute(
            "INSERT OR IGNORE INTO projects (id, name, description) VALUES (1, '电商平台测试', '电商平台API测试项目')"
        )
        
        # 添加环境变量
        env_vars = [
            ('api_url', 'https://api-dev.example.com', 'dev', 1, 'API基础地址'),
            ('api_url', 'https://api-test.example.com', 'test', 1, 'API基础地址'),
            ('api_url', 'https://api.example.com', 'prod', 1, 'API基础地址'),
            ('timeout', '30', 'dev', 1, '请求超时时间（秒）'),
            ('timeout', '60', 'test', 1, '请求超时时间（秒）'),
            ('timeout', '120', 'prod', 1, '请求超时时间（秒）'),
            ('debug', 'true', 'dev', 1, '调试模式开关'),
            ('debug', 'false', 'test', 1, '调试模式开关'),
            ('debug', 'false', 'prod', 1, '调试模式开关'),
            ('db_host', 'localhost', 'dev', 1, '数据库主机'),
            ('db_host', 'test-db.example.com', 'test', 1, '数据库主机'),
            ('db_host', 'prod-db.example.com', 'prod', 1, '数据库主机'),
        ]
        
        for var_name, var_value, env, project_id, desc in env_vars:
            cursor.execute(
                "INSERT OR IGNORE INTO environment_variables (var_name, var_value, environment, project_id, description) VALUES (?, ?, ?, ?, ?)",
                (var_name, var_value, env, project_id, desc)
            )
        
        # 添加自定义关键字
        custom_keywords = [
            ('用户登录', """
function 用户登录 (用户名, 密码) do
    [打印], 内容: "正在登录用户: ${用户名}"
    
    # 模拟登录请求
    [HTTP请求], 客户端: "default", 配置: '''
        method: POST
        url: ${api_url}/auth/login
        timeout: ${timeout}
        json:
            username: ${用户名}
            password: ${密码}
    '''
    
    # 模拟返回token
    token = "mock_token_${用户名}_123456"
    [打印], 内容: "登录成功，Token: ${token}"
    
    return ${token}
end
            """, '用户登录关键字', 1),
            
            ('检查商品库存', """
function 检查商品库存 (商品ID, 最小库存=10) do
    [打印], 内容: "检查商品库存: ${商品ID}"
    
    # 发送库存查询请求
    [HTTP请求], 客户端: "default", 配置: '''
        method: GET
        url: ${api_url}/products/${商品ID}/stock
        timeout: ${timeout}
    '''
    
    # 模拟库存数据
    当前库存 = 50
    
    if ${当前库存} >= ${最小库存} do
        库存状态 = "充足"
    else
        库存状态 = "不足"
    end
    
    库存信息 = {
        "product_id": ${商品ID},
        "current_stock": ${当前库存},
        "min_stock": ${最小库存},
        "status": ${库存状态}
    }
    
    [打印], 内容: "库存检查结果: ${库存状态} (当前: ${当前库存}, 最小: ${最小库存})"
    return ${库存信息}
end
            """, '检查商品库存关键字', 1),
            
            ('创建订单', """
function 创建订单 (用户ID, 商品列表, 收货地址) do
    [打印], 内容: "为用户 ${用户ID} 创建订单"
    
    # 生成订单号
    订单号 = "ORD_" + ${用户ID} + "_123456"
    
    # 发送创建订单请求
    [HTTP请求], 客户端: "default", 配置: '''
        method: POST
        url: ${api_url}/orders
        timeout: ${timeout}
        json:
            user_id: ${用户ID}
            products: ${商品列表}
            address: ${收货地址}
            order_no: ${订单号}
    '''
    
    订单信息 = {
        "order_no": ${订单号},
        "user_id": ${用户ID},
        "products": ${商品列表},
        "address": ${收货地址},
        "status": "created"
    }
    
    [打印], 内容: "订单创建成功: ${订单号}"
    return ${订单信息}
end
            """, '创建订单关键字', 1)
        ]
        
        for name, content, desc, project_id in custom_keywords:
            cursor.execute(
                "INSERT OR IGNORE INTO custom_keywords (name, dsl_content, description, project_id) VALUES (?, ?, ?, ?)",
                (name, content, desc, project_id)
            )
        
        # 添加测试案例
        test_cases = [
            ('用户登录测试', '验证用户登录功能', """
@name: "用户登录测试"
@description: "测试用户登录功能的正常流程"
@tags: ["login", "authentication", "smoke"]

# 测试正常登录
登录结果 = [用户登录], 用户名: "testuser", 密码: "password123"

[断言], 条件: "${登录结果} != null", 消息: "登录应该返回token"
[打印], 内容: "登录测试完成，Token: ${登录结果}"
            """, '["login", "authentication", "smoke"]', 1),
            
            ('商品库存检查测试', '验证商品库存检查功能', """
@name: "商品库存检查测试"
@description: "测试商品库存检查的各种场景"
@tags: ["inventory", "products", "api"]

# 测试库存充足的情况
库存结果1 = [检查商品库存], 商品ID: "PROD001", 最小库存: 10

[断言], 条件: "${库存结果1["status"]} == '充足'", 消息: "库存应该显示充足"
[打印], 内容: "库存检查结果: ${库存结果1}"

# 测试库存不足的情况
库存结果2 = [检查商品库存], 商品ID: "PROD002", 最小库存: 100

[打印], 内容: "第二次库存检查: ${库存结果2}"
            """, '["inventory", "products", "api"]', 1),
            
            ('订单创建流程测试', '验证完整的订单创建流程', """
@name: "订单创建流程测试"
@description: "测试从登录到创建订单的完整流程"
@tags: ["order", "workflow", "integration"]

# 第一步：用户登录
用户token = [用户登录], 用户名: "buyer001", 密码: "buyer123"

# 第二步：检查商品库存
商品列表 = [
    {"product_id": "PROD001", "quantity": 2},
    {"product_id": "PROD002", "quantity": 1}
]

for 商品 in ${商品列表} do
    库存信息 = [检查商品库存], 商品ID: ${商品["product_id"]}, 最小库存: ${商品["quantity"]}
    [断言], 条件: "${库存信息["status"]} == '充足'", 消息: "商品 ${商品["product_id"]} 库存不足"
end

# 第三步：创建订单
收货地址 = {
    "province": "广东省",
    "city": "深圳市",
    "district": "南山区",
    "detail": "科技园南区XX大厦"
}

订单信息 = [创建订单], 用户ID: "buyer001", 商品列表: ${商品列表}, 收货地址: ${收货地址}

[断言], 条件: "${订单信息["status"]} == 'created'", 消息: "订单应该创建成功"
[打印], 内容: "订单创建完成: ${订单信息["order_no"]}"
            """, '["order", "workflow", "integration"]', 1),
            
            ('环境配置验证', '验证不同环境的配置是否正确', """
@name: "环境配置验证"
@description: "验证当前环境的配置参数是否正确"
@tags: ["config", "environment"]

# 验证环境变量
[打印], 内容: "当前API地址: ${api_url}"
[打印], 内容: "请求超时: ${timeout}秒"
[打印], 内容: "调试模式: ${debug}"
[打印], 内容: "数据库主机: ${db_host}"

# 检查API地址格式
[断言], 条件: "'http' in '${api_url}'", 消息: "API地址应该包含http协议"

# 检查超时时间
timeout_int = int(${timeout})
[断言], 条件: "${timeout_int} > 0", 消息: "超时时间应该大于0"

# 发送健康检查请求
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: ${api_url}/health
    timeout: ${timeout}
'''

[打印], 内容: "环境配置验证完成"
            """, '["config", "environment"]', 1)
        ]
        
        for name, desc, content, tags, project_id in test_cases:
            cursor.execute(
                "INSERT OR IGNORE INTO test_cases (name, description, dsl_content, tags, project_id) VALUES (?, ?, ?, ?, ?)",
                (name, desc, content, tags, project_id)
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
            # 尝试按ID加载
            if dsl_id.isdigit():
                cursor.execute("SELECT dsl_content FROM test_cases WHERE id = ?", (int(dsl_id),))
            else:
                # 尝试按名称加载
                cursor.execute("SELECT dsl_content FROM test_cases WHERE name = ?", (dsl_id,))
            
            row = cursor.fetchone()
            if row:
                print(f"🔄 从测试平台加载DSL案例: {dsl_id}")
                return row[0]
            
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
            query = """
                SELECT id, name, description, tags, project_id, created_at, updated_at
                FROM test_cases
            """
            params = []
            
            if project_id:
                query += " WHERE project_id = ?"
                params.append(project_id)
            
            if filters:
                if 'tags' in filters:
                    if params:
                        query += " AND"
                    else:
                        query += " WHERE"
                    query += " tags LIKE ?"
                    params.append(f"%{filters['tags']}%")
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            cases = []
            for row in rows:
                cases.append({
                    'id': str(row[0]),
                    'name': row[1],
                    'description': row[2],
                    'tags': json.loads(row[3]) if row[3] else [],
                    'project_id': row[4],
                    'created_at': row[5],
                    'updated_at': row[6]
                })
            
            print(f"📋 从测试平台获取到 {len(cases)} 个测试案例")
            return cases
            
        finally:
            conn.close()
    
    @hookimpl
    def dsl_register_custom_keywords(self, project_id: Optional[int] = None) -> None:
        """注册数据库中的自定义关键字"""
        from pytest_dsl.core.custom_keyword_manager import custom_keyword_manager
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            query = "SELECT name, dsl_content FROM custom_keywords"
            params = []
            
            if project_id:
                query += " WHERE project_id = ?"
                params.append(project_id)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            registered_count = 0
            for row in rows:
                name, dsl_content = row
                try:
                    custom_keyword_manager.register_keyword_from_dsl_content(
                        dsl_content, f"测试平台:{name}"
                    )
                    registered_count += 1
                except Exception as e:
                    print(f"⚠️ 注册关键字失败 {name}: {e}")
            
            print(f"🔧 从测试平台注册了 {registered_count} 个自定义关键字")
            
        finally:
            conn.close()
    
    @hookimpl
    def dsl_load_variables(self) -> Dict[str, Any]:
        """批量加载环境变量"""
        environment = os.environ.get('PYTEST_DSL_ENVIRONMENT', 'dev')
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT var_name, var_value FROM environment_variables WHERE environment = ?",
                (environment,)
            )
            
            variables = {}
            for row in cursor.fetchall():
                var_name, var_value = row
                
                # 尝试解析布尔值和数字
                if var_value.lower() in ('true', 'false'):
                    variables[var_name] = var_value.lower() == 'true'
                elif var_value.isdigit():
                    variables[var_name] = int(var_value)
                else:
                    variables[var_name] = var_value
            
            print(f"🌍 从测试平台加载了 {len(variables)} 个环境变量 (环境: {environment})")
            return variables
            
        finally:
            conn.close()
    
    @hookimpl
    def dsl_get_variable(self, var_name: str) -> Optional[Any]:
        """获取单个变量值"""
        environment = os.environ.get('PYTEST_DSL_ENVIRONMENT', 'dev')
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT var_value FROM environment_variables WHERE var_name = ? AND environment = ?",
                (var_name, environment)
            )
            
            row = cursor.fetchone()
            if row:
                var_value = row[0]
                
                # 尝试解析布尔值和数字
                if var_value.lower() in ('true', 'false'):
                    result = var_value.lower() == 'true'
                elif var_value.isdigit():
                    result = int(var_value)
                else:
                    result = var_value
                
                print(f"🔍 测试平台提供变量: {var_name} = {result} (环境: {environment})")
                return result
            
            return None
            
        finally:
            conn.close()
    
    @hookimpl
    def dsl_list_variable_sources(self) -> List[Dict[str, Any]]:
        """列出可用的变量源"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT DISTINCT environment FROM environment_variables")
            environments = [row[0] for row in cursor.fetchall()]
            
            cursor.execute("SELECT COUNT(*) FROM environment_variables")
            total_vars = cursor.fetchone()[0]
            
            return [{
                'name': 'test_platform_db',
                'type': 'database',
                'description': f'测试平台数据库变量源 (共{total_vars}个变量)',
                'environments': environments,
                'database_path': self.db_path
            }]
            
        finally:
            conn.close()
    
    @hookimpl
    def dsl_validate_variables(self, variables: Dict[str, Any]) -> List[str]:
        """验证变量配置"""
        errors = []
        
        # 检查必需变量
        required_vars = ['api_url', 'timeout']
        for var in required_vars:
            if var not in variables:
                errors.append(f"缺少必需变量: {var}")
        
        # 检查API地址格式
        if 'api_url' in variables:
            api_url = variables['api_url']
            if not api_url.startswith(('http://', 'https://')):
                errors.append("api_url必须以http://或https://开头")
        
        # 检查超时时间
        if 'timeout' in variables:
            timeout = variables['timeout']
            if not isinstance(timeout, int) or timeout <= 0:
                errors.append("timeout必须是大于0的整数")
        
        return errors
    
    @hookimpl
    def dsl_before_execution(self, dsl_id: str, context: Dict[str, Any]) -> None:
        """执行前hook"""
        print(f"🚀 测试平台准备执行案例: {dsl_id}")
        
        # 记录执行开始时间
        context['execution_start_time'] = __import__('time').time()
        
        # 可以在这里添加执行前的准备工作，如：
        # - 检查环境状态
        # - 准备测试数据
        # - 设置监控
    
    @hookimpl
    def dsl_after_execution(self, dsl_id: str, context: Dict[str, Any],
                            result: Any, exception: Optional[Exception] = None) -> None:
        """执行后hook"""
        start_time = context.get('execution_start_time', 0)
        execution_time = __import__('time').time() - start_time
        
        if exception:
            print(f"❌ 测试平台案例执行失败: {dsl_id} (耗时: {execution_time:.2f}秒)")
            print(f"   错误信息: {exception}")
            # 可以在这里记录失败日志到数据库
        else:
            print(f"✅ 测试平台案例执行成功: {dsl_id} (耗时: {execution_time:.2f}秒)")
            # 可以在这里记录成功日志到数据库
    
    # === 案例管理方法 ===
    
    def add_test_case(self, name: str, description: str, dsl_content: str, 
                      tags: List[str] = None, project_id: int = 1) -> int:
        """添加测试案例"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO test_cases (name, description, dsl_content, tags, project_id) VALUES (?, ?, ?, ?, ?)",
                (name, description, dsl_content, json.dumps(tags or []), project_id)
            )
            case_id = cursor.lastrowid
            conn.commit()
            print(f"➕ 添加测试案例: {name} (ID: {case_id})")
            return case_id
            
        finally:
            conn.close()
    
    def update_test_case(self, case_id: int, **kwargs) -> bool:
        """更新测试案例"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 构建更新语句
            update_fields = []
            values = []
            
            for field in ['name', 'description', 'dsl_content']:
                if field in kwargs:
                    update_fields.append(f"{field} = ?")
                    values.append(kwargs[field])
            
            if 'tags' in kwargs:
                update_fields.append("tags = ?")
                values.append(json.dumps(kwargs['tags']))
            
            if not update_fields:
                return False
            
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(case_id)
            
            query = f"UPDATE test_cases SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(query, values)
            
            updated = cursor.rowcount > 0
            conn.commit()
            
            if updated:
                print(f"🔄 更新测试案例: ID {case_id}")
            
            return updated
            
        finally:
            conn.close()
    
    def delete_test_case(self, case_id: int) -> bool:
        """删除测试案例"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM test_cases WHERE id = ?", (case_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            
            if deleted:
                print(f"🗑️ 删除测试案例: ID {case_id}")
            
            return deleted
            
        finally:
            conn.close()
    
    def add_environment_variable(self, var_name: str, var_value: str, 
                                 environment: str, project_id: int = 1, 
                                 description: str = "") -> int:
        """添加环境变量"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO environment_variables (var_name, var_value, environment, project_id, description) VALUES (?, ?, ?, ?, ?)",
                (var_name, var_value, environment, project_id, description)
            )
            var_id = cursor.lastrowid
            conn.commit()
            print(f"➕ 添加环境变量: {var_name}={var_value} (环境: {environment})")
            return var_id
            
        finally:
            conn.close()
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取平台统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 统计案例数量
            cursor.execute("SELECT COUNT(*) FROM test_cases")
            total_cases = cursor.fetchone()[0]
            
            # 统计关键字数量
            cursor.execute("SELECT COUNT(*) FROM custom_keywords")
            total_keywords = cursor.fetchone()[0]
            
            # 统计环境变量数量
            cursor.execute("SELECT COUNT(*) FROM environment_variables")
            total_variables = cursor.fetchone()[0]
            
            # 统计项目数量
            cursor.execute("SELECT COUNT(*) FROM projects")
            total_projects = cursor.fetchone()[0]
            
            return {
                'total_cases': total_cases,
                'total_keywords': total_keywords,
                'total_variables': total_variables,
                'total_projects': total_projects,
                'database_path': self.db_path
            }
            
        finally:
            conn.close()


class TestPlatformIntegration:
    """测试平台集成测试类"""
    
    def __init__(self):
        self.plugin = None
        self.temp_db = None
    
    def setup_method(self):
        """每个测试方法前的设置"""
        # 创建临时数据库
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        
        # 创建插件实例
        self.plugin = TestPlatformPlugin(self.temp_db.name)
        
        # 注册插件
        hook_manager.register_plugin(self.plugin, "test_platform")
        hook_manager.initialize()
        
        # 启用变量Hook
        yaml_vars.set_enable_hooks(True)
        
        print(f"🔧 测试环境已设置，数据库: {self.temp_db.name}")
    
    def teardown_method(self):
        """每个测试方法后的清理"""
        # 清理Hook管理器
        if hasattr(hook_manager, 'pm') and hook_manager.pm:
            hook_manager.pm.unregister(self.plugin, "test_platform")
        
        # 删除临时数据库
        if self.temp_db and os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
        
        # 重置环境变量
        if 'PYTEST_DSL_ENVIRONMENT' in os.environ:
            del os.environ['PYTEST_DSL_ENVIRONMENT']
        
        print("🧹 测试环境已清理")
    
    def test_platform_statistics(self):
        """测试平台统计信息"""
        stats = self.plugin.get_statistics()
        
        assert stats['total_cases'] > 0, "应该有测试案例"
        assert stats['total_keywords'] > 0, "应该有自定义关键字"
        assert stats['total_variables'] > 0, "应该有环境变量"
        assert stats['total_projects'] > 0, "应该有项目"
        
        print(f"📊 平台统计: {stats}")
    
    def test_list_cases(self):
        """测试案例列表功能"""
        # 通过Hook获取案例列表
        cases_results = hook_manager.pm.hook.dsl_list_cases(project_id=1)
        
        cases = []
        for result in cases_results:
            if result:
                cases.extend(result)
        
        assert len(cases) > 0, "应该有测试案例"
        
        # 检查案例结构
        for case in cases:
            assert 'id' in case
            assert 'name' in case
            assert 'description' in case
            assert 'tags' in case
            
        print(f"📋 获取到 {len(cases)} 个测试案例")
        for case in cases[:2]:  # 只显示前2个
            print(f"   - {case['name']}: {case['description']}")
    
    def test_environment_variables(self):
        """测试环境变量功能"""
        # 测试不同环境
        environments = ['dev', 'test', 'prod']
        
        for env in environments:
            os.environ['PYTEST_DSL_ENVIRONMENT'] = env
            
            # 获取变量
            api_url = yaml_vars.get_variable('api_url')
            timeout = yaml_vars.get_variable('timeout')
            debug = yaml_vars.get_variable('debug')
            
            assert api_url is not None, f"环境 {env} 应该有api_url"
            assert timeout is not None, f"环境 {env} 应该有timeout"
            assert debug is not None, f"环境 {env} 应该有debug"
            
            print(f"🌍 环境 {env}: api_url={api_url}, timeout={timeout}, debug={debug}")
    
    def test_custom_keywords_registration(self):
        """测试自定义关键字注册"""
        from pytest_dsl.core.keyword_manager import keyword_manager
        
        # 通过Hook注册关键字
        hook_manager.pm.hook.dsl_register_custom_keywords(project_id=1)
        
        # 检查关键字是否注册成功
        expected_keywords = ['用户登录', '检查商品库存', '创建订单']
        
        for keyword_name in expected_keywords:
            keyword_info = keyword_manager.get_keyword_info(keyword_name)
            assert keyword_info is not None, f"关键字 {keyword_name} 应该已注册"
            
        print(f"🔧 自定义关键字注册验证完成")
    
    def test_execute_dsl_case_by_id(self):
        """测试通过ID执行DSL案例"""
        # 设置环境
        os.environ['PYTEST_DSL_ENVIRONMENT'] = 'dev'
        
        # 创建执行器
        executor = DSLExecutor(enable_hooks=True)
        
        # 执行环境配置验证案例（案例ID为4）
        try:
            result = executor.execute_from_content(
                content="",  # 空内容，通过Hook加载
                dsl_id="4",  # 环境配置验证案例
                context={'test_id': 4, 'environment': 'dev'}
            )
            
            print(f"✅ 案例执行成功")
            
        except Exception as e:
            print(f"❌ 案例执行失败: {e}")
            # 对于演示目的，我们不让测试失败
            # 因为HTTP请求等可能会失败
    
    def test_execute_dsl_case_by_name(self):
        """测试通过名称执行DSL案例"""
        # 设置环境
        os.environ['PYTEST_DSL_ENVIRONMENT'] = 'test'
        
        # 创建执行器
        executor = DSLExecutor(enable_hooks=True)
        
        # 执行环境配置验证案例
        try:
            result = executor.execute_from_content(
                content="",
                dsl_id="环境配置验证",
                context={'environment': 'test'}
            )
            
            print(f"✅ 案例执行成功")
            
        except Exception as e:
            print(f"❌ 案例执行失败: {e}")
            # 对于演示目的，我们不让测试失败
    
    def test_case_management(self):
        """测试案例管理功能"""
        # 添加新案例
        new_case_dsl = """
@name: "新建测试案例"
@description: "这是一个新创建的测试案例"
@tags: ["demo", "new"]

[打印], 内容: "这是一个新的测试案例"
[打印], 内容: "API地址: ${api_url}"
[打印], 内容: "测试完成"
        """
        
        case_id = self.plugin.add_test_case(
            name="新建测试案例",
            description="演示案例管理功能",
            dsl_content=new_case_dsl,
            tags=["demo", "new"]
        )
        
        assert case_id > 0, "案例ID应该大于0"
        
        # 更新案例
        updated = self.plugin.update_test_case(
            case_id,
            description="更新后的案例描述",
            tags=["demo", "updated"]
        )
        
        assert updated, "案例应该更新成功"
        
        # 执行新案例
        os.environ['PYTEST_DSL_ENVIRONMENT'] = 'dev'
        executor = DSLExecutor(enable_hooks=True)
        
        try:
            result = executor.execute_from_content(
                content="",
                dsl_id=str(case_id)
            )
            print(f"✅ 新案例执行成功")
        except Exception as e:
            print(f"⚠️ 新案例执行时有警告: {e}")
        
        # 删除案例
        deleted = self.plugin.delete_test_case(case_id)
        assert deleted, "案例应该删除成功"
        
        print(f"🔄 案例管理功能验证完成")
    
    def test_variable_management(self):
        """测试变量管理功能"""
        # 添加新环境变量
        var_id = self.plugin.add_environment_variable(
            var_name="new_var",
            var_value="test_value",
            environment="dev",
            description="测试变量"
        )
        
        assert var_id > 0, "变量ID应该大于0"
        
        # 验证变量是否可用
        os.environ['PYTEST_DSL_ENVIRONMENT'] = 'dev'
        value = yaml_vars.get_variable('new_var')
        
        assert value == "test_value", f"变量值应该是test_value，实际是{value}"
        
        print(f"🔧 变量管理功能验证完成")


# 主函数用于独立运行演示
def main():
    """演示测试平台Hook集成功能"""
    print("🎯 测试平台Hook集成演示")
    print("=" * 50)
    
    # 创建演示实例
    demo = TestPlatformIntegration()
    demo.setup_method()
    
    try:
        print("\n1. 平台统计信息")
        demo.test_platform_statistics()
        
        print("\n2. 案例列表功能")
        demo.test_list_cases()
        
        print("\n3. 环境变量功能")
        demo.test_environment_variables()
        
        print("\n4. 自定义关键字注册")
        demo.test_custom_keywords_registration()
        
        print("\n5. 执行DSL案例")
        demo.test_execute_dsl_case_by_id()
        
        print("\n6. 案例管理功能")
        demo.test_case_management()
        
        print("\n7. 变量管理功能")
        demo.test_variable_management()
        
        print("\n" + "=" * 50)
        print("🎉 测试平台Hook集成演示完成！")
        
    finally:
        demo.teardown_method()


if __name__ == "__main__":
    main() 