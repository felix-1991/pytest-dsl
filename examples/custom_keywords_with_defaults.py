"""
自定义关键字默认值功能演示

这个示例展示了如何在自定义关键字中使用默认值功能
"""

from pytest_dsl.core.keyword_manager import keyword_manager


@keyword_manager.register('HTTP请求模拟', [
    {'name': '方法', 'mapping': 'method', 'description': 'HTTP方法', 'default': 'GET'},
    {'name': '地址', 'mapping': 'url', 'description': '请求地址'},
    {'name': '超时', 'mapping': 'timeout', 'description': '超时时间（秒）', 'default': 30},
    {'name': '重试次数', 'mapping': 'retries', 'description': '重试次数', 'default': 3},
    {'name': '验证SSL', 'mapping': 'verify_ssl', 'description': '是否验证SSL证书', 'default': True}
])
def http_request_mock(**kwargs):
    """模拟HTTP请求，展示默认值功能
    
    Args:
        method: HTTP方法
        url: 请求地址
        timeout: 超时时间
        retries: 重试次数
        verify_ssl: 是否验证SSL证书
        context: 测试上下文
        
    Returns:
        dict: 模拟的响应结果
    """
    method = kwargs.get('method', 'GET')
    url = kwargs.get('url', '')
    timeout = kwargs.get('timeout', 30)
    retries = kwargs.get('retries', 3)
    verify_ssl = kwargs.get('verify_ssl', True)
    
    # 模拟请求执行
    result = {
        'status_code': 200,
        'method': method,
        'url': url,
        'timeout': timeout,
        'retries': retries,
        'verify_ssl': verify_ssl,
        'response_body': f'模拟响应 - {method} {url}'
    }
    
    print(f"执行HTTP请求模拟: {method} {url}")
    print(f"参数 - 超时: {timeout}秒, 重试: {retries}次, SSL验证: {verify_ssl}")
    
    return result


@keyword_manager.register('数据库连接', [
    {'name': '主机', 'mapping': 'host', 'description': '数据库主机地址', 'default': 'localhost'},
    {'name': '端口', 'mapping': 'port', 'description': '数据库端口', 'default': 3306},
    {'name': '用户名', 'mapping': 'username', 'description': '用户名'},
    {'name': '密码', 'mapping': 'password', 'description': '密码'},
    {'name': '数据库名', 'mapping': 'database', 'description': '数据库名称'},
    {'name': '连接池大小', 'mapping': 'pool_size', 'description': '连接池大小', 'default': 10},
    {'name': '连接超时', 'mapping': 'connect_timeout', 'description': '连接超时时间（秒）', 'default': 30}
])
def database_connect(**kwargs):
    """模拟数据库连接，展示默认值功能
    
    Args:
        host: 数据库主机
        port: 数据库端口
        username: 用户名
        password: 密码
        database: 数据库名称
        pool_size: 连接池大小
        connect_timeout: 连接超时时间
        context: 测试上下文
        
    Returns:
        dict: 连接信息
    """
    host = kwargs.get('host', 'localhost')
    port = kwargs.get('port', 3306)
    username = kwargs.get('username', '')
    password = kwargs.get('password', '')
    database = kwargs.get('database', '')
    pool_size = kwargs.get('pool_size', 10)
    connect_timeout = kwargs.get('connect_timeout', 30)
    
    # 模拟连接过程
    connection_info = {
        'host': host,
        'port': port,
        'username': username,
        'database': database,
        'pool_size': pool_size,
        'connect_timeout': connect_timeout,
        'status': 'connected',
        'connection_id': f"{host}:{port}/{database}"
    }
    
    print(f"连接数据库: {host}:{port}/{database}")
    print(f"连接参数 - 用户: {username}, 池大小: {pool_size}, 超时: {connect_timeout}秒")
    
    return connection_info


@keyword_manager.register('文件处理', [
    {'name': '文件路径', 'mapping': 'file_path', 'description': '文件路径'},
    {'name': '操作', 'mapping': 'operation', 'description': '操作类型', 'default': 'read'},
    {'name': '编码', 'mapping': 'encoding', 'description': '文件编码', 'default': 'utf-8'},
    {'name': '缓冲区大小', 'mapping': 'buffer_size', 'description': '缓冲区大小（字节）', 'default': 8192},
    {'name': '创建目录', 'mapping': 'create_dirs', 'description': '是否自动创建目录', 'default': False}
])
def file_operation(**kwargs):
    """模拟文件处理，展示默认值功能
    
    Args:
        file_path: 文件路径
        operation: 操作类型
        encoding: 文件编码
        buffer_size: 缓冲区大小
        create_dirs: 是否自动创建目录
        context: 测试上下文
        
    Returns:
        dict: 操作结果
    """
    file_path = kwargs.get('file_path', '')
    operation = kwargs.get('operation', 'read')
    encoding = kwargs.get('encoding', 'utf-8')
    buffer_size = kwargs.get('buffer_size', 8192)
    create_dirs = kwargs.get('create_dirs', False)
    
    # 模拟文件操作
    result = {
        'file_path': file_path,
        'operation': operation,
        'encoding': encoding,
        'buffer_size': buffer_size,
        'create_dirs': create_dirs,
        'status': 'success',
        'message': f'模拟{operation}操作完成'
    }
    
    print(f"文件操作: {operation} - {file_path}")
    print(f"参数 - 编码: {encoding}, 缓冲区: {buffer_size}字节, 创建目录: {create_dirs}")
    
    return result


if __name__ == '__main__':
    print("自定义关键字已注册，包含以下关键字：")
    print("1. HTTP请求模拟 - 展示HTTP请求参数的默认值")
    print("2. 数据库连接 - 展示数据库连接参数的默认值")
    print("3. 文件处理 - 展示文件操作参数的默认值")
    print("\n可以在DSL文件中使用这些关键字进行测试。") 