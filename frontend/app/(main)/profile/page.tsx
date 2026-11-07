import type { Metadata } from "next";

import EmptyState from "@/components/EmptyState";
import PageHeader from "@/components/PageHeader";

export const metadata: Metadata = { title: "学习档案 · 小码 Xiaoma" };

export default function ProfilePage() {
  return (
    <>
      <PageHeader title="学习档案" description="学习目标、掌握情况、薄弱点与测验记录" />
      <EmptyState
        title="尚未建立学习档案"
        description="完成首次初始化后，这里将展示你的学习目标、掌握情况与薄弱点。"
      />
    </>
  );
}
