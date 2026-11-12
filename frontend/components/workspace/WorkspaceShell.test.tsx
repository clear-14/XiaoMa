import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { publishWorkspaceEvent } from "@/lib/workspace-bus";
import { loadWorkspaceSnapshot } from "@/lib/workspace-data";

import WorkspaceShell from "./WorkspaceShell";

vi.mock("./LeftRail", () => ({
  default: () => <nav data-testid="left-rail" aria-label="主导航与最近会话" />,
}));
vi.mock("./RightWorkspace", () => ({
  default: () => <aside data-testid="right-workspace" aria-label="学习工作区" />,
}));
vi.mock("./StartupGuide", () => ({ default: () => null }));
vi.mock("@/lib/workspace-data", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/workspace-data")>();
  return { ...actual, loadWorkspaceSnapshot: vi.fn() };
});

const loadMock = vi.mocked(loadWorkspaceSnapshot);

const emptySnapshot = {
  plan: { data: null, error: null },
  today: { data: null, error: null },
  knowledgePoint: { data: null, error: null },
  overview: { data: null, error: null },
  mastery: { data: null, error: null },
};

beforeEach(() => {
  loadMock.mockReset();
  loadMock.mockResolvedValue(emptySnapshot);
});

describe("V1.4 窗口三栏外壳", () => {
  it("三栏骨架始终挂载，中栏渲染当前路由内容", async () => {
    render(
      <WorkspaceShell>
        <div>当前视图内容</div>
      </WorkspaceShell>,
    );

    const shell = document.querySelector(".window-shell");
    expect(shell).not.toBeNull();
    expect(shell?.getAttribute("data-left")).toBe("expanded");
    expect(shell?.getAttribute("data-right")).toBe("expanded");
    expect(screen.getByText("当前视图内容")).toBeInTheDocument();
    expect(screen.getByTestId("left-rail")).toBeInTheDocument();
    expect(screen.getByTestId("right-workspace")).toBeInTheDocument();
    // 没有计划时如实显示，不编造进度
    expect(screen.getByText("尚未建立学习计划")).toBeInTheDocument();
    await waitFor(() => expect(loadMock).toHaveBeenCalledTimes(1));
  });

  it("左右栏可独立收起与展开", () => {
    render(<WorkspaceShell>内容</WorkspaceShell>);
    const shell = document.querySelector(".window-shell") as HTMLElement;

    fireEvent.click(screen.getByRole("button", { name: "收起左栏" }));
    expect(shell.getAttribute("data-left")).toBe("collapsed");
    fireEvent.click(screen.getByRole("button", { name: "展开左栏" }));
    expect(shell.getAttribute("data-left")).toBe("expanded");

    fireEvent.click(screen.getByRole("button", { name: "收起学习工作区" }));
    expect(shell.getAttribute("data-right")).toBe("collapsed");
    fireEvent.click(screen.getByRole("button", { name: "展开学习工作区" }));
    expect(shell.getAttribute("data-right")).toBe("expanded");
  });

  it("移动端双抽屉互斥，Escape 或遮罩可关闭", () => {
    render(<WorkspaceShell>内容</WorkspaceShell>);
    const shell = document.querySelector(".window-shell") as HTMLElement;

    fireEvent.click(screen.getByRole("button", { name: "打开导航与历史会话" }));
    expect(shell.getAttribute("data-mobile-left")).toBe("open");
    expect(screen.getByRole("button", { name: "关闭抽屉" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "打开学习工作区" }));
    expect(shell.getAttribute("data-mobile-left")).toBe("closed");
    expect(shell.getAttribute("data-mobile-right")).toBe("open");

    fireEvent.keyDown(window, { key: "Escape" });
    expect(shell.getAttribute("data-mobile-right")).toBe("closed");
  });

  it("收到业务数据变更事件时重新拉取真实面板数据", async () => {
    render(<WorkspaceShell>内容</WorkspaceShell>);
    await waitFor(() => expect(loadMock).toHaveBeenCalledTimes(1));
    publishWorkspaceEvent({ type: "panels:refresh" });
    await waitFor(() => expect(loadMock).toHaveBeenCalledTimes(2));
  });
});
