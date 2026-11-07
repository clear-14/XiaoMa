import type { Metadata } from "next";
import { Suspense } from "react";

import LoadingState from "@/components/LoadingState";
import PageHeader from "@/components/PageHeader";

import WorkspaceClient from "./WorkspaceClient";

export const metadata: Metadata = { title: "AI 学习工作台 · 小码 Xiaoma" };

export default function WorkspacePage() {
  return (
    <>
      <PageHeader
        title="AI 学习工作台"
        description="围绕当前知识点与学习任务进行教学对话，历史消息自动保存"
      />
      <Suspense fallback={<LoadingState label="正在打开工作台…" />}>
        <WorkspaceClient />
      </Suspense>
    </>
  );
}
