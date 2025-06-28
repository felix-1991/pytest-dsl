#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
序列化工具模块

提供统一的XML-RPC序列化检查和转换功能，避免代码重复。
"""

import datetime
from typing import Any, Dict, List, Optional


class XMLRPCSerializer:
    """XML-RPC序列化工具类
    
    统一处理XML-RPC序列化检查、转换和过滤逻辑，
    避免在多个类中重复实现相同的序列化代码。
    """
    
    # 敏感信息过滤模式
    DEFAULT_EXCLUDE_PATTERNS = [
        'password', 'secret', 'token', 'credential', 'auth', 'private'
    ]
    
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
    def convert_to_serializable(value: Any) -> Optional[Any]:
        """尝试将值转换为XML-RPC可序列化的格式
        
        Args:
            value: 要转换的值
            
        Returns:
            转换后的值，如果无法转换则返回None
        """
        # 如果已经可序列化，直接返回
        if XMLRPCSerializer.is_serializable(value):
            return value
        
        # 尝试转换类字典对象为标准字典
        if hasattr(value, 'keys') and hasattr(value, 'items'):
            try:
                converted_dict = {}
                for k, v in value.items():
                    # 键必须是字符串
                    if not isinstance(k, str):
                        k = str(k)
                    
                    # 递归转换值
                    converted_value = XMLRPCSerializer.convert_to_serializable(v)
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
                    converted_item = XMLRPCSerializer.convert_to_serializable(item)
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
    def validate_xmlrpc_data(data: Any) -> bool:
        """验证数据是否可以通过XML-RPC传输
        
        Args:
            data: 要验证的数据
            
        Returns:
            bool: 是否可以传输
        """
        try:
            import xmlrpc.client
            # 尝试序列化数据
            xmlrpc.client.dumps((data,), allow_none=True)
            return True
        except Exception:
            return False


# 创建全局序列化器实例，方便直接使用
xmlrpc_serializer = XMLRPCSerializer() 