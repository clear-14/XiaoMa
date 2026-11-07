import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "小码 Xiaoma",
  description: "开源、免费、个人独立部署的 AI 编程学习教练",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
