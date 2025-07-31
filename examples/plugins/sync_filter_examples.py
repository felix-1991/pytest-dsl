#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
变量同步过滤插件示例

展示如何通过Hook机制自定义远程关键字变量同步的过滤规则
"""

from pytest_dsl.core.hookspecs import hookimpl


class EnvironmentBasedSyncPlugin:
    """基于环境的同步过滤插件"""
    
    @hookimpl
    def dsl_filter_sync_variables(self, variables, sync_context):
        """根据服务器环境过滤变量"""
        server_alias = sync_context.get('server_alias', '')
        
        # 生产环境严格过滤
        if 'prod' in server_alias or 'production' in server_alias:
            # 只同步必要的配置变量
            essential_vars = [
                'g_environment', 'g_base_url', 'g_timeout',
                'api_version', 'api_key', 'config_'
            ]
            filtered = {}
            for k, v in variables.items():
                if any(k.startswith(prefix) for prefix in essential_vars):
                    filtered[k] = v
            
            print(f"生产环境过滤: {len(variables)} -> {len(filtered)} 个变量")
            return filtered
        
        # 开发环境排除生产配置
        elif 'dev' in server_alias or 'development' in server_alias:
            filtered = {k: v for k, v in variables.items() 
                       if not k.startswith(('prod_', 'production_'))}
            return filtered
            
        # 测试环境排除敏感数据
        elif 'test' in server_alias:
            filtered = {k: v for k, v in variables.items() 
                       if not any(sensitive in k.lower() 
                                for sensitive in ['password', 'secret', 'key', 'token'])}
            return filtered
        
        return None  # 其他环境不修改


class PerformanceOptimizedSyncPlugin:
    """性能优化的同步过滤插件"""
    
    @hookimpl
    def dsl_filter_sync_variables(self, variables, sync_context):
        """基于性能考虑过滤变量"""
        sync_type = sync_context.get('sync_type', '')
        
        # 实时同步时进行性能优化
        if sync_type == 'realtime':
            filtered = {}
            large_objects_count = 0
            
            for k, v in variables.items():
                # 过滤大对象
                if isinstance(v, (list, dict)):
                    size = len(str(v))
                    if size > 1000:  # 超过1KB的对象
                        large_objects_count += 1
                        continue
                
                # 过滤临时变量
                if k.startswith(('temp_', 'cache_', 'session_')):
                    continue
                    
                filtered[k] = v
            
            if large_objects_count > 0:
                print(f"实时同步过滤掉 {large_objects_count} 个大对象")
            
            return filtered
        
        # 初始同步时限制变量总数
        elif sync_type == 'initial' and len(variables) > 100:
            # 按重要性排序，只保留前100个
            important_prefixes = ['g_', 'api_', 'config_', 'http_']
            important_vars = {}
            other_vars = {}
            
            for k, v in variables.items():
                if any(k.startswith(prefix) for prefix in important_prefixes):
                    important_vars[k] = v
                else:
                    other_vars[k] = v
            
            # 重要变量全部保留，其他变量按需保留
            remaining_slots = 100 - len(important_vars)
            if remaining_slots > 0:
                other_items = list(other_vars.items())[:remaining_slots]
                important_vars.update(dict(other_items))
            
            print(f"初始同步限制变量数量: {len(variables)} -> {len(important_vars)}")
            return important_vars
        
        return None


class SecurityBasedSyncPlugin:
    """基于安全考虑的同步过滤插件"""
    
    @hookimpl
    def dsl_filter_sync_variables(self, variables, sync_context):
        """基于安全策略过滤变量"""
        server_alias = sync_context.get('server_alias', '')
        variable_source = sync_context.get('variable_source', '')
        
        # 外部服务器额外安全检查
        if 'external' in server_alias or 'third_party' in server_alias:
            # 只同步白名单变量
            whitelist = [
                'g_environment', 'g_base_url', 'api_version',
                'timeout', 'retry_count'
            ]
            filtered = {k: v for k, v in variables.items() if k in whitelist}
            print(f"外部服务器白名单过滤: {len(variables)} -> {len(filtered)}")
            return filtered
        
        # 检查变量值中的敏感信息
        filtered = {}
        for k, v in variables.items():
            if isinstance(v, str):
                # 检查字符串值是否包含敏感信息
                sensitive_patterns = [
                    'password', 'secret', 'token', 'key', 'credential',
                    'private', 'confidential'
                ]
                if any(pattern in v.lower() for pattern in sensitive_patterns):
                    print(f"跳过包含敏感信息的变量: {k}")
                    continue
            
            filtered[k] = v
        
        return filtered if len(filtered) != len(variables) else None


class DataTypeBasedSyncPlugin:
    """基于数据类型的同步过滤插件"""
    
    @hookimpl
    def dsl_filter_sync_variables(self, variables, sync_context):
        """根据数据类型过滤变量"""
        variable_source = sync_context.get('variable_source', '')
        sync_type = sync_context.get('sync_type', '')
        
        # YAML变量源的特殊处理
        if variable_source == 'yaml':
            filtered = {}
            for k, v in variables.items():
                # 跳过测试数据
                if k.startswith('test_') and sync_type == 'initial':
                    continue
                
                # 转换复杂对象为字符串（便于传输）
                if isinstance(v, (list, dict)) and len(str(v)) < 500:
                    filtered[k] = str(v)  # 转换为字符串
                elif not isinstance(v, (list, dict)):
                    filtered[k] = v
                    
            return filtered
        
        return None


class CustomBusinessLogicSyncPlugin:
    """自定义业务逻辑同步过滤插件"""
    
    def __init__(self, business_rules=None):
        """
        Args:
            business_rules: 业务规则配置
        """
        self.business_rules = business_rules or {
            'max_variables_per_sync': 50,
            'allowed_variable_prefixes': ['g_', 'api_', 'config_'],
            'blocked_servers': ['legacy_server'],
            'priority_variables': ['g_environment', 'g_base_url']
        }
    
    @hookimpl
    def dsl_filter_sync_variables(self, variables, sync_context):
        """基于业务规则过滤变量"""
        server_alias = sync_context.get('server_alias', '')
        
        # 检查服务器黑名单
        if server_alias in self.business_rules.get('blocked_servers', []):
            print(f"服务器 {server_alias} 在黑名单中，不同步任何变量")
            return {}
        
        # 应用变量数量限制
        max_vars = self.business_rules.get('max_variables_per_sync', 50)
        if len(variables) > max_vars:
            # 优先保留重要变量
            priority_vars = {}
            other_vars = {}
            
            priority_list = self.business_rules.get('priority_variables', [])
            for k, v in variables.items():
                if k in priority_list:
                    priority_vars[k] = v
                else:
                    other_vars[k] = v
            
            # 填充剩余槽位
            remaining = max_vars - len(priority_vars)
            if remaining > 0:
                other_items = list(other_vars.items())[:remaining]
                priority_vars.update(dict(other_items))
            
            print(f"业务规则限制变量数量: {len(variables)} -> {len(priority_vars)}")
            return priority_vars
        
        return None


# 使用示例
def register_sync_plugins():
    """注册同步过滤插件的示例函数"""
    from pytest_dsl.core.hook_manager import hook_manager
    
    # 注册各种插件
    hook_manager.register_plugin(EnvironmentBasedSyncPlugin(), "env_sync_filter")
    hook_manager.register_plugin(PerformanceOptimizedSyncPlugin(), "perf_sync_filter")
    hook_manager.register_plugin(SecurityBasedSyncPlugin(), "security_sync_filter")
    hook_manager.register_plugin(DataTypeBasedSyncPlugin(), "datatype_sync_filter")
    
    # 注册自定义业务逻辑插件
    business_rules = {
        'max_variables_per_sync': 30,
        'blocked_servers': ['old_server', 'deprecated_server'],
        'priority_variables': ['g_environment', 'g_base_url', 'api_version']
    }
    hook_manager.register_plugin(
        CustomBusinessLogicSyncPlugin(business_rules), 
        "business_sync_filter"
    )
    
    print("所有同步过滤插件已注册")


if __name__ == '__main__':
    # 演示插件注册
    register_sync_plugins()
