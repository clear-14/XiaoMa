import AccessGate from "@/components/AccessGate";
import WorkspaceShell from "@/components/workspace/WorkspaceShell";

/**
 * V1.4 批次 3：站点式 Sidebar + main 改为窗口式三栏外壳。
 *
 * 三栏骨架挂在 layout 上始终存在；children 仍是既有 10 个页面路由的渲染结果，
 * 辅助视图只替换中栏内容区，不删除任何既有页面、接口或测试（CLAUDE.md 第 5 条）。
 * 旧 Sidebar 组件保留在仓库中，供浏览器辅助通道与后续兼容使用。
 */
export default function MainLayout({ children }: LayoutProps<"/">) {
  return (
    <AccessGate>
      <WorkspaceShell>{children}</WorkspaceShell>
    </AccessGate>
  );
}
