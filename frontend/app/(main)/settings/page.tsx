import type { Metadata } from "next";

import PageHeader from "@/components/PageHeader";

import SettingsClient from "./SettingsClient";

export const metadata: Metadata = { title: "系统设置 · 小码 Xiaoma" };

export default function SettingsPage() {
  return (
    <>
      <PageHeader title="系统设置" description="模型配置、访问安全与数据备份恢复" />
      <SettingsClient />
    </>
  );
}
