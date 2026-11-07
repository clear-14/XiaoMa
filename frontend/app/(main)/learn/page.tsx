import type { Metadata } from "next";

import PageHeader from "@/components/PageHeader";

import LearnClient from "./LearnClient";

export const metadata: Metadata = { title: "课程学习 · 小码 Xiaoma" };

export default function LearnPage() {
  return (
    <>
      <PageHeader
        title="课程学习"
        description="浏览课程章节与知识点，并围绕知识点向 AI 提问"
      />
      <LearnClient />
    </>
  );
}
