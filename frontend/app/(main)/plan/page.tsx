import type { Metadata } from "next";

import PageHeader from "@/components/PageHeader";

import PlanClient from "./PlanClient";

export const metadata: Metadata = { title: "学习计划 · 小码 Xiaoma" };

export default function PlanPage() {
  return (
    <>
      <PageHeader title="学习计划" description="课程章节、知识点、计划安排与历史版本" />
      <PlanClient />
    </>
  );
}
