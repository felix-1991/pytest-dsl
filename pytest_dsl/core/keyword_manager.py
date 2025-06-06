from typing import Dict, Any, Callable, List, Optional
import functools
import allure


class Parameter:
    def __init__(self, name: str, mapping: str, description: str, default: Any = None):
        self.name = name
        self.mapping = mapping
        self.description = description
        self.default = default


class KeywordManager:
    def __init__(self):
        self._keywords: Dict[str, Dict] = {}
        self.current_context = None

    def register(self, name: str, parameters: List[Dict], source_info: Optional[Dict] = None):
        """关键字注册装饰器
        
        Args:
            name: 关键字名称
            parameters: 参数列表
            source_info: 来源信息，包含 source_type, source_name, module_name 等
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(**kwargs):
                # 获取自定义步骤名称，如果未指定则使用关键字名称
                step_name = kwargs.pop('step_name', name)
                
                with allure.step(f"{step_name}"):
                    try:
                        result = func(**kwargs)
                        self._log_execution(step_name, kwargs, result)
                        return result
                    except Exception as e:
                        self._log_failure(step_name, kwargs, e)
                        raise

            param_list = [Parameter(**p) for p in parameters]
            mapping = {p.name: p.mapping for p in param_list}
            defaults = {p.mapping: p.default for p in param_list if p.default is not None}
            
            # 自动添加 step_name 到 mapping 中
            mapping["步骤名称"] = "step_name"
            
            # 构建关键字信息，包含来源信息
            keyword_info = {
                'func': wrapper,
                'mapping': mapping,
                'parameters': param_list,
                'defaults': defaults  # 存储默认值
            }
            
            # 添加来源信息
            if source_info:
                keyword_info.update(source_info)
            else:
                # 尝试从函数模块推断来源信息
                keyword_info.update(self._infer_source_info(func))
            
            self._keywords[name] = keyword_info
            return wrapper
        return decorator

    def _infer_source_info(self, func: Callable) -> Dict:
        """从函数推断来源信息"""
        source_info = {}
        
        if hasattr(func, '__module__'):
            module_name = func.__module__
            source_info['module_name'] = module_name
            
            if module_name.startswith('pytest_dsl.keywords'):
                # 内置关键字
                source_info['source_type'] = 'builtin'
                source_info['source_name'] = 'pytest-dsl内置'
            elif 'pytest_dsl' in module_name:
                # pytest-dsl相关但不是内置的
                source_info['source_type'] = 'internal'
                source_info['source_name'] = 'pytest-dsl'
            else:
                # 第三方插件或用户自定义
                source_info['source_type'] = 'external'
                # 提取可能的包名
                parts = module_name.split('.')
                if len(parts) > 1:
                    source_info['source_name'] = parts[0]
                else:
                    source_info['source_name'] = module_name
        
        return source_info

    def register_with_source(self, name: str, parameters: List[Dict], 
                           source_type: str, source_name: str, **kwargs):
        """带来源信息的关键字注册装饰器
        
        Args:
            name: 关键字名称
            parameters: 参数列表
            source_type: 来源类型 (builtin, plugin, local, remote, project_custom)
            source_name: 来源名称 (插件名、文件路径等)
            **kwargs: 其他来源相关信息
        """
        source_info = {
            'source_type': source_type,
            'source_name': source_name,
            **kwargs
        }
        return self.register(name, parameters, source_info)

    def execute(self, keyword_name: str, **params: Any) -> Any:
        """执行关键字"""
        keyword_info = self._keywords.get(keyword_name)
        if not keyword_info:
            raise KeyError(f"未注册的关键字: {keyword_name}")
        
        # 应用默认值
        final_params = {}
        defaults = keyword_info.get('defaults', {})
        
        # 首先设置所有默认值
        for param_key, default_value in defaults.items():
            final_params[param_key] = default_value
        
        # 然后用传入的参数覆盖默认值
        final_params.update(params)
        
        return keyword_info['func'](**final_params)

    def get_keyword_info(self, keyword_name: str) -> Dict:
        """获取关键字信息"""
        keyword_info = self._keywords.get(keyword_name)
        if not keyword_info:
            return None
            
        # 动态添加step_name参数到参数列表中
        if not any(p.name == "步骤名称" for p in keyword_info['parameters']):
            keyword_info['parameters'].append(Parameter(
                name="步骤名称",
                mapping="step_name",
                description="自定义的步骤名称，用于在报告中显示"
            ))
            
        return keyword_info

    def get_keywords_by_source(self) -> Dict[str, List[str]]:
        """按来源分组获取关键字"""
        by_source = {}
        
        for name, info in self._keywords.items():
            source_name = info.get('source_name', '未知来源')
            if source_name not in by_source:
                by_source[source_name] = []
            by_source[source_name].append(name)
        
        return by_source

    def _log_execution(self, keyword_name: str, params: Dict, result: Any) -> None:
        """记录关键字执行结果"""
        allure.attach(
            f"参数: {params}\n返回值: {result}",
            name=f"关键字 {keyword_name} 执行详情",
            attachment_type=allure.attachment_type.TEXT
        )

    def _log_failure(self, keyword_name: str, params: Dict, error: Exception) -> None:
        """记录关键字执行失败"""
        allure.attach(
            f"参数: {params}\n异常: {str(error)}",
            name=f"关键字 {keyword_name} 执行失败",
            attachment_type=allure.attachment_type.TEXT
        )

    def generate_docs(self) -> str:
        """生成关键字文档"""
        docs = []
        for name, info in self._keywords.items():
            docs.append(f"关键字: {name}")
            docs.append("参数:")
            # 确保step_name参数在文档中显示
            if not any(p.name == "步骤名称" for p in info['parameters']):
                info['parameters'].append(Parameter(
                    name="步骤名称",
                    mapping="step_name",
                    description="自定义的步骤名称，用于在报告中显示"
                ))
            for param in info['parameters']:
                default_info = f" (默认值: {param.default})" if param.default is not None else ""
                docs.append(
                    f"  {param.name} ({param.mapping}): {param.description}{default_info}")
            docs.append("")
        return "\n".join(docs)


# 创建全局关键字管理器实例
keyword_manager = KeywordManager()
