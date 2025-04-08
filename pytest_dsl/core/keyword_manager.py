from typing import Dict, Any, Callable, List
import functools
import allure


class Parameter:
    def __init__(self, name: str, mapping: str, description: str):
        self.name = name
        self.mapping = mapping
        self.description = description


class KeywordManager:
    def __init__(self):
        self._keywords: Dict[str, Dict] = {}
        self.current_context = None

    def register(self, name: str, parameters: List[Dict]):
        """关键字注册装饰器"""
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
            
            # 自动添加 step_name 到 mapping 中
            mapping["步骤名称"] = "step_name"
            
            self._keywords[name] = {
                'func': wrapper,
                'mapping': mapping,
                'parameters': param_list
            }
            return wrapper
        return decorator

    def execute(self, keyword_name: str, **params: Any) -> Any:
        """执行关键字"""
        keyword_info = self._keywords.get(keyword_name)
        if not keyword_info:
            raise KeyError(f"未注册的关键字: {keyword_name}")
        return keyword_info['func'](**params)

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
                docs.append(
                    f"  {param.name} ({param.mapping}): {param.description}")
            docs.append("")
        return "\n".join(docs)


# 创建全局关键字管理器实例
keyword_manager = KeywordManager()
