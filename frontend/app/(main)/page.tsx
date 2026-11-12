import type { Metadata } from "next";

import PageHeader from "@/components/PageHeader";
import WorkspaceWelcome from "@/components/workspace/WorkspaceWelcome";

import DashboardClient from "./DashboardClient";

export const metadata: Metadata = { title: "学习工作台 · 小码 Xiaoma" };

/** 窗口启动即进入工作台：欢迎区 + 真实今日任务，右侧面板同步学习上下文。 */
export default function DashboardPage() {
  return (
    <>
      <PageHeader
        title="学习工作台"
        description="今日学习任务与 AI 教学入口"
      />
      <WorkspaceWelcome />
      <DashboardClient />
    </>
  );
}
