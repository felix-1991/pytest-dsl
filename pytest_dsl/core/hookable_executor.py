"""
可扩展的DSL执行器

支持hook机制的DSL执行器，提供统一的执行接口
"""
from typing import Dict, List, Optional, Any
from .dsl_executor import DSLExecutor
from .hook_manager import hook_manager


class HookableExecutor:
    """支持Hook机制的DSL执行器"""
    
    def __init__(self):
        self.executor = None
        self._ensure_initialized()
    
    def _ensure_initialized(self):
        """确保执行器已初始化"""
        if self.executor is None:
            self.executor = DSLExecutor(enable_hooks=True)
    
    def execute_dsl(self, dsl_id: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """执行DSL用例
        
        Args:
            dsl_id: DSL标识符
            context: 执行上下文（可选）
            
        Returns:
            执行结果
        """
        self._ensure_initialized()
        
        # 通过hook获取执行上下文扩展
        if self.executor.enable_hooks and self.executor.hook_manager:
            context_results = self.executor.hook_manager.pm.hook.dsl_get_execution_context(
                dsl_id=dsl_id, base_context=context or {}
            )
            for extended_context in context_results:
                if extended_context:
                    context = extended_context
                    break
        
        # 执行DSL（内容为空，通过hook加载）
        return self.executor.execute_from_content(
            content="",
            dsl_id=dsl_id,
            context=context
        )
    
    def list_dsl_cases(self, project_id: Optional[int] = None, 
                       filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """列出DSL用例
        
        Args:
            project_id: 项目ID（可选）
            filters: 过滤条件（可选）
            
        Returns:
            用例列表
        """
        self._ensure_initialized()
        
        if not (self.executor.enable_hooks and self.executor.hook_manager):
            return []
        
        all_cases = []
        case_results = self.executor.hook_manager.pm.hook.dsl_list_cases(
            project_id=project_id, filters=filters
        )
        
        for result in case_results:
            if result:
                all_cases.extend(result)
        
        return all_cases
    
    def validate_dsl_content(self, dsl_id: str, content: str) -> List[str]:
        """验证DSL内容
        
        Args:
            dsl_id: DSL标识符
            content: DSL内容
            
        Returns:
            验证错误列表，空列表表示验证通过
        """
        self._ensure_initialized()
        
        if not (self.executor.enable_hooks and self.executor.hook_manager):
            return []
        
        all_errors = []
        validation_results = self.executor.hook_manager.pm.hook.dsl_validate_content(
            dsl_id=dsl_id, content=content
        )
        
        for errors in validation_results:
            if errors:
                all_errors.extend(errors)
        
        return all_errors
    
    def transform_dsl_content(self, dsl_id: str, content: str) -> str:
        """转换DSL内容
        
        Args:
            dsl_id: DSL标识符
            content: 原始DSL内容
            
        Returns:
            转换后的DSL内容
        """
        self._ensure_initialized()
        
        if not (self.executor.enable_hooks and self.executor.hook_manager):
            return content
        
        transformed_content = content
        transform_results = self.executor.hook_manager.pm.hook.dsl_transform_content(
            dsl_id=dsl_id, content=content
        )
        
        for result in transform_results:
            if result:
                transformed_content = result
                break
        
        return transformed_content


# 全局实例
hookable_executor = HookableExecutor() 