import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api";
import {
  completeDailyTask,
  generateTodayTasks,
  getTodayTasks,
  startDailyTask,
} from "@/lib/learning";
import { createPlacementQuiz, deleteSelfStudyTask } from "@/lib/study";
import type { TodayTasks } from "@/lib/types";

import DashboardClient from "./DashboardClient";

const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("@/lib/learning", () => ({
  getTodayTasks: vi.fn(),
  generateTodayTasks: vi.fn(),
  startDailyTask: vi.fn(),
  completeDailyTask: vi.fn(),
}));

vi.mock("@/lib/study", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/study")>();
  return {
    ...actual,
    createPlacementQuiz: vi.fn(),
    deleteSelfStudyTask: vi.fn(),
  };
});

const readMock = vi.mocked(getTodayTasks);
const generateMock = vi.mocked(generateTodayTasks);
const startMock = vi.mocked(startDailyTask);
const completeMock = vi.mocked(completeDailyTask);
const verifyMock = vi.mocked(createPlacementQuiz);
const withdrawMock = vi.mocked(deleteSelfStudyTask);

const TASK = {
  id: "task-1",
  plan_id: "plan-1",
  task_date: "2026-11-08",
  day_index: 1,
  status: "pending" as const,
  started_at: null,
  completed_at: null,
  knowledge_point: {
    code: "python-basics-01-01",
    name: "什么是编程与 Python",
    learning_goal: "了解程序与 Python 的基本关系",
    difficulty: "beginner",
    estimated_minutes: 30,
    mastery_criteria: "能说出解释型语言的特点",
    chapter_code: "python-basics-01",
    chapter_title: "第一章 初识 Python",
    resources: null,
    prerequisite_codes: [],
  },
  course_refs: {
    course_id: "course-1",
    module_id: "module-1",
    lesson_id: "lesson-1",
    knowledge_point_id: "kp-1",
    course_code: "python-basics",
    module_code: "python-basics-01",
    lesson_code: "python-basics-01-lesson-01",
    knowledge_point_code: "python-basics-01-01",
    lesson_title: "从零开始认识编程",
  },
  mastery_status: "not_started",
  mastery_evidence_count: 0,
  completion_note: null,
};

const SELF_TASK = {
  ...TASK,
  id: "task-self",
  plan_id: null,
  day_index: 0,
  source: "self_selected" as const,
  knowledge_point: {
    ...TASK.knowledge_point,
    code: "python-basics-06-03",
    name: "数据结构综合运用",
  },
};

const EMPTY: TodayTasks = {
  task_date: "2026-11-08",
  generated: false,
  tasks: [],
  note: "当天还没有生成学习任务",
};

beforeEach(() => {
  readMock.mockReset();
  generateMock.mockReset();
  startMock.mockReset();
  completeMock.mockReset();
  verifyMock.mockReset();
  withdrawMock.mockReset();
  pushMock.mockReset();
});

describe("DashboardClient 今日任务两步走（阶段 6）", () => {
  it("当天已有任务时只读不生成，并展示真实课时与掌握证据", async () => {
    readMock.mockResolvedValue({
      task_date: "2026-11-08",
      generated: false,
      tasks: [TASK],
      note: null,
    });

    render(<DashboardClient />);

    expect(await screen.findByText("什么是编程与 Python")).toBeInTheDocument();
    await waitFor(() => {
      expect(readMock).toHaveBeenCalledWith(false);
    });
    expect(generateMock).not.toHaveBeenCalled();
    expect(screen.getByText(/教材课时：从零开始认识编程/)).toBeInTheDocument();
    expect(
      screen.getByText(
        (_, element) =>
          element?.tagName === "SPAN" &&
          (element.textContent ?? "").includes("证据 0 条"),
      ),
    ).toHaveTextContent("掌握：未开始");
  });

  it("当天没有任务时才调用幂等生成接口", async () => {
    readMock.mockResolvedValue(EMPTY);
    generateMock.mockResolvedValue({
      task_date: "2026-11-08",
      generated: true,
      tasks: [TASK],
      note: null,
    });

    render(<DashboardClient />);

    expect(await screen.findByText("什么是编程与 Python")).toBeInTheDocument();
    expect(readMock).toHaveBeenCalledTimes(1);
    expect(readMock).toHaveBeenCalledWith(false);
    expect(generateMock).toHaveBeenCalledTimes(1);
  });

  it("没有学习计划时显示空状态，且不触发生成", async () => {
    readMock.mockRejectedValue(new ApiError(404, "暂无学习计划，请先创建"));

    render(<DashboardClient />);

    expect(await screen.findByText("暂无学习计划")).toBeInTheDocument();
    expect(generateMock).not.toHaveBeenCalled();
  });

  it("生成后仍无任务时展示后端返回的说明", async () => {
    readMock.mockResolvedValue(EMPTY);
    generateMock.mockResolvedValue({
      task_date: "2026-11-08",
      generated: false,
      tasks: [],
      note: "当前计划的全部知识点已完成或已掌握",
    });

    render(<DashboardClient />);

    expect(
      await screen.findByText("当前计划的全部知识点已完成或已掌握"),
    ).toBeInTheDocument();
    expect(generateMock).toHaveBeenCalledTimes(1);
  });
});

describe("DashboardClient 自主选题（阶段 7）", () => {
  it("只有自选任务时仍会生成当天的计划任务，两类并存", async () => {
    readMock.mockResolvedValue({
      task_date: "2026-11-08",
      generated: false,
      tasks: [SELF_TASK],
      plan_tasks: [],
      self_selected_tasks: [SELF_TASK],
      note: null,
    });
    generateMock.mockResolvedValue({
      task_date: "2026-11-08",
      generated: true,
      tasks: [TASK, SELF_TASK],
      plan_tasks: [TASK],
      self_selected_tasks: [SELF_TASK],
      note: null,
    });

    render(<DashboardClient />);

    expect(await screen.findByText("什么是编程与 Python")).toBeInTheDocument();
    expect(generateMock).toHaveBeenCalledTimes(1);
    expect(screen.getByText("数据结构综合运用")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "我自己选的" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "按计划安排" }),
    ).toBeInTheDocument();
  });

  it("已学完的任务显示「测一测」，点击后跳转诊断测验", async () => {
    const completed = {
      ...TASK,
      status: "completed" as const,
      progress_label: "已学完（未验证）",
      mastery_status: "self_reported_completed",
    };
    readMock.mockResolvedValue({
      task_date: "2026-11-08",
      generated: false,
      tasks: [completed],
      plan_tasks: [completed],
      note: null,
    });
    verifyMock.mockResolvedValue({ id: "attempt-7" });

    render(<DashboardClient />);

    fireEvent.click(
      await screen.findByRole("button", { name: "我会了，测一测" }),
    );

    await waitFor(() => {
      expect(verifyMock).toHaveBeenCalledWith("python-basics-01-01");
    });
    expect(pushMock).toHaveBeenCalledWith("/quiz?attempt=attempt-7");
  });

  it("撤回自选任务后从列表移除", async () => {
    readMock.mockResolvedValue({
      task_date: "2026-11-08",
      generated: false,
      tasks: [SELF_TASK],
      plan_tasks: [],
      self_selected_tasks: [SELF_TASK],
      note: "暂无生效的学习计划；以下是你自己加入的学习任务",
    });
    generateMock.mockRejectedValue(new ApiError(404, "暂无学习计划，请先创建"));
    withdrawMock.mockResolvedValue(undefined);

    render(<DashboardClient />);

    fireEvent.click(await screen.findByRole("button", { name: "撤回" }));

    await waitFor(() => {
      expect(withdrawMock).toHaveBeenCalledWith("task-self");
    });
    await waitFor(() => {
      expect(screen.queryByText("数据结构综合运用")).not.toBeInTheDocument();
    });
  });

  it("开始学习会调用后端并更新任务状态", async () => {
    readMock.mockResolvedValue({
      task_date: "2026-11-08",
      generated: false,
      tasks: [TASK],
      plan_tasks: [TASK],
      note: null,
    });
    startMock.mockResolvedValue({
      ...TASK,
      status: "learning",
      progress_label: "学习中",
    });

    render(<DashboardClient />);

    fireEvent.click(await screen.findByRole("button", { name: "开始学习" }));

    await waitFor(() => {
      expect(startMock).toHaveBeenCalledWith("task-1");
    });
    expect(await screen.findByText("学习中")).toBeInTheDocument();
    expect(completeMock).not.toHaveBeenCalled();
  });
});
