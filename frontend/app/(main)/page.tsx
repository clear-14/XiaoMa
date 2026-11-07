import type { Metadata } from "next";

import PageHeader from "@/components/PageHeader";

import DashboardClient from "./DashboardClient";

export const metadata: Metadata = { title: "首页 · 小码 Xiaoma" };

export default function DashboardPage() {
  return (
    <>
      <PageHeader
        title="首页"
        description="今日学习任务与 AI 教学入口"
      />
      <DashboardClient />
    </>
  );
}
