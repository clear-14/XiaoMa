import Sidebar from "@/components/Sidebar";

export default function MainLayout({ children }: LayoutProps<"/">) {
  return (
    <div className="shell">
      <Sidebar />
      <main className="shell-main">
        <div className="shell-inner">{children}</div>
      </main>
    </div>
  );
}
