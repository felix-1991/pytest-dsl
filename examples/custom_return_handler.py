"""
自定义返回处理器示例

展示如何创建和注册自定义的远程关键字返回处理器
"""

from pytest_dsl.remote.return_handlers import RemoteReturnHandler, register_return_handler
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class DatabaseReturnHandler(RemoteReturnHandler):
    """数据库操作关键字返回处理器示例"""
    
    def can_handle(self, return_data: Dict[str, Any]) -> bool:
        """检查是否为数据库操作关键字的返回格式"""
        return (isinstance(return_data, dict) and 
                'db_result' in return_data and
                'affected_rows' in return_data)
    
    def process(self, return_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
        """处理数据库操作关键字的返回数据"""
        logger.info("使用数据库返回处理器处理数据")
        
        # 提取数据库特定信息
        db_result = return_data.get('db_result')
        affected_rows = return_data.get('affected_rows', 0)
        connection_info = return_data.get('connection_info', {})
        
        # 构建副作用信息
        side_effects = {}
        
        # 如果有查询结果，可能需要注入变量
        if 'query_variables' in return_data:
            side_effects['variables'] = return_data['query_variables']
            
        # 数据库连接状态更新
        if connection_info:
            side_effects['context_updates'] = {
                'db_connection': connection_info
            }
            

        
        return {
            'result': db_result,
            'side_effects': side_effects,
            'metadata': {
                'affected_rows': affected_rows,
                'execution_time': return_data.get('execution_time'),
                'keyword_type': 'database_operation'
            }
        }
    
    @property
    def priority(self) -> int:
        return 15  # 中等优先级


class FileOperationReturnHandler(RemoteReturnHandler):
    """文件操作关键字返回处理器示例"""
    
    def can_handle(self, return_data: Dict[str, Any]) -> bool:
        """检查是否为文件操作关键字的返回格式"""
        return (isinstance(return_data, dict) and 
                'file_path' in return_data and
                'operation' in return_data)
    
    def process(self, return_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
        """处理文件操作关键字的返回数据"""
        logger.info("使用文件操作返回处理器处理数据")
        
        file_path = return_data.get('file_path')
        operation = return_data.get('operation')
        file_content = return_data.get('file_content')
        
        side_effects = {}
        
        # 如果读取了文件内容，注入到变量中
        if file_content is not None:
            # 根据文件路径生成变量名
            var_name = f"file_content_{file_path.replace('/', '_').replace('.', '_')}"
            side_effects['variables'] = {var_name: file_content}
            
        # 文件系统状态更新
        side_effects['context_updates'] = {
            'last_file_operation': {
                'path': file_path,
                'operation': operation,
                'timestamp': return_data.get('timestamp')
            }
        }
        

        
        return {
            'result': return_data.get('result', True),
            'side_effects': side_effects,
            'metadata': {
                'file_path': file_path,
                'operation': operation,
                'keyword_type': 'file_operation'
            }
        }
    
    @property
    def priority(self) -> int:
        return 25


class CacheReturnHandler(RemoteReturnHandler):
    """缓存操作关键字返回处理器示例"""
    
    def can_handle(self, return_data: Dict[str, Any]) -> bool:
        """检查是否为缓存操作关键字的返回格式"""
        return (isinstance(return_data, dict) and 
                'cache_key' in return_data and
                'cache_operation' in return_data)
    
    def process(self, return_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
        """处理缓存操作关键字的返回数据"""
        logger.info("使用缓存返回处理器处理数据")
        
        cache_key = return_data.get('cache_key')
        operation = return_data.get('cache_operation')
        cache_value = return_data.get('cache_value')
        
        side_effects = {}
        
        # 如果是GET操作且有值，注入变量
        if operation == 'GET' and cache_value is not None:
            side_effects['variables'] = {f"cache_{cache_key}": cache_value}
            
        # 缓存状态更新
        side_effects['context_updates'] = {
            'cache_stats': {
                'last_operation': operation,
                'last_key': cache_key,
                'hit': return_data.get('cache_hit', False)
            }
        }
        
        return {
            'result': cache_value if operation == 'GET' else return_data.get('success', True),
            'side_effects': side_effects,
            'metadata': {
                'cache_key': cache_key,
                'operation': operation,
                'keyword_type': 'cache_operation'
            }
        }
    
    @property
    def priority(self) -> int:
        return 30


def register_custom_handlers():
    """注册所有自定义返回处理器"""
    register_return_handler(DatabaseReturnHandler())
    register_return_handler(FileOperationReturnHandler())
    register_return_handler(CacheReturnHandler())
    logger.info("已注册所有自定义返回处理器")


# 示例：如何在远程关键字中使用新格式
def example_database_keyword(query: str, connection: str = "default"):
    """示例数据库关键字，展示如何返回新格式"""
    # 模拟数据库操作
    result = [{"id": 1, "name": "test"}]
    affected_rows = 1

    # 返回新的通用格式
    return {
        "result": result,
        "side_effects": {
            "variables": {"last_query_result": result},
            "context_updates": {
                "db_connection": {"status": "active", "connection": connection}
            }
        },
        "metadata": {
            "affected_rows": affected_rows,
            "execution_time": 0.05,
            "keyword_type": "database_operation"
        }
    }


if __name__ == "__main__":
    # 注册自定义处理器
    register_custom_handlers()
    
    # 测试处理器
    from pytest_dsl.remote.return_handlers import return_handler_registry
    
    # 测试数据库返回处理器
    db_data = {
        "db_result": [{"id": 1, "name": "test"}],
        "affected_rows": 1,
        "query_variables": {"last_id": 1}
    }
    
    processed = return_handler_registry.process(db_data)
    print("数据库处理结果:", processed)
    
    # 测试文件操作返回处理器
    file_data = {
        "file_path": "/tmp/test.txt",
        "operation": "read",
        "file_content": "Hello World",
        "result": True
    }
    
    processed = return_handler_registry.process(file_data)
    print("文件操作处理结果:", processed)
