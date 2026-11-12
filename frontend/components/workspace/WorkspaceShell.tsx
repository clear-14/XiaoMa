"use client";

import { Suspense, useCallback, useEffect, useState, type ReactNode } from "react";

import { getErrorMessage } from "@/lib/api";
import { subscribeWorkspaceEvent } from "@/lib/workspace-bus";
import {
  computeLearningRuler,
  loadWorkspaceSnapshot,
  type WorkspaceSnapshot,
} from "@/lib/workspace-data";

import LeftRail from "./LeftRail";
import RightWorkspace from "./RightWorkspace";
import StartupGuide from "./StartupGuide";
import WindowTitlebar from "./WindowTitlebar";

const EMPTY_SNAPSHOT: WorkspaceSnapshot = {
  plan: { data: null, error: null },
  today: { data: null, error: null },
  knowledgePoint: { data: null, error: null },
  overview: { data: null, error: null },
  mastery: { data: null, error: null },
};

/**
 * V1.4 窗口工作区外壳：挂在 `(main)` layout 上，三栏骨架始终存在。
 *
 * 中栏只替换 children（当前路由的既有页面），辅助视图打开不会让三栏消失；
 * 左/右栏可收起，≤767px 时两者都变成抽屉。界面层不调用任何桌面壳专有接口，
 * 浏览器与移动端访问同一套代码（技术设计 §2.3、§8.3）。
 */
export default function WorkspaceShell({ children }: { children: ReactNode }) {
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);
  const [mobileLeftOpen, setMobileLeftOpen] = useState(false);
  const [mobileRightOpen, setMobileRightOpen] = useState(false);

  const [snapshot, setSnapshot] = useState<WorkspaceSnapshot>(EMPTY_SNAPSHOT);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      setSnapshot(await loadWorkspaceSnapshot());
    } catch (err) {
      setLoadError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 0);
    return () => window.clearTimeout(timer);
  }, [refresh]);

  useEffect(() => {
    return subscribeWorkspaceEvent((event) => {
      if (event.type === "panels:refresh") {
        void refresh();
      }
    });
  }, [refresh]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMobileLeftOpen(false);
        setMobileRightOpen(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const ruler = computeLearningRuler(snapshot.today.data, snapshot.plan.data);

  return (
    <div
      className="window-shell"
      data-left={leftCollapsed ? "collapsed" : "expanded"}
      data-right={rightCollapsed ? "collapsed" : "expanded"}
      data-mobile-left={mobileLeftOpen ? "open" : "closed"}
      data-mobile-right={mobileRightOpen ? "open" : "closed"}
    >
      <WindowTitlebar
        leftCollapsed={leftCollapsed}
        rightCollapsed={rightCollapsed}
        onToggleLeft={() => setLeftCollapsed((value) => !value)}
        onToggleRight={() => setRightCollapsed((value) => !value)}
        onOpenMobileLeft={() => {
          setMobileRightOpen(false);
          setMobileLeftOpen(true);
        }}
        onOpenMobileRight={() => {
          setMobileLeftOpen(false);
          setMobileRightOpen(true);
        }}
        ruler={ruler}
      />

      <div className="window-columns">
        <Suspense fallback={<nav className="window-rail" aria-label="主导航与最近会话" />}>
          <LeftRail
            collapsed={leftCollapsed}
            mobileOpen={mobileLeftOpen}
            onCollapse={() => setLeftCollapsed(true)}
            onCloseMobile={() => setMobileLeftOpen(false)}
          />
        </Suspense>

        <main className="window-main" id="window-main">
          {loadError && (
            <p className="window-load-error" role="alert">
              学习上下文读取失败：{loadError}
            </p>
          )}
          <div className="window-main-inner">{children}</div>
        </main>

        <RightWorkspace
          snapshot={snapshot}
          loading={loading}
          onRefresh={() => void refresh()}
          collapsed={rightCollapsed}
          mobileOpen={mobileRightOpen}
          onCloseMobile={() => setMobileRightOpen(false)}
          onCollapse={() => setRightCollapsed(true)}
        />
      </div>

      {(mobileLeftOpen || mobileRightOpen) && (
        <button
          type="button"
          className="window-scrim"
          aria-label="关闭抽屉"
          onClick={() => {
            setMobileLeftOpen(false);
            setMobileRightOpen(false);
          }}
        />
      )}

      <StartupGuide />
    </div>
  );
}
