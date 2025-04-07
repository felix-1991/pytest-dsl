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
                with allure.step(f"执行关键字: {name}"):
                    try:
                        # 保存当前上下文引用
                        # if 'context' in kwargs:
                        #     self.current_context = kwargs['context']
                            
                        result = func(**kwargs)
                        self._log_execution(name, kwargs, result)
                        return result
                    except Exception as e:
                        self._log_failure(name, kwargs, e)
                        raise

            param_list = [Parameter(**p) for p in parameters]
            mapping = {p.name: p.mapping for p in param_list}
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
        return self._keywords.get(keyword_name)

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
            for param in info['parameters']:
                docs.append(
                    f"  {param.name} ({param.mapping}): {param.description}")
            docs.append("")
        return "\n".join(docs)


# 创建全局关键字管理器实例
keyword_manager = KeywordManager()
