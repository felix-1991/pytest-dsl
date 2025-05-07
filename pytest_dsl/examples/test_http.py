"""装饰器测试示例

该示例展示如何使用auto_dsl装饰器创建测试类
"""

from pytest_dsl.core.auto_decorator import auto_dsl
from pytest_dsl.core.auth_provider import register_auth_provider, CustomAuthProvider
import requests
import json
import logging
import sys

# 配置日志输出
logging.basicConfig(
    level=logging.DEBUG,  # 设置为DEBUG级别
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("CSRF_AUTH_DEBUG")


@auto_dsl("./http")
class TestHttp:
    """HTTP测试类
    
    该类使用auto_dsl装饰器，测试http目录下的.auto文件。
    """
    pass

