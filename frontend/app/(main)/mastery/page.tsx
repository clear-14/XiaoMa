/** 阶段 5：掌握度总览、六维能力诊断与个性化学习路线。 */

import type { Metadata } from "next";

import PageHeader from "@/components/PageHeader";

import MasteryClient from "./MasteryClient";

export const metadata: Metadata = { title: "能力诊断 · 小码 Xiaoma" };

export default function MasteryPage() {
  return (
    <>
      <PageHeader
        title="能力诊断与掌握度"
        description="按知识点记录掌握证据：自述、练习、测验各自留痕，自述不等于掌握"
      />
      <MasteryClient />
    </>
  );
}
