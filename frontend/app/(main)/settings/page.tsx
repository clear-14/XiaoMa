import type { Metadata } from "next";

import EmptyState from "@/components/EmptyState";
import PageHeader from "@/components/PageHeader";

export const metadata: Metadata = { title: "系统设置 · 小码 Xiaoma" };

export default function SettingsPage() {
  return (
    <>
      <PageHeader title="系统设置" description="模型配置、访问安全与数据备份恢复" />
      <EmptyState
        title="设置功能暂未开放"
        description="模型配置、访问安全与数据备份恢复功能将在后续阶段提供。"
      />
    </>
  );
}
