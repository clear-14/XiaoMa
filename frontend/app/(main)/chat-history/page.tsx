import type { Metadata } from "next";

import PageHeader from "@/components/PageHeader";

import ChatHistoryClient from "./ChatHistoryClient";

export const metadata: Metadata = { title: "聊天历史 · 小码 Xiaoma" };

export default function ChatHistoryPage() {
  return (
    <>
      <PageHeader
        title="聊天历史"
        description="查看、继续或永久删除历史会话（删除后不可恢复）"
      />
      <ChatHistoryClient />
    </>
  );
}
