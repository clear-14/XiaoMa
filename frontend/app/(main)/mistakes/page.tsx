import type { Metadata } from "next";

import PageHeader from "@/components/PageHeader";
import MistakesClient from "./MistakesClient";

export const metadata: Metadata = { title: "错题本 · 小码 Xiaoma" };

export default function MistakesPage() {
  return (
    <>
      <PageHeader
        title="错题本"
        description="收录测验错题，保留解析与评分依据，并按间隔安排复习"
      />
      <MistakesClient />
    </>
  );
}
