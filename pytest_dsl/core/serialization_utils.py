#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
序列化工具模块

提供统一的XML-RPC序列化检查和转换功能，避免代码重复。
"""

import datetime
import sys
import base64
from typing import Any, Dict, List, Optional


class XMLRPCSerializer:
    """XML-RPC序列化工具类
    
    统一处理XML-RPC序列化检查、转换和过滤逻辑，
    避免在多个类中重复实现相同的序列化代码。
    """
    
    # 敏感信息过滤模式
    DEFAULT_EXCLUDE_PATTERNS = [
        
    ]

    # XML-RPC限制
    MAX_STRING_LENGTH = 10000  # 最大字符串长度
    MAX_INT_VALUE = 2**31 - 1  # XML-RPC int最大值
    MIN_INT_VALUE = -2**31     # XML-RPC int最小值
    
    @staticmethod
    def is_serializable(value: Any) -> bool:
        """检查值是否可以被XML-RPC序列化
        
        XML-RPC支持的类型：
        - None (需要allow_none=True)
        - bool, int, float, str, bytes
        - datetime.datetime
        - list (元素也必须可序列化)
        - dict (键必须是字符串，值必须可序列化)
        
        Args:
            value: 要检查的值
            
        Returns:
            bool: 是否可序列化
        """
        # 基本类型
        if value is None:
            return True
        if isinstance(value, (bool, int, float, str, bytes)):
            return True
        if isinstance(value, datetime.datetime):
            return True
        
        # 严格检查：只允许内置的list和dict类型，不允许自定义类
        value_type = type(value)
        
        # 检查是否为内置list类型（不是子类）
        if value_type is list:
            try:
                for item in value:
                    if not XMLRPCSerializer.is_serializable(item):
                        return False
                return True
            except Exception:
                return False
        
        # 检查是否为内置tuple类型
        if value_type is tuple:
            try:
                for item in value:
                    if not XMLRPCSerializer.is_serializable(item):
                        return False
                return True
            except Exception:
                return False
        
        # 检查是否为内置dict类型（不是子类，如DotAccessDict）
        if value_type is dict:
            try:
                for k, v in value.items():
                    # XML-RPC要求字典的键必须是字符串
                    if not isinstance(k, str):
                        return False
                    if not XMLRPCSerializer.is_serializable(v):
                        return False
                return True
            except Exception:
                return False
        
        # 其他类型都不可序列化
        return False

    @staticmethod
    def safe_serialize_value(value: Any) -> Any:
        """安全地序列化单个值，处理各种边界情况

        Args:
            value: 要序列化的值

        Returns:
            安全的序列化值
        """
        if value is None:
            return None

        # 处理字符串
        if isinstance(value, str):
            # 检查字符串长度
            if len(value) > XMLRPCSerializer.MAX_STRING_LENGTH:
                return f"<字符串过长: {len(value)} 字符，已截断>"

            # 检查是否包含非法XML字符
            try:
                # 尝试编码为UTF-8
                value.encode('utf-8')

                # 检查是否包含XML非法字符
                illegal_chars = ['\x00', '\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07', '\x08',
                               '\x0b', '\x0c', '\x0e', '\x0f', '\x10', '\x11', '\x12', '\x13', '\x14',
                               '\x15', '\x16', '\x17', '\x18', '\x19', '\x1a', '\x1b', '\x1c', '\x1d',
                               '\x1e', '\x1f']

                for char in illegal_chars:
                    if char in value:
                        # 移除非法字符
                        value = value.replace(char, '')

                return value
            except UnicodeEncodeError:
                # 编码失败，返回安全的表示
                return f"<编码错误: 无法编码为UTF-8>"

        # 处理整数
        elif isinstance(value, int):
            # 检查整数范围
            if value > XMLRPCSerializer.MAX_INT_VALUE:
                # 超出范围时使用特殊标记，服务器端会自动转换回整数
                return f"__bigint__:{value}"
            elif value < XMLRPCSerializer.MIN_INT_VALUE:
                # 超出范围时使用特殊标记，服务器端会自动转换回整数
                return f"__bigint__:{value}"
            return value

        # 处理浮点数
        elif isinstance(value, float):
            # 检查是否为特殊值
            if value != value:  # NaN
                return "<NaN>"
            elif value == float('inf'):
                return "<正无穷>"
            elif value == float('-inf'):
                return "<负无穷>"
            return value

        # 处理bytes
        elif isinstance(value, bytes):
            try:
                # 检查是否包含null字节或其他非法字符
                if b'\x00' in value or any(b in value for b in [b'\x01', b'\x02', b'\x03', b'\x04', b'\x05', b'\x06', b'\x07', b'\x08', b'\x0b', b'\x0c', b'\x0e', b'\x0f']):
                    # 包含非法字符，直接使用base64编码
                    encoded = base64.b64encode(value).decode('ascii')
                    return f"<base64: {encoded}>"

                # 尝试解码为UTF-8字符串
                decoded = value.decode('utf-8')

                # 再次检查解码后的字符串是否包含非法XML字符
                illegal_chars = ['\x00', '\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07', '\x08',
                               '\x0b', '\x0c', '\x0e', '\x0f', '\x10', '\x11', '\x12', '\x13', '\x14',
                               '\x15', '\x16', '\x17', '\x18', '\x19', '\x1a', '\x1b', '\x1c', '\x1d',
                               '\x1e', '\x1f']

                for char in illegal_chars:
                    if char in decoded:
                        # 包含非法字符，使用base64编码
                        encoded = base64.b64encode(value).decode('ascii')
                        return f"<base64: {encoded}>"

                return decoded

            except UnicodeDecodeError:
                # 解码失败，使用base64编码
                try:
                    encoded = base64.b64encode(value).decode('ascii')
                    return f"<base64: {encoded}>"
                except Exception:
                    return f"<二进制数据: {len(value)} 字节>"

        # 处理datetime
        elif isinstance(value, datetime.datetime):
            try:
                # 转换为ISO格式字符串，移除时区信息以避免序列化问题
                if value.tzinfo is not None:
                    value = value.replace(tzinfo=None)
                return value.isoformat()
            except Exception:
                return f"<日期时间: {str(value)}>"

        # 处理布尔值
        elif isinstance(value, bool):
            return value

        # 其他类型返回原值
        return value
    
    @staticmethod
    def convert_to_serializable(value: Any, visited: Optional[set] = None) -> Optional[Any]:
        """尝试将值转换为XML-RPC可序列化的格式

        Args:
            value: 要转换的值
            visited: 已访问对象的集合，用于检测循环引用

        Returns:
            转换后的值，如果无法转换则返回None
        """
        # 初始化访问集合
        if visited is None:
            visited = set()

        # 检测循环引用
        value_id = id(value)
        if value_id in visited:
            # 检测到循环引用，返回对象的字符串表示
            try:
                return f"<循环引用: {type(value).__name__}>"
            except Exception:
                return "<循环引用: 未知类型>"

        # 对于字典和列表，需要递归处理，不能直接调用 safe_serialize_value
        # 因为 safe_serialize_value 只处理基本类型，不处理容器类型
        if isinstance(value, dict):
            # 注意：循环引用检查已在第226行完成
            visited.add(value_id)
            try:
                # 递归处理字典中的值
                converted_dict = {}
                for k, v in value.items():
                    # 键必须是字符串
                    if not isinstance(k, str):
                        k = str(k)
                    # 递归转换值
                    converted_value = XMLRPCSerializer.convert_to_serializable(v, visited)
                    if converted_value is not None or v is None:
                        converted_dict[k] = converted_value
                return converted_dict
            finally:
                visited.discard(value_id)
        
        if isinstance(value, (list, tuple)):
            # 注意：循环引用检查已在第226行完成
            visited.add(value_id)
            try:
                # 递归处理列表/元组中的元素
                converted_list = []
                for item in value:
                    converted_item = XMLRPCSerializer.convert_to_serializable(item, visited)
                    if converted_item is not None or item is None:
                        converted_list.append(converted_item)
                return tuple(converted_list) if isinstance(value, tuple) else converted_list
            finally:
                visited.discard(value_id)
        
        # 对于其他可序列化的基本类型，进行安全处理
        if XMLRPCSerializer.is_serializable(value):
            return XMLRPCSerializer.safe_serialize_value(value)

        # 将当前对象添加到访问集合中
        visited.add(value_id)

        try:
            # 检查是否为SQLAlchemy的InstrumentedList或其他已知的循环引用类型
            type_name = type(value).__name__
            if type_name in ['InstrumentedList', 'Agent', 'InstrumentedAttribute']:
                # 对于这些类型，直接返回类型描述，避免深度遍历
                return f"<{type_name}: 已跳过序列化>"

            # 尝试转换类字典对象为标准字典
            if hasattr(value, 'keys') and hasattr(value, 'items'):
                try:
                    converted_dict = {}
                    for k, v in value.items():
                        # 键必须是字符串
                        if not isinstance(k, str):
                            k = str(k)

                        # 递归转换值
                        converted_value = XMLRPCSerializer.convert_to_serializable(v, visited)
                        if converted_value is not None or v is None:
                            converted_dict[k] = converted_value
                        else:
                            # 如果无法转换子值，跳过这个键值对
                            print(f"跳过无法转换的字典项: {k} "
                                  f"(类型: {type(v).__name__})")
                            continue

                    return converted_dict
                except Exception as e:
                    print(f"转换类字典对象失败: {e}")
                    return None

            # 尝试转换类列表对象为标准列表
            if hasattr(value, '__iter__') and not isinstance(value, (str, bytes)):
                try:
                    converted_list = []
                    for item in value:
                        converted_item = XMLRPCSerializer.convert_to_serializable(item, visited)
                        if converted_item is not None or item is None:
                            converted_list.append(converted_item)
                        else:
                            # 如果无法转换子项，跳过
                            print(f"跳过无法转换的列表项: "
                                  f"(类型: {type(item).__name__})")
                            continue

                    return converted_list
                except Exception as e:
                    print(f"转换类列表对象失败: {e}")
                    return None

            # 尝试转换为字符串表示
            try:
                str_value = str(value)
                # 避免转换过长的字符串或包含敏感信息的对象
                if (len(str_value) < 1000 and
                    not any(pattern in str_value.lower()
                           for pattern in XMLRPCSerializer.DEFAULT_EXCLUDE_PATTERNS)):
                    return str_value
            except Exception:
                pass

            # 无法转换
            return None

        finally:
            # 从访问集合中移除当前对象
            visited.discard(value_id)
    
    @staticmethod
    def filter_variables(variables: Dict[str, Any], 
                        exclude_patterns: Optional[List[str]] = None) -> Dict[str, Any]:
        """过滤变量字典，移除敏感变量和不可序列化的变量
        
        Args:
            variables: 原始变量字典
            exclude_patterns: 排除模式列表，如果为None则使用默认模式
            
        Returns:
            Dict[str, Any]: 过滤后的变量字典
        """
        if exclude_patterns is None:
            exclude_patterns = XMLRPCSerializer.DEFAULT_EXCLUDE_PATTERNS
        
        filtered_variables = {}
        
        for var_name, var_value in variables.items():
            # 检查是否需要排除
            should_exclude = False
            var_name_lower = var_name.lower()
            
            # 检查变量名
            for pattern in exclude_patterns:
                if pattern.lower() in var_name_lower:
                    should_exclude = True
                    break
            
            # 如果值是字符串，也检查是否包含敏感信息
            if not should_exclude and isinstance(var_value, str):
                value_lower = var_value.lower()
                for pattern in exclude_patterns:
                    if (pattern.lower() in value_lower and 
                        len(var_value) < 100):  # 只检查短字符串
                        should_exclude = True
                        break
            
            if not should_exclude:
                # 尝试转换为可序列化的格式
                serializable_value = XMLRPCSerializer.convert_to_serializable(var_value)
                # 注意：None值转换后仍然是None，但这是有效的结果
                if serializable_value is not None or var_value is None:
                    filtered_variables[var_name] = serializable_value
                else:
                    print(f"跳过不可序列化的变量: {var_name} "
                          f"(类型: {type(var_value).__name__})")
            else:
                print(f"跳过敏感变量: {var_name}")
        
        return filtered_variables
    
    @staticmethod
    def validate_xmlrpc_data(data: Any) -> tuple[bool, str]:
        """验证数据是否可以通过XML-RPC传输

        Args:
            data: 要验证的数据

        Returns:
            tuple[bool, str]: (是否可以传输, 错误信息)
        """
        try:
            import xmlrpc.client
            # 尝试序列化数据
            serialized = xmlrpc.client.dumps((data,), allow_none=True)

            # 检查序列化后的大小
            if len(serialized) > 1024 * 1024 * 5:  # 5MB限制
                return False, f"序列化数据过大: {len(serialized)} 字节"

            # 尝试反序列化验证完整性
            xmlrpc.client.loads(serialized)
            return True, ""

        except UnicodeDecodeError as e:
            return False, f"Unicode解码错误: {str(e)}"
        except UnicodeEncodeError as e:
            return False, f"Unicode编码错误: {str(e)}"
        except OverflowError as e:
            return False, f"数值溢出错误: {str(e)}"
        except ValueError as e:
            return False, f"值错误: {str(e)}"
        except Exception as e:
            return False, f"序列化错误: {type(e).__name__}: {str(e)}"

    @staticmethod
    def safe_xmlrpc_call(server_proxy, method_name: str, *args, **kwargs):
        """安全的XML-RPC调用，包含错误处理和重试机制

        Args:
            server_proxy: XML-RPC服务器代理
            method_name: 方法名
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            调用结果或错误信息
        """
        import xmlrpc.client
        import socket
        import http.client

        try:
            # 获取方法
            method = getattr(server_proxy, method_name)

            # 先转换参数（处理超长整数等边界情况）
            # 这样可以确保超长整数在验证前就被转换为字符串格式
            converted_args = []
            for arg in args:
                converted_arg = XMLRPCSerializer.convert_to_serializable(arg)
                converted_args.append(converted_arg)
            
            converted_kwargs = {}
            for key, value in kwargs.items():
                converted_value = XMLRPCSerializer.convert_to_serializable(value)
                converted_kwargs[key] = converted_value

            # 验证转换后的参数
            for i, arg in enumerate(converted_args):
                is_valid, error_msg = XMLRPCSerializer.validate_xmlrpc_data(arg)
                if not is_valid:
                    raise ValueError(f"参数 {i} 无法序列化: {error_msg}")

            for key, value in converted_kwargs.items():
                is_valid, error_msg = XMLRPCSerializer.validate_xmlrpc_data(value)
                if not is_valid:
                    raise ValueError(f"参数 '{key}' 无法序列化: {error_msg}")

            # 执行调用（使用转换后的参数）
            return method(*converted_args, **converted_kwargs)

        except xmlrpc.client.ProtocolError as e:
            raise Exception(f"XML-RPC协议错误: {e.errcode} {e.errmsg}")
        except xmlrpc.client.Fault as e:
            raise Exception(f"XML-RPC服务器错误: {e.faultCode} {e.faultString}")
        except socket.timeout:
            raise Exception("XML-RPC调用超时")
        except socket.error as e:
            raise Exception(f"网络连接错误: {str(e)}")
        except http.client.HTTPException as e:
            raise Exception(f"HTTP错误: {str(e)}")
        except UnicodeError as e:
            raise Exception(f"编码错误: {str(e)}")
        except Exception as e:
            raise Exception(f"XML-RPC调用失败: {type(e).__name__}: {str(e)}")


# 创建全局序列化器实例，方便直接使用
xmlrpc_serializer = XMLRPCSerializer() 