"use client";

import { useState } from "react";

import type { WorkspaceSnapshot } from "@/lib/workspace-data";

import {
  KnowledgePanel,
  PlanPanel,
  ProgressPanel,
  TodayPanel,
} from "./WorkspacePanels";

type PanelKey = "plan" | "today" | "knowledge" | "progress";

const PANEL_TABS: { key: PanelKey; label: string; short: string }[] = [
  { key: "plan", label: "学习计划", short: "计划" },
  { key: "today", label: "今日任务", short: "任务" },
  { key: "knowledge", label: "当前知识点", short: "知识点" },
  { key: "progress", label: "学习进度", short: "进度" },
];

export interface RightWorkspaceProps {
  snapshot: WorkspaceSnapshot;
  loading: boolean;
  onRefresh: () => void;
  collapsed: boolean;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  onCollapse: () => void;
}

/**
 * 右栏学习工作区：四个面板的数据全部来自既有只读接口，
 * 面板切换只换内容不重复取数；刷新按钮与 `panels:refresh` 事件触发重新聚合。
 */
export default function RightWorkspace({
  snapshot,
  loading,
  onRefresh,
  collapsed,
  mobileOpen,
  onCloseMobile,
  onCollapse,
}: RightWorkspaceProps) {
  const [active, setActive] = useState<PanelKey>("today");

  const panelProps = { snapshot, loading, onRetry: onRefresh };

  return (
    <aside
      className="window-right"
      aria-label="学习工作区"
      aria-hidden={collapsed && !mobileOpen}
    >
      <div className="window-right-inner">
        <div className="right-head">
          <div>
            <span className="right-eyebrow">学习上下文</span>
            <h2 className="right-title">学习工作区</h2>
          </div>
          <div className="right-head-actions">
            <button
              type="button"
              className="win-icon-btn"
              aria-label="刷新面板数据"
              onClick={onRefresh}
              disabled={loading}
            >
              <svg
                viewBox="0 0 24 24"
                width="17"
                height="17"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeLinecap="round"
                aria-hidden="true"
              >
                <path d="M20 11a8 8 0 1 0-2 6" />
                <path d="M20 4v7h-7" />
              </svg>
            </button>
            <button
              type="button"
              className="win-icon-btn win-narrow-right-only"
              aria-label="关闭学习工作区"
              onClick={onCloseMobile}
            >
              ✕
            </button>
            <button
              type="button"
              className="win-icon-btn win-wide-right-only"
              aria-label="收起学习工作区"
              onClick={onCollapse}
            >
              ✕
            </button>
          </div>
        </div>

        <div className="right-tabs" role="tablist" aria-label="学习工作区面板">
          {PANEL_TABS.map((tab) => (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={active === tab.key}
              className={`right-tab${active === tab.key ? " active" : ""}`}
              onClick={() => setActive(tab.key)}
            >
              <span className="right-tab-long">{tab.label}</span>
              <span className="right-tab-short">{tab.short}</span>
            </button>
          ))}
        </div>

        <div className="right-body" role="tabpanel">
          {active === "plan" && <PlanPanel {...panelProps} />}
          {active === "today" && <TodayPanel {...panelProps} />}
          {active === "knowledge" && <KnowledgePanel {...panelProps} />}
          {active === "progress" && <ProgressPanel {...panelProps} />}
        </div>

        <p className="right-source">
          面板数据来自后端真实业务记录，不由对话内容推断。
        </p>
      </div>
    </aside>
  );
}
