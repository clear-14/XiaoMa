"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { getErrorMessage } from "@/lib/api";
import {
  deleteConversation,
  listConversations,
  renameConversation,
  type ConversationSummary,
} from "@/lib/conversations";
import { formatConversationTime } from "@/lib/format";
import {
  publishWorkspaceEvent,
  subscribeWorkspaceEvent,
} from "@/lib/workspace-bus";

/** 简洁线性图标（与既有 Sidebar 同一套视觉语言，不引入图标库）。 */
function Icon({ children }: { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="17"
      height="17"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

const NAV_ITEMS: { href: string; label: string; icon: ReactNode }[] = [
  {
    href: "/",
    label: "学习工作台",
    icon: (
      <Icon>
        <path d="M3 10.5 12 3l9 7.5" />
        <path d="M5 9.5V21h14V9.5" />
      </Icon>
    ),
  },
  {
    href: "/plan",
    label: "学习计划",
    icon: (
      <Icon>
        <rect x="3" y="5" width="18" height="16" rx="2" />
        <path d="M8 3v4M16 3v4M3 11h18" />
      </Icon>
    ),
  },
  {
    href: "/learn",
    label: "课程体系",
    icon: (
      <Icon>
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
      </Icon>
    ),
  },
  {
    href: "/quiz",
    label: "测验记录",
    icon: (
      <Icon>
        <rect x="5" y="3" width="14" height="18" rx="2" />
        <path d="m9 13 2 2 4-4" />
      </Icon>
    ),
  },
  {
    href: "/mistakes",
    label: "错题本",
    icon: (
      <Icon>
        <path d="M12 3 2.5 20h19L12 3z" />
        <path d="M12 10v4.5M12 17.8v.2" />
      </Icon>
    ),
  },
  {
    href: "/profile",
    label: "学习档案",
    icon: (
      <Icon>
        <circle cx="12" cy="8" r="4" />
        <path d="M4 21c0-4 3.6-6 8-6s8 2 8 6" />
      </Icon>
    ),
  },
  {
    href: "/mastery",
    label: "能力诊断",
    icon: (
      <Icon>
        <path d="M3 20h18M6 20V11M11 20V5M16 20v-7M21 20v-4" />
      </Icon>
    ),
  },
  {
    href: "/settings",
    label: "系统设置",
    icon: (
      <Icon>
        <circle cx="12" cy="12" r="3" />
        <path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1" />
      </Icon>
    ),
  },
];

export interface LeftRailProps {
  collapsed: boolean;
  mobileOpen: boolean;
  onCollapse: () => void;
  onCloseMobile: () => void;
}

/** 左栏：新建对话、8 项辅助视图、最近会话（真实接口）、重命名与删除二次确认。 */
export default function LeftRail({
  collapsed,
  mobileOpen,
  onCollapse,
  onCloseMobile,
}: LeftRailProps) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeConversationId = searchParams.get("conversation_id");

  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const editInputRef = useRef<HTMLInputElement | null>(null);
  // Enter 与 blur 都可能触发提交，用 ref 挡住同一次编辑的重复请求
  const renameGuardRef = useRef<string | null>(null);

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
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  useEffect(() => {
    return subscribeWorkspaceEvent((event) => {
      if (event.type === "conversation:changed") {
        void load();
      }
    });
  }, [load]);

  useEffect(() => {
    if (editingId) {
      editInputRef.current?.focus();
    }
  }, [editingId]);

  const startNewChat = () => {
    onCloseMobile();
    if (pathname === "/workspace") {
      publishWorkspaceEvent({ type: "conversation:new" });
    } else {
      router.push("/workspace");
    }
  };

  const selectConversation = (id: string) => {
    onCloseMobile();
    if (pathname === "/workspace") {
      publishWorkspaceEvent({ type: "conversation:select", id });
    } else {
      router.push(
        `/workspace?conversation_id=${encodeURIComponent(id)}`,
      );
    }
  };

  const submitRename = async (id: string) => {
    if (renameGuardRef.current === id) {
      return;
    }
    const title = editTitle.trim();
    if (!title) {
      setEditingId(null);
      return;
    }
    renameGuardRef.current = id;
    setBusyId(id);
    setError(null);
    try {
      await renameConversation(id, title);
      setEditingId(null);
      publishWorkspaceEvent({ type: "conversation:changed" });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      renameGuardRef.current = null;
      setBusyId(null);
    }
  };

  const removeConversation = async (conversation: ConversationSummary) => {
    const confirmed = window.confirm(
      `确定永久删除「${conversation.title}」吗？该会话的全部消息将被删除且无法恢复；学习计划、测验与错题等独立业务数据不会被删除。`,
    );
    if (!confirmed) {
      return;
    }
    setBusyId(conversation.id);
    setError(null);
    try {
      await deleteConversation(conversation.id);
      publishWorkspaceEvent({ type: "conversation:changed" });
      publishWorkspaceEvent({
        type: "conversation:deleted",
        id: conversation.id,
      });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  };

  const isActive = (href: string) =>
    href === "/"
      ? pathname === "/"
      : pathname === href || pathname.startsWith(`${href}/`);

  return (
    <nav
      className="window-rail"
      aria-label="主导航与最近会话"
      aria-hidden={collapsed && !mobileOpen}
    >
      <div className="window-rail-inner">
        <div className="rail-head">
          <button
            type="button"
            className="btn btn-primary rail-new"
            onClick={startNewChat}
          >
            <span aria-hidden="true">＋</span> 新建对话
          </button>
          <Link
            className="rail-workspace-link"
            href="/workspace"
            onClick={onCloseMobile}
            aria-current={pathname === "/workspace" ? "page" : undefined}
          >
            <Icon>
              <path d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5c-1.5 0-2.9-.4-4.1-1L3 20l1.2-5.2A8.5 8.5 0 1 1 21 11.5z" />
            </Icon>
            <span>进入对话工作台</span>
          </Link>
        </div>

        <div className="rail-section-label">功能视图</div>
        <ul className="rail-nav">
          {NAV_ITEMS.map((item) => (
            <li key={item.href}>
              <Link
                href={item.href}
                className={`rail-nav-item${isActive(item.href) ? " active" : ""}`}
                aria-current={isActive(item.href) ? "page" : undefined}
                onClick={onCloseMobile}
              >
                {item.icon}
                <span>{item.label}</span>
              </Link>
            </li>
          ))}
        </ul>

        <div className="rail-section-label rail-section-gap">最近会话</div>
        {loading && <p className="rail-muted">正在读取会话…</p>}
        {error && (
          <div className="rail-error" role="alert">
            <span>{error}</span>
            <button type="button" className="btn btn-sm" onClick={() => void load()}>
              重试
            </button>
          </div>
        )}
        {!loading && !error && conversations.length === 0 && (
          <p className="rail-muted">暂无历史会话</p>
        )}
        <ul className="rail-conversations">
          {conversations.map((conversation) => (
            <li
              key={conversation.id}
              className={`rail-conversation${
                conversation.id === activeConversationId ? " active" : ""
              }`}
            >
              {editingId === conversation.id ? (
                <input
                  ref={editInputRef}
                  className="form-input rail-rename-input"
                  value={editTitle}
                  maxLength={120}
                  aria-label="修改会话名称"
                  onChange={(event) => setEditTitle(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      void submitRename(conversation.id);
                    } else if (event.key === "Escape") {
                      setEditingId(null);
                    }
                  }}
                  onBlur={() => void submitRename(conversation.id)}
                />
              ) : (
                <button
                  type="button"
                  className="rail-conversation-main"
                  onClick={() => selectConversation(conversation.id)}
                  title={conversation.title}
                >
                  <span className="rail-conversation-title">
                    {conversation.title}
                  </span>
                  <span className="rail-conversation-meta">
                    {conversation.message_count} 条 ·{" "}
                    {formatConversationTime(conversation.last_activity_at)}
                  </span>
                </button>
              )}
              <span className="rail-conversation-actions">
                <button
                  type="button"
                  className="rail-mini-btn"
                  aria-label={`重命名会话 ${conversation.title}`}
                  onClick={() => {
                    setEditingId(conversation.id);
                    setEditTitle(conversation.title);
                  }}
                  disabled={busyId === conversation.id}
                >
                  重命名
                </button>
                <button
                  type="button"
                  className="rail-mini-btn danger"
                  aria-label={`删除会话 ${conversation.title}`}
                  onClick={() => void removeConversation(conversation)}
                  disabled={busyId === conversation.id}
                >
                  {busyId === conversation.id ? "…" : "删除"}
                </button>
              </span>
            </li>
          ))}
        </ul>

        <button
          type="button"
          className="rail-collapse win-wide-left-only"
          onClick={onCollapse}
        >
          收起左栏
        </button>
      </div>
    </nav>
  );
}
