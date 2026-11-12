/**
 * V1.4 批次 5：卡片操作区组件测试。
 *
 * 覆盖真实按钮渲染、二次确认闸口、加载/成功/失败三态、答题表单校验，
 * 以及操作成功后右栏刷新事件。API 边界用 mock，业务规则用真实纯函数。
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { runCardAction } from "@/lib/card-action-runner";
import { normalizeCard, type Card, type CardType } from "@/lib/cards";
import { validEnvelope } from "@/lib/card-test-fixtures";
import { publishWorkspaceEvent } from "@/lib/workspace-bus";

import CardActions from "./CardActions";

vi.mock("@/lib/card-action-runner", () => ({ runCardAction: vi.fn() }));
vi.mock("@/lib/workspace-bus", () => ({ publishWorkspaceEvent: vi.fn() }));

function cardOf(
  type: CardType,
  extra: Record<string, unknown> = {},
): Card {
  return normalizeCard(validEnvelope(type, extra));
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(runCardAction).mockResolvedValue("操作已完成");
});

describe("按钮渲染与二次确认", () => {
  it("没有可执行动作的卡片不渲染任何按钮", () => {
    const { container } = render(<CardActions card={cardOf("lesson_card")} />);
    expect(container.firstChild).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("计划调整卡片渲染确认与放弃两个按钮", () => {
    render(<CardActions card={cardOf("plan_change_card")} />);
    expect(
      screen.getByRole("button", { name: "确认并保存调整" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "放弃调整" }),
    ).toBeInTheDocument();
  });

  it("取消二次确认后不调用任何业务接口", () => {
    const confirmSpy = vi
      .spyOn(window, "confirm")
      .mockReturnValue(false);
    render(<CardActions card={cardOf("plan_change_card")} />);
    fireEvent.click(
      screen.getByRole("button", { name: "确认并保存调整" }),
    );
    expect(confirmSpy).toHaveBeenCalledOnce();
    expect(runCardAction).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it("确认后调用真实动作并展示成功状态、刷新业务面板", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<CardActions card={cardOf("plan_change_card")} />);
    fireEvent.click(
      screen.getByRole("button", { name: "确认并保存调整" }),
    );

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("操作已完成");
    });
    expect(runCardAction).toHaveBeenCalledOnce();
    expect(publishWorkspaceEvent).toHaveBeenCalledWith({
      type: "panels:refresh",
    });
    expect(publishWorkspaceEvent).toHaveBeenCalledWith({
      type: "conversation:changed",
    });
    confirmSpy.mockRestore();
  });

  it("接口失败时明确展示失败原因，不显示为成功", async () => {
    vi.mocked(runCardAction).mockRejectedValue(
      new Error("提案已被确认，无法重复操作"),
    );
    render(<CardActions card={cardOf("quiz_result_card")} />);
    fireEvent.click(
      screen.getByRole("button", { name: "查看最新评分" }),
    );
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "提案已被确认，无法重复操作",
      );
    });
    expect(screen.queryByRole("status")).toBeNull();
    expect(publishWorkspaceEvent).not.toHaveBeenCalled();
  });

  it("请求进行中展示加载态并禁用按钮", async () => {
    let resolveAction: (value: string) => void = () => undefined;
    vi.mocked(runCardAction).mockReturnValue(
      new Promise<string>((resolve) => {
        resolveAction = resolve;
      }),
    );
    render(<CardActions card={cardOf("progress_card")} />);
    fireEvent.click(
      screen.getByRole("button", { name: "刷新进度" }),
    );
    expect(
      screen.getByRole("button", { name: "处理中…" }),
    ).toBeDisabled();

    resolveAction("已刷新");
    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("已刷新");
    });
  });
});

describe("测验答题表单", () => {
  it("题目未答完时提交按钮不可用，答完后可提交真实答案", async () => {
    render(<CardActions card={cardOf("quiz_card")} />);
    const submit = screen.getByRole("button", { name: "提交答案" });
    expect(submit).toBeDisabled();
    expect(
      screen.getByText("请完成全部题目后再提交。"),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("A. age = 18"));
    expect(submit).toBeEnabled();

    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    fireEvent.click(submit);
    await waitFor(() => {
      expect(runCardAction).toHaveBeenCalledOnce();
    });
    const [, input] = vi.mocked(runCardAction).mock.calls[0];
    expect(input?.answers).toEqual([{ question_id: "q1", answer: "A" }]);
    confirmSpy.mockRestore();
  });

  it("答题表单不展示题目卡里的正确答案与解析", () => {
    render(<CardActions card={cardOf("quiz_card")} />);
    expect(screen.queryByText(/correct_answer/)).toBeNull();
    expect(screen.queryByText(/变量名在赋值号左侧/)).toBeNull();
  });
});

describe("错题复习输入", () => {
  it("复习答案为空时按钮不可用", () => {
    render(
      <CardActions
        card={cardOf("mistake_card", { review_task_id: "review-1" })}
      />,
    );
    expect(
      screen.getByRole("button", { name: "提交复习答案" }),
    ).toBeDisabled();
  });
});
