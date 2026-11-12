import type { Metadata } from "next";

import PageHeader from "@/components/PageHeader";

import ProfileClient from "./ProfileClient";

export const metadata: Metadata = { title: "学习档案 · 小码 Xiaoma" };

export default function ProfilePage() {
  return (
    <>
      <PageHeader title="学习档案" description="学习目标、掌握情况、薄弱点与测验记录" />
      <ProfileClient />
    </>
  );
}
