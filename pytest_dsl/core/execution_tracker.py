"""
DSL执行跟踪器
负责跟踪DSL执行过程中的行号、状态等信息，并提供回调接口
"""

import time
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class ExecutionStatus(Enum):
    """执行状态枚举"""
    PENDING = "pending"      # 等待执行
    RUNNING = "running"      # 正在执行
    SUCCESS = "success"      # 执行成功
    FAILED = "failed"        # 执行失败
    SKIPPED = "skipped"      # 跳过执行


@dataclass
class ExecutionStep:
    """执行步骤信息"""
    line_number: int
    node_type: str
    description: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error: Optional[str] = None
    result: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> Optional[float]:
        """计算执行耗时"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    def start(self):
        """开始执行"""
        self.status = ExecutionStatus.RUNNING
        self.start_time = time.time()

    def finish(self, result: Any = None, error: str = None):
        """完成执行"""
        self.end_time = time.time()
        if error:
            self.status = ExecutionStatus.FAILED
            self.error = error
        else:
            self.status = ExecutionStatus.SUCCESS
            self.result = result

    def skip(self, reason: str = None):
        """跳过执行"""
        self.status = ExecutionStatus.SKIPPED
        if reason:
            self.metadata['skip_reason'] = reason


class ExecutionTracker:
    """DSL执行跟踪器"""

    def __init__(self, dsl_id: str = None):
        self.dsl_id = dsl_id
        self.steps: List[ExecutionStep] = []
        self.current_step: Optional[ExecutionStep] = None
        self.execution_start_time: Optional[float] = None
        self.execution_end_time: Optional[float] = None
        self.callbacks: Dict[str, List[Callable]] = {
            'step_start': [],
            'step_finish': [],
            'execution_start': [],
            'execution_finish': [],
            'line_change': []
        }
        self._lock = threading.Lock()

        # 执行统计
        self.total_steps = 0
        self.completed_steps = 0
        self.failed_steps = 0

    def register_callback(self, event: str, callback: Callable):
        """注册回调函数

        Args:
            event: 事件类型 (step_start, step_finish, execution_start, 
                   execution_finish, line_change)
            callback: 回调函数
        """
        if event in self.callbacks:
            self.callbacks[event].append(callback)

    def _trigger_callbacks(self, event: str, **kwargs):
        """触发回调函数"""
        for callback in self.callbacks.get(event, []):
            try:
                callback(tracker=self, **kwargs)
            except Exception as e:
                # 回调异常不应影响主执行流程
                print(f"回调函数执行异常: {e}")

    def start_execution(self):
        """开始执行"""
        with self._lock:
            self.execution_start_time = time.time()
            self._trigger_callbacks('execution_start')

    def finish_execution(self):
        """完成执行"""
        with self._lock:
            self.execution_end_time = time.time()
            self._trigger_callbacks('execution_finish')

    def start_step(self, line_number: int, node_type: str,
                   description: str, **metadata) -> ExecutionStep:
        """开始执行步骤"""
        with self._lock:
            step = ExecutionStep(
                line_number=line_number,
                node_type=node_type,
                description=description,
                metadata=metadata
            )
            step.start()

            self.steps.append(step)
            self.current_step = step
            self.total_steps += 1

            # 触发回调
            self._trigger_callbacks('step_start', step=step)
            self._trigger_callbacks('line_change',
                                    line_number=line_number, step=step)

            return step

    def finish_current_step(self, result: Any = None, error: str = None):
        """完成当前步骤"""
        with self._lock:
            if self.current_step:
                self.current_step.finish(result, error)

                if error:
                    self.failed_steps += 1
                else:
                    self.completed_steps += 1

                # 触发回调
                self._trigger_callbacks('step_finish', step=self.current_step)

                # 记录到Allure
                self._log_step_to_allure(self.current_step)

                self.current_step = None

    def skip_current_step(self, reason: str = None):
        """跳过当前步骤"""
        with self._lock:
            if self.current_step:
                self.current_step.skip(reason)
                self.completed_steps += 1

                # 触发回调
                self._trigger_callbacks('step_finish', step=self.current_step)

                # 记录到Allure
                self._log_step_to_allure(self.current_step)

                self.current_step = None

    def get_current_line(self) -> Optional[int]:
        """获取当前执行行号"""
        return self.current_step.line_number if self.current_step else None

    def get_execution_progress(self) -> Dict[str, Any]:
        """获取执行进度信息"""
        return {
            'dsl_id': self.dsl_id,
            'total_steps': self.total_steps,
            'completed_steps': self.completed_steps,
            'failed_steps': self.failed_steps,
            'current_line': self.get_current_line(),
            'progress_percentage': (
                (self.completed_steps / self.total_steps * 100)
                if self.total_steps > 0 else 0),
            'execution_time': self.get_execution_time()
        }

    def get_execution_time(self) -> Optional[float]:
        """获取执行时间"""
        if self.execution_start_time:
            end_time = self.execution_end_time or time.time()
            return end_time - self.execution_start_time
        return None

    def get_steps_summary(self) -> Dict[str, Any]:
        """获取步骤执行摘要"""
        status_counts = {}
        line_ranges = []

        for step in self.steps:
            # 统计状态
            status = step.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

            # 收集行号范围
            line_ranges.append(step.line_number)

        return {
            'total_steps': len(self.steps),
            'status_counts': status_counts,
            'line_range': {
                'start': min(line_ranges) if line_ranges else None,
                'end': max(line_ranges) if line_ranges else None
            },
            'execution_time': self.get_execution_time(),
            'steps': [
                {
                    'line': step.line_number,
                    'type': step.node_type,
                    'status': step.status.value,
                    'duration': step.duration,
                    'description': step.description
                } for step in self.steps
            ]
        }

    def _log_step_to_allure(self, step: ExecutionStep):
        """将步骤信息记录到Allure报告"""
        # 不再创建额外的allure attachment，避免重复记录
        # DSL执行器中已经有专门的attachment记录行号信息
        pass

    def export_execution_report(self) -> Dict[str, Any]:
        """导出执行报告"""
        return {
            'dsl_id': self.dsl_id,
            'execution_summary': self.get_execution_progress(),
            'steps_summary': self.get_steps_summary(),
            'execution_timeline': [
                {
                    'line_number': step.line_number,
                    'node_type': step.node_type,
                    'description': step.description,
                    'status': step.status.value,
                    'start_time': step.start_time,
                    'end_time': step.end_time,
                    'duration': step.duration,
                    'error': step.error,
                    'metadata': step.metadata
                } for step in self.steps
            ]
        }


# 全局跟踪器注册表
_global_trackers: Dict[str, ExecutionTracker] = {}
_tracker_lock = threading.Lock()


def get_or_create_tracker(dsl_id: str = None) -> ExecutionTracker:
    """获取或创建执行跟踪器"""
    with _tracker_lock:
        if dsl_id is None:
            dsl_id = f"tracker_{int(time.time() * 1000)}"

        if dsl_id not in _global_trackers:
            _global_trackers[dsl_id] = ExecutionTracker(dsl_id)

        return _global_trackers[dsl_id]


def get_tracker(dsl_id: str) -> Optional[ExecutionTracker]:
    """获取指定的执行跟踪器"""
    return _global_trackers.get(dsl_id)


def remove_tracker(dsl_id: str):
    """移除执行跟踪器"""
    with _tracker_lock:
        _global_trackers.pop(dsl_id, None)


def list_active_trackers() -> List[str]:
    """列出所有活跃的跟踪器"""
    return list(_global_trackers.keys())
