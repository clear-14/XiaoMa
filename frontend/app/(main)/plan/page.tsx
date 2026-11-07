import type { Metadata } from "next";

import EmptyState from "@/components/EmptyState";
import PageHeader from "@/components/PageHeader";

export const metadata: Metadata = { title: "学习计划 · 小码 Xiaoma" };

export default function PlanPage() {
  return (
    <>
      <PageHeader title="学习计划" description="课程章节、知识点、计划安排与历史版本" />
      <EmptyState
        title="暂无学习计划"
        description="完成基础诊断后，这里将展示为你生成的学习计划与历史版本。"
      />
    </>
  );
}
