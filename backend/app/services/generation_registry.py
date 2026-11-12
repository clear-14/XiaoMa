"""V1.4 生成运行注册表（进程内，单 uvicorn 进程 / 单副本前提）。

用途：``POST /conversations/{id}/messages/stop`` 只负责置位，真正落
``status=stopped`` 的部分消息由 SSE 生成器在下一次事件边界完成，避免
另一个请求直接写数据库造成竞态。

用 ``threading.Event`` 而非 ``asyncio.Event``：置位来自同步的 REST 端点
（运行在线程池），读取来自异步的 SSE 生成器（运行在事件循环），跨线程
必须线程安全。Registry 是纯内存结构，进程重启后自然清空，不需要持久化。
"""

from __future__ import annotations

import threading
import uuid


class GenerationRegistry:
    """按会话记录当前正在生成的运行标志。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active: dict[uuid.UUID, threading.Event] = {}

    def register(self, conversation_id: uuid.UUID) -> threading.Event:
        """登记一次生成；同一会话若仍有旧标志则直接覆盖（旧流已结束）。"""
        flag = threading.Event()
        with self._lock:
            self._active[conversation_id] = flag
        return flag

    def request_stop(self, conversation_id: uuid.UUID) -> bool:
        """请求停止；返回是否确实存在运行中的生成。"""
        with self._lock:
            flag = self._active.get(conversation_id)
        if flag is None:
            return False
        flag.set()
        return True

    def unregister(
        self, conversation_id: uuid.UUID, flag: threading.Event
    ) -> None:
        """流结束后清理；只删自己登记的标志，避免误删新流。"""
        with self._lock:
            if self._active.get(conversation_id) is flag:
                del self._active[conversation_id]

    def active_count(self) -> int:
        """供测试与诊断读取当前活跃生成数。"""
        with self._lock:
            return len(self._active)


generation_registry = GenerationRegistry()
