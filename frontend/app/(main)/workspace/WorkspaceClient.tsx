"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";

import ErrorState from "@/components/ErrorState";
import LoadingState from "@/components/LoadingState";
import { ApiError, getErrorMessage } from "@/lib/api";
import {
  createConversation,
  deleteConversation,
  getConversation,
  listConversations,
  streamMessage,
  type ConversationMessage,
  type ConversationSummary,
} from "@/lib/conversations";
import { formatConversationTime } from "@/lib/format";
import {
  getKnowledgePoint,
  getTaskDetail,
  type DailyTask,
  type KnowledgePointDetail,
} from "@/lib/learning";
import type { MessageRole } from "@/lib/types";

interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  status: "completed" | "error" | "streaming";
  errorMessage?: string | null;
  modelName?: string | null;
}

interface DraftContext {
  taskId?: string;
  knowledgePointCode?: string;
  task?: DailyTask;
  knowledgePoint?: KnowledgePointDetail;
}

function toChatMessage(message: ConversationMessage): ChatMessage {
  return {
    id: message.id,
    role: message.role,
    content: message.content,
    status: message.status === "error" ? "error" : "completed",
    errorMessage: message.error_message,
    modelName: message.model_name,
  };
}

export default function WorkspaceClient() {
  const searchParams = useSearchParams();
  const conversationParam = searchParams.get("conversation_id");
  const taskParam = searchParams.get("daily_task_id");
  const knowledgePointParam = searchParams.get("knowledge_point_code");
  const paramKey = `${conversationParam ?? ""}|${taskParam ?? ""}|${knowledgePointParam ?? ""}`;

  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const [activeId, setActiveId] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [activeTitle, setActiveTitle] = useState("新对话");
  const [activeKnowledgePoint, setActiveKnowledgePoint] = useState<{
    name: string;
    chapter_title: string;
  } | null>(null);

  const [draftContext, setDraftContext] = useState<DraftContext | null>(null);
  const [contextLoading, setContextLoading] = useState(false);
  const [contextError, setContextError] = useState<string | null>(null);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [streamErrorStatus, setStreamErrorStatus] = useState<number | null>(null);

  const detailRequestRef = useRef(0);
  const streamControllerRef = useRef<AbortController | null>(null);
  const messageListRef = useRef<HTMLDivElement | null>(null);
  // 同步记录当前会话 ID：Next.js 会同步 history.replaceState 引起的查询参数变化，
  // 用于区分“URL 刚切换到自己”与“用户切换到其他会话”
  const activeIdRef = useRef<string | null>(null);
  // 清理“刚创建但未保存任何消息”的会话时，跳过随之而来的查询参数重置，
  // 以保留当前错误提示与恢复的上下文
  const skipNextParamResetRef = useRef(false);

  const loadConversations = useCallback(async () => {
    setListLoading(true);
    setListError(null);
    try {
      setConversations(await listConversations());
    } catch (err) {
      setListError(getErrorMessage(err));
    } finally {
      setListLoading(false);
    }
  }, []);

  const refreshConversationList = useCallback(async () => {
    try {
      setConversations(await listConversations());
      setListError(null);
    } catch (err) {
      setListError(getErrorMessage(err));
    }
  }, []);

  const loadConversation = useCallback(async (id: string) => {
    const requestId = ++detailRequestRef.current;
    activeIdRef.current = id;
    setActiveId(id);
    setActiveKnowledgePoint(null);
    setDetailLoading(true);
    setDetailError(null);
    try {
      const data = await getConversation(id);
      if (detailRequestRef.current !== requestId) {
        return;
      }
      setActiveId(data.id);
      setActiveTitle(data.title);
      setActiveKnowledgePoint(
        data.knowledge_point
          ? {
              name: data.knowledge_point.name,
              chapter_title: data.knowledge_point.chapter_title,
            }
          : null,
      );
      setMessages(data.messages.map(toChatMessage));
      setDraftContext(null);
      setContextError(null);
    } catch (err) {
      if (detailRequestRef.current !== requestId) {
        return;
      }
      setDetailError(getErrorMessage(err));
      setMessages([]);
    } finally {
      if (detailRequestRef.current === requestId) {
        setDetailLoading(false);
      }
    }
  }, []);

  const loadDraftContext = useCallback(
    async (taskId: string | null, kpCode: string | null) => {
      setDraftContext(null);
      setContextError(null);
      if (!taskId && !kpCode) {
        return;
      }
      setContextLoading(true);
      try {
        const [task, knowledgePoint] = await Promise.all([
          taskId ? getTaskDetail(taskId) : Promise.resolve(null),
          kpCode ? getKnowledgePoint(kpCode) : Promise.resolve(null),
        ]);
        if (
          task &&
          knowledgePoint &&
          task.knowledge_point.code !== knowledgePoint.code
        ) {
          setContextError(
            "每日任务与知识点不匹配，请从对应的任务或知识点入口重新进入",
          );
          return;
        }
        setDraftContext({
          taskId: task?.id,
          knowledgePointCode:
            knowledgePoint?.code ?? task?.knowledge_point.code,
          task: task ?? undefined,
          knowledgePoint: knowledgePoint ?? undefined,
        });
      } catch (err) {
        setContextError(getErrorMessage(err));
      } finally {
        setContextLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    // 在定时回调中发起请求，避免在 effect 主体同步触发状态更新
    const timer = window.setTimeout(() => {
      void loadConversations();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadConversations]);

  useEffect(() => {
    // URL 查询参数变化时切换上下文；定时回调避免 effect 主体同步更新状态
    const timer = window.setTimeout(() => {
      if (skipNextParamResetRef.current) {
        skipNextParamResetRef.current = false;
        return;
      }
      if (conversationParam) {
        // 新建会话后 replaceState 也会让查询参数变化；此时局部消息流正在渲染，
        // 不能重新拉取尚未包含 AI 回复的详情，否则会清掉流式占位消息
        if (conversationParam === activeIdRef.current) {
          return;
        }
        void loadConversation(conversationParam);
        return;
      }
      activeIdRef.current = null;
      detailRequestRef.current += 1;
      setActiveId(null);
      setActiveTitle("新对话");
      setActiveKnowledgePoint(null);
      setDetailLoading(false);
      setDetailError(null);
      setMessages([]);
      setStreamError(null);
      setStreamErrorStatus(null);
      void loadDraftContext(taskParam, knowledgePointParam);
    }, 0);
    return () => window.clearTimeout(timer);
  }, [
    paramKey,
    conversationParam,
    taskParam,
    knowledgePointParam,
    loadConversation,
    loadDraftContext,
  ]);

  useEffect(() => {
    return () => {
      streamControllerRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    const element = messageListRef.current;
    if (element) {
      element.scrollTop = element.scrollHeight;
    }
  }, [messages]);

  const startNewChat = () => {
    if (sending) {
      return;
    }
    detailRequestRef.current += 1;
    activeIdRef.current = null;
    setActiveId(null);
    setActiveTitle("新对话");
    setActiveKnowledgePoint(null);
    setDetailLoading(false);
    setDetailError(null);
    setMessages([]);
    setDraftContext(null);
    setContextLoading(false);
    setContextError(null);
    setDraft("");
    setStreamError(null);
    setStreamErrorStatus(null);
    window.history.replaceState(null, "", "/workspace");
  };

  const selectConversation = (id: string) => {
    if (sending || id === activeId) {
      return;
    }
    setStreamError(null);
    setStreamErrorStatus(null);
    window.history.replaceState(
      null,
      "",
      `/workspace?conversation_id=${encodeURIComponent(id)}`,
    );
    void loadConversation(id);
  };

  const updateTitle = (id: string, title: string) => {
    // 流式回复只会更新当前会话，直接同步标题，避免闭包中的 activeId 滞后
    setActiveTitle(title);
    setConversations((prev) =>
      prev.map((item) => (item.id === id ? { ...item, title } : item)),
    );
  };

  const updateMessageCount = (id: string, count: number) => {
    setConversations((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, message_count: count } : item,
      ),
    );
  };

  const handleDelete = async (conversation: ConversationSummary) => {
    if (sending) {
      return;
    }
    const confirmed = window.confirm(
      `确定永久删除「${conversation.title}」吗？该会话的全部消息将被删除且无法恢复。`,
    );
    if (!confirmed) {
      return;
    }
    setDeletingId(conversation.id);
    setListError(null);
    try {
      await deleteConversation(conversation.id);
      setConversations((prev) =>
        prev.filter((item) => item.id !== conversation.id),
      );
      if (activeId === conversation.id) {
        startNewChat();
      }
    } catch (err) {
      setListError(getErrorMessage(err));
    } finally {
      setDeletingId(null);
    }
  };

  const handleSend = async () => {
    const content = draft.trim();
    if (
      !content ||
      sending ||
      detailLoading ||
      contextLoading ||
      contextError
    ) {
      return;
    }

    setSending(true);
    setStreamError(null);
    setStreamErrorStatus(null);

    const controller = new AbortController();
    streamControllerRef.current = controller;

    const userLocalId = `local-user-${Date.now()}`;
    const assistantLocalId = `local-assistant-${Date.now()}`;
    const pendingContext = draftContext;
    let conversationId = activeId;
    let createdConversationId: string | null = null;
    let streamedText = "";
    let errorEventMessage: string | null = null;
    let finished = false;

    try {
      if (!conversationId) {
        try {
          const created = await createConversation({
            knowledge_point_code: draftContext?.knowledgePointCode,
            daily_task_id: draftContext?.taskId,
          });
          conversationId = created.id;
          createdConversationId = created.id;
          activeIdRef.current = created.id;
          setActiveId(created.id);
          setActiveTitle(created.title);
          setActiveKnowledgePoint(
            created.knowledge_point
              ? {
                  name: created.knowledge_point.name,
                  chapter_title: created.knowledge_point.chapter_title,
                }
              : null,
          );
          setMessages([]);
          setDraftContext(null);
          window.history.replaceState(
            null,
            "",
            `/workspace?conversation_id=${encodeURIComponent(created.id)}`,
          );
          setConversations((prev) => [created, ...prev]);
        } catch (err) {
          setStreamError(getErrorMessage(err));
          setStreamErrorStatus(err instanceof ApiError ? err.status : null);
          return;
        }
      }

      setMessages((prev) => [
        ...prev,
        {
          id: userLocalId,
          role: "user",
          content,
          status: "completed",
        },
        {
          id: assistantLocalId,
          role: "assistant",
          content: "",
          status: "streaming",
        },
      ]);
      setDraft("");

      const targetId = conversationId;
      await streamMessage(
        targetId,
        content,
        {
          onStart: (info) => {
            if (info.title) {
              updateTitle(targetId, info.title);
            }
            if (info.model) {
              setMessages((prev) =>
                prev.map((message) =>
                  message.id === assistantLocalId
                    ? { ...message, modelName: info.model }
                    : message,
                ),
              );
            }
          },
          onDelta: (text) => {
            streamedText += text;
            setMessages((prev) =>
              prev.map((message) =>
                message.id === assistantLocalId
                  ? { ...message, content: streamedText }
                  : message,
              ),
            );
          },
          onDone: (info) => {
            finished = true;
            setMessages((prev) =>
              prev.map((message) =>
                message.id === assistantLocalId
                  ? { ...message, content: streamedText, status: "completed" }
                  : message,
              ),
            );
            if (info.title) {
              updateTitle(targetId, info.title);
            }
            if (typeof info.message_count === "number") {
              updateMessageCount(targetId, info.message_count);
            }
            void refreshConversationList();
          },
          onError: (info) => {
            errorEventMessage = info.message;
          },
        },
        controller.signal,
      );

      if (!finished) {
        const reason = errorEventMessage ?? "连接中断，回复可能未完整保存";
        setStreamError(reason);
        setMessages((prev) =>
          prev.map((message) =>
            message.id === assistantLocalId
              ? {
                  ...message,
                  status: "error",
                  content: streamedText,
                  errorMessage: reason,
                }
              : message,
          ),
        );
        // 后端已保存失败回复；重新拉取历史，展示真实的持久化状态
        void loadConversation(targetId);
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        return;
      }
      if (err instanceof ApiError && err.status > 0) {
        // 流开始前被拒绝（如未配置默认模型）：后端未保存本轮消息，回滚并恢复输入
        let cleanupFailed = false;
        if (createdConversationId) {
          // 本轮刚创建的会话还没有任何消息，避免留下空的「新对话」记录
          try {
            await deleteConversation(createdConversationId);
          } catch {
            cleanupFailed = true;
          }
          setConversations((prev) =>
            prev.filter((item) => item.id !== createdConversationId),
          );
          activeIdRef.current = null;
          detailRequestRef.current += 1;
          setActiveId(null);
          setActiveTitle("新对话");
          setActiveKnowledgePoint(null);
          setMessages([]);
          setDraftContext(pendingContext);
          const query = pendingContext?.taskId
            ? `?daily_task_id=${encodeURIComponent(pendingContext.taskId)}`
            : pendingContext?.knowledgePointCode
              ? `?knowledge_point_code=${encodeURIComponent(
                  pendingContext.knowledgePointCode,
                )}`
              : "";
          skipNextParamResetRef.current = true;
          window.history.replaceState(null, "", `/workspace${query}`);
        } else {
          setMessages((prev) =>
            prev.filter(
              (message) =>
                message.id !== userLocalId && message.id !== assistantLocalId,
            ),
          );
        }
        setDraft(content);
        setStreamError(
          cleanupFailed
            ? `${getErrorMessage(err)}（临时会话清理失败，可在聊天历史中删除）`
            : getErrorMessage(err),
        );
        setStreamErrorStatus(err.status);
      } else {
        const reason = getErrorMessage(err);
        setStreamError(reason);
        setStreamErrorStatus(null);
        setMessages((prev) =>
          prev.map((message) =>
            message.id === assistantLocalId
              ? {
                  ...message,
                  status: "error",
                  content: streamedText,
                  errorMessage: reason,
                }
              : message,
          ),
        );
      }
    } finally {
      streamControllerRef.current = null;
      if (!controller.signal.aborted) {
        setSending(false);
      }
    }
  };

  const handleComposerKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault();
      void handleSend();
    }
  };

  const activeContext = draftContext?.task
    ? {
        name: draftContext.task.knowledge_point.name,
        chapterTitle: draftContext.task.knowledge_point.chapter_title,
        goal: draftContext.task.knowledge_point.learning_goal,
      }
    : draftContext?.knowledgePoint
      ? {
          name: draftContext.knowledgePoint.name,
          chapterTitle: draftContext.knowledgePoint.chapter.title,
          goal: draftContext.knowledgePoint.learning_goal,
        }
      : null;

  const headerSubtitle = activeKnowledgePoint
    ? `${activeKnowledgePoint.chapter_title} · ${activeKnowledgePoint.name}`
    : activeContext
      ? `${activeContext.chapterTitle} · ${activeContext.name}`
      : "通用问答";

  const sendDisabled =
    sending ||
    !draft.trim() ||
    detailLoading ||
    Boolean(detailError) ||
    contextLoading ||
    Boolean(contextError);

  return (
    <div className="workspace-layout">
      <aside className="conversation-panel card" aria-label="会话列表">
        <div className="conversation-panel-head">
          <h2 className="section-title">会话</h2>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={startNewChat}
            disabled={sending}
          >
            新建对话
          </button>
        </div>

        {listLoading && conversations.length === 0 && (
          <LoadingState label="加载会话…" />
        )}
        {listError && (
          <div className="inline-error" role="alert">
            <span>{listError}</span>
            <button
              type="button"
              className="btn btn-sm"
              onClick={() => void loadConversations()}
            >
              重试
            </button>
          </div>
        )}
        {!listLoading && conversations.length === 0 && !listError && (
          <p className="muted conversation-empty">暂无历史会话</p>
        )}

        <ul className="conversation-list">
          {conversations.map((conversation) => (
            <li
              key={conversation.id}
              className={`conversation-item${
                conversation.id === activeId ? " active" : ""
              }`}
            >
              <button
                type="button"
                className="conversation-main"
                onClick={() => selectConversation(conversation.id)}
                disabled={sending}
              >
                <span className="conversation-title">{conversation.title}</span>
                <span className="conversation-meta">
                  {conversation.knowledge_point
                    ? conversation.knowledge_point.name
                    : "通用问答"}
                  {" · "}
                  {conversation.message_count} 条消息
                </span>
                <span className="conversation-time">
                  {formatConversationTime(conversation.last_activity_at)}
                </span>
              </button>
              <button
                type="button"
                className="conversation-delete"
                aria-label={`永久删除会话 ${conversation.title}`}
                title="永久删除"
                onClick={() => void handleDelete(conversation)}
                disabled={sending || deletingId === conversation.id}
              >
                {deletingId === conversation.id ? "删除中…" : "删除"}
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <section className="chat-panel card" aria-label="教学对话">
        <header className="chat-head">
          <div>
            <h2 className="chat-title">{activeTitle}</h2>
            <p className="chat-subtitle">{headerSubtitle}</p>
          </div>
          {sending && <span className="status-pill">AI 正在回复…</span>}
        </header>

        {contextLoading && <LoadingState label="正在读取学习上下文…" />}

        {!activeId && activeContext && !contextLoading && (
          <div className="context-card">
            <span className="context-label">本次对话上下文</span>
            <strong className="context-name">{activeContext.name}</strong>
            <span className="context-meta">{activeContext.chapterTitle}</span>
            <p className="context-goal">{activeContext.goal}</p>
          </div>
        )}

        {contextError && (
          <div className="inline-error" role="alert">
            <span>{contextError}</span>
            <button
              type="button"
              className="btn btn-sm"
              onClick={() => {
                setDraftContext(null);
                setContextError(null);
                window.history.replaceState(null, "", "/workspace");
              }}
            >
              不带上下文新对话
            </button>
          </div>
        )}

        {detailLoading ? (
          <LoadingState label="加载对话…" />
        ) : detailError ? (
          <ErrorState
            title="无法打开会话"
            message={detailError}
            action={
              <div className="row-actions">
                {activeId && (
                  <button
                    type="button"
                    className="btn btn-sm"
                    onClick={() => void loadConversation(activeId)}
                  >
                    重试
                  </button>
                )}
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={startNewChat}
                >
                  新建对话
                </button>
              </div>
            }
          />
        ) : (
          <>
            <div className="chat-messages" ref={messageListRef} role="log">
              {messages.length === 0 ? (
                <div className="chat-placeholder">
                  <h3>开始一段新的教学对话</h3>
                  <p>
                    AI 会结合你的学习档案与当前知识点进行概念解释、分步骤讲解、举例、代码解释和报错分析。V1.0
                    不会执行你提交的代码。
                  </p>
                </div>
              ) : (
                messages.map((message) => (
                  <article
                    key={message.id}
                    className={`message message-${message.role}${
                      message.status === "error" ? " message-failed" : ""
                    }`}
                  >
                    <div className="message-role">
                      {message.role === "user" ? "你" : "小码"}
                      {message.role === "assistant" && message.modelName && (
                        <span className="message-model">{message.modelName}</span>
                      )}
                    </div>
                    <div className="message-bubble">
                      {message.status === "error" && (
                        <span className="message-error-label">回复失败</span>
                      )}
                      {message.content ? (
                        <div className="message-text">{message.content}</div>
                      ) : message.status === "streaming" ? (
                        <div className="message-text muted">正在生成…</div>
                      ) : message.status === "error" ? (
                        <div className="message-text muted">
                          （未生成任何内容）
                        </div>
                      ) : null}
                      {message.status === "streaming" && message.content && (
                        <span className="stream-cursor" aria-hidden="true">
                          ▍
                        </span>
                      )}
                      {message.status === "error" && message.errorMessage && (
                        <div className="message-error-detail">
                          {message.errorMessage}
                        </div>
                      )}
                    </div>
                  </article>
                ))
              )}
            </div>

            <div className="chat-composer">
              {streamError && (
                <div className="stream-error" role="alert">
                  <div className="stream-error-text">{streamError}</div>
                  <div className="stream-error-actions">
                    {streamErrorStatus === 409 && (
                      <Link className="btn btn-sm" href="/settings">
                        前往系统设置
                      </Link>
                    )}
                    {activeId && (
                      <button
                        type="button"
                        className="btn btn-sm"
                        onClick={() => void loadConversation(activeId)}
                        disabled={sending}
                      >
                        重新加载会话
                      </button>
                    )}
                  </div>
                </div>
              )}
              <textarea
                className="form-textarea chat-input"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={handleComposerKeyDown}
                placeholder="围绕当前知识点提问，例如：这个概念是什么意思？能分步骤讲解吗？"
                rows={4}
                maxLength={20000}
                disabled={sending || detailLoading || Boolean(detailError)}
              />
              <div className="composer-foot">
                <span className="form-hint">
                  Enter 发送 · Shift + Enter 换行 · V1.0 不执行代码
                </span>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => void handleSend()}
                  disabled={sendDisabled}
                >
                  {sending ? "生成中…" : "发送"}
                </button>
              </div>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
