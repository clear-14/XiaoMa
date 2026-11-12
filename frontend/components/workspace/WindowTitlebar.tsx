"use client";

import type { ReactNode } from "react";

import type { LearningRuler } from "@/lib/workspace-data";

/** 标题栏内联图标：不引入图标库依赖，纯线性、尺寸 18。 */
function Icon({ children }: { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
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

export interface WindowTitlebarProps {
  leftCollapsed: boolean;
  rightCollapsed: boolean;
  onToggleLeft: () => void;
  onToggleRight: () => void;
  onOpenMobileLeft: () => void;
  onOpenMobileRight: () => void;
  ruler: LearningRuler;
}

/**
 * 窗口标题栏（Brutally minimal）：产品名、唯一的记忆点「今日学习刻度尺」、
 * 左右栏收起与移动端抽屉入口。刻度数字全部来自后端真实计划数据，
 * 没有计划时显示「尚未建立学习计划」，绝不编造进度。
 */
export default function WindowTitlebar({
  leftCollapsed,
  rightCollapsed,
  onToggleLeft,
  onToggleRight,
  onOpenMobileLeft,
  onOpenMobileRight,
  ruler,
}: WindowTitlebarProps) {
  const percent =
    ruler.total > 0
      ? Math.min(100, Math.round((ruler.completed / ruler.total) * 100))
      : 0;

  return (
    <header className="window-titlebar">
      <div className="window-titlebar-start">
        <button
          type="button"
          className="win-icon-btn win-narrow-left-only"
          aria-label="打开导航与历史会话"
          onClick={onOpenMobileLeft}
        >
          <Icon>
            <path d="M4 6h16M4 12h16M4 18h16" />
          </Icon>
        </button>
        <button
          type="button"
          className="win-icon-btn win-wide-left-only"
          aria-label={leftCollapsed ? "展开左栏" : "收起左栏"}
          aria-expanded={!leftCollapsed}
          onClick={onToggleLeft}
        >
          <Icon>
            <path d="M4 5h16M4 12h10M4 19h16" />
            <path d={leftCollapsed ? "m17 9 3 3-3 3" : "m20 9-3 3 3 3"} />
          </Icon>
        </button>
        <span className="window-brand" aria-label="小码 Xiaoma">
          <span className="window-brand-mark" aria-hidden="true">
            小
          </span>
          <span className="window-brand-name">Xiaoma</span>
        </span>
      </div>

      <div
        className="learning-ruler"
        role="status"
        aria-label={`学习进度：${ruler.label}`}
      >
        <span className="learning-ruler-label">今日刻度</span>
        <span className="learning-ruler-track" aria-hidden="true">
          <span
            className="learning-ruler-fill"
            style={{ width: `${percent}%` }}
          />
        </span>
        <span className="learning-ruler-value">{ruler.label}</span>
      </div>

      <div className="window-titlebar-end">
        <button
          type="button"
          className="win-icon-btn win-wide-right-only"
          aria-label={rightCollapsed ? "展开学习工作区" : "收起学习工作区"}
          aria-expanded={!rightCollapsed}
          onClick={onToggleRight}
        >
          <Icon>
            <rect x="3" y="4" width="18" height="16" rx="2" />
            <path d="M14 4v16" />
            <path d={rightCollapsed ? "m12 9-3 3 3 3" : "m15 9 3 3-3 3"} />
          </Icon>
        </button>
        <button
          type="button"
          className="win-icon-btn win-narrow-right-only"
          aria-label="打开学习工作区"
          onClick={onOpenMobileRight}
        >
          <Icon>
            <rect x="3" y="4" width="18" height="16" rx="2" />
            <path d="M14 4v16" />
          </Icon>
        </button>
      </div>
    </header>
  );
}
