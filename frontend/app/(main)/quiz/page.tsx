import type { Metadata } from "next";

import PageHeader from "@/components/PageHeader";
import QuizClient from "./QuizClient";

export const metadata: Metadata = { title: "测验中心 · 小码 Xiaoma" };

export default function QuizPage() {
  return (
    <>
      <PageHeader
        title="测验中心"
        description="按知识点、章节或学习阶段生成测验；自动评分并记录掌握依据"
      />
      <QuizClient />
    </>
  );
}
