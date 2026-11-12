"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getProfile } from "@/lib/profile";

/**
 * 工作台欢迎区（PRD §4.2）：非首次启动恢复最近工作区后，
 * 给用户一个明确的「今天学什么 / 从哪里继续」入口。
 * 用户名来自真实档案接口；读取失败时退化为不含用户名的通用文案，
 * 不编造任何学习数据（今日任务由下方 DashboardClient 与右栏真实接口展示）。
 */
export default function WorkspaceWelcome() {
  const [username, setUsername] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      try {
        const profile = await getProfile();
        if (!cancelled) setUsername(profile.username);
      } catch {
        // 档案不可用时保持通用文案，不阻塞工作台
      }
    }, 0);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, []);

  return (
    <section className="workspace-welcome" aria-labelledby="welcome-title">
      <div className="workspace-welcome-copy">
        <span className="workspace-welcome-eyebrow">今日学习工作台</span>
        <h2 id="welcome-title" className="workspace-welcome-title">
          {username ? `欢迎回来，${username}` : "欢迎回来"}
        </h2>
        <p className="workspace-welcome-desc">
          下面的今日任务来自你的学习计划；右侧面板同步显示计划、当前知识点与学习进度。
          想直接提问，进入对话工作台即可。
        </p>
      </div>
      <div className="workspace-welcome-actions">
        <Link className="btn btn-primary" href="/workspace">
          进入对话工作台
        </Link>
        <Link className="btn" href="/plan">
          查看学习计划
        </Link>
      </div>
    </section>
  );
}
