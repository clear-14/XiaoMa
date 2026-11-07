"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import EmptyState from "@/components/EmptyState";
import ErrorState from "@/components/ErrorState";
import LoadingState from "@/components/LoadingState";
import { getErrorMessage } from "@/lib/api";
import {
  deleteConversation,
  listConversations,
  type ConversationSummary,
} from "@/lib/conversations";
import { formatDateTime } from "@/lib/format";

export default function ChatHistoryClient() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setConversations(await listConversations());
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // 在定时回调中发起请求，避免在 effect 主体同步触发状态更新
    const timer = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  const handleDelete = async (conversation: ConversationSummary) => {
    const confirmed = window.confirm(
      `确定永久删除「${conversation.title}」吗？该会话的全部消息将被删除且无法恢复。`,
    );
    if (!confirmed) {
      return;
    }
    setDeletingId(conversation.id);
    setDeleteError(null);
    try {
      await deleteConversation(conversation.id);
      setConversations((prev) =>
        prev.filter((item) => item.id !== conversation.id),
      );
    } catch (err) {
      setDeleteError(getErrorMessage(err));
    } finally {
      setDeletingId(null);
    }
  };

  if (loading) {
    return <LoadingState label="加载聊天历史…" />;
  }

  if (error) {
    return (
      <ErrorState
        title="无法加载聊天历史"
        message={error}
        action={
          <button type="button" className="btn" onClick={() => void load()}>
            重试
          </button>
        }
      />
    );
  }

  if (conversations.length === 0) {
    return (
      <EmptyState
        title="暂无聊天记录"
        description="与 AI 的对话记录将保存在这里，可随时查看、继续或永久删除。"
        action={
          <Link className="btn btn-primary" href="/workspace">
            新建对话
          </Link>
        }
      />
    );
  }

  return (
    <>
      <div className="history-toolbar">
        <span className="muted">共 {conversations.length} 个会话</span>
        <Link className="btn btn-primary btn-sm" href="/workspace">
          新建对话
        </Link>
      </div>

      {deleteError && (
        <div className="inline-error" role="alert">
          <span>{deleteError}</span>
          <button
            type="button"
            className="btn btn-sm"
            onClick={() => setDeleteError(null)}
          >
            关闭
          </button>
        </div>
      )}

      <ul className="history-list">
        {conversations.map((conversation) => (
          <li key={conversation.id} className="history-item card">
            <Link
              className="history-main"
              href={`/workspace?conversation_id=${encodeURIComponent(
                conversation.id,
              )}`}
            >
              <span className="history-title">{conversation.title}</span>
              <span className="history-meta">
                {conversation.knowledge_point
                  ? `${conversation.knowledge_point.chapter_title} · ${conversation.knowledge_point.name}`
                  : "通用问答"}
                {" · "}
                {conversation.message_count} 条消息
              </span>
              <span className="history-time">
                最近活动：{formatDateTime(conversation.last_activity_at)}
              </span>
            </Link>
            <div className="history-actions">
              <Link
                className="btn btn-sm"
                href={`/workspace?conversation_id=${encodeURIComponent(
                  conversation.id,
                )}`}
              >
                继续对话
              </Link>
              <button
                type="button"
                className="btn btn-sm btn-danger"
                onClick={() => void handleDelete(conversation)}
                disabled={deletingId === conversation.id}
              >
                {deletingId === conversation.id ? "删除中…" : "永久删除"}
              </button>
            </div>
          </li>
        ))}
      </ul>
    </>
  );
}
