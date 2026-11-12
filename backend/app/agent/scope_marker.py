"""超范围回复的结构化标记过滤器（V1.4 批次 8）。

问题：会话绑定某个知识点时，用户问了别的主题，模型会先声明「不在本次范围内」
再引导；这类回复不是讲解正文，不该下发 ``lesson_card``。用中文关键词去猜回复
性质不可靠（口径随模型措辞漂移），所以改用提示词协议：模型在正文最前面单独
输出一行 ``[[out_of_scope]]``。

本过滤器负责三件事：

1. 把标记从流式增量里剥掉 —— 用户界面与聊天记录都不该看到它；
2. 标记可能跨多个增量（模型会分片输出 ``[[out_`` + ``of_scope]]``），
   在判定完成前先缓冲，判定为「不是标记」时原样补发，不丢字；
3. 给出 ``out_of_scope`` 这一结构化信号，供 ``finalize`` 决定是否发讲解卡片。

标记只认回复最前面的位置；出现在正文中间的同名字样按普通文本处理，不做语义猜测。
"""

from __future__ import annotations

from collections.abc import Callable

MARKER = "[[out_of_scope]]"

Emit = Callable[[dict[str, str]], None]


class ScopeMarkerFilter:
    """把流式增量转发给下游，同时剥离开头的范围标记并给出判定。"""

    def __init__(self, emit: Emit) -> None:
        self._emit = emit
        self._pending = ""
        self._decided = False
        self._skip_leading_blank = False
        # 已下发（即去掉标记后）的正文，供上层作为最终 reply 使用。
        self.text = ""
        # 模型是否把本轮判定为「先说明范围再回答」。
        self.out_of_scope = False

    def feed(self, delta: str) -> None:
        """接收一个模型增量；判定未完成时先缓冲，完成后再转发。"""
        if not delta:
            return
        if self._decided:
            self._write(delta)
            return

        self._pending += delta
        pending = self._pending

        if MARKER.startswith(pending):
            if pending == MARKER:
                # 正好是标记本身，正文还没到；先定判定，等后续增量。
                self._pending = ""
                self._decided = True
                self.out_of_scope = True
                self._skip_leading_blank = True
            return

        if pending.startswith(MARKER):
            self._pending = ""
            self._decided = True
            self.out_of_scope = True
            self._skip_leading_blank = True
            self._write(pending[len(MARKER) :])
            return

        # 开头不是标记：原样补发，之后不再判定。
        self._pending = ""
        self._decided = True
        self._write(pending)

    def feed_event(self, event: dict[str, str]) -> None:
        """适配 LangGraph writer 的事件形状 ``{"delta": str}``。"""
        self.feed(str(event.get("delta", "")))

    def flush(self) -> None:
        """流结束时补发未决缓冲（例如模型只输出了 ``[[out`` 就结束）。"""
        if self._decided or not self._pending:
            return
        pending, self._pending = self._pending, ""
        self._decided = True
        self._write(pending)

    def _write(self, text: str) -> None:
        if not text:
            return
        if self._skip_leading_blank:
            # 标记后面紧跟的换行与空白不属于正文，去掉；只处理开头这一次。
            stripped = text.lstrip()
            if not stripped:
                return
            self._skip_leading_blank = False
            text = stripped
        self.text += text
        self._emit({"delta": text})
