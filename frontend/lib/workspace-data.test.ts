import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api";
import type { CurrentPlan, TodayTasks } from "@/lib/types";
import {
  computeLearningRuler,
  isNotFound,
  pickKnowledgePointCode,
  shouldGenerateTodayTasks,
  toPanelResult,
} from "@/lib/workspace-data";

const today = (tasks: TodayTasks["tasks"]): TodayTasks => ({
  task_date: "2026-11-09",
  generated: tasks.length > 0,
  tasks,
  note: null,
});

const task = (code: string, dayIndex: number) =>
  ({
    id: `t-${code}`,
    plan_id: "p1",
    task_date: "2026-11-09",
    day_index: dayIndex,
    status: "pending",
    started_at: null,
    completed_at: null,
    knowledge_point: {
      code,
      name: `知识点 ${code}`,
      learning_goal: "目标",
      difficulty: "beginner",
      estimated_minutes: 30,
      mastery_criteria: "标准",
      chapter_code: "ch1",
      chapter_title: "第一章",
      resources: null,
      prerequisite_codes: [],
    },
    course_refs: null,
    mastery_status: "not_started",
    mastery_evidence_count: 0,
    completion_note: null,
  }) as TodayTasks["tasks"][number];

describe("右栏数据聚合的确定性规则", () => {
  it("今日任务只有确实为空时才走生成接口", () => {
    expect(shouldGenerateTodayTasks(today([]))).toBe(true);
    expect(shouldGenerateTodayTasks(today([task("kp1", 3)]))).toBe(false);
  });

  it("当前知识点取当天第一个任务，无任务时为 null", () => {
    expect(pickKnowledgePointCode(today([task("kp1", 3), task("kp2", 4)]))).toBe(
      "kp1",
    );
    expect(pickKnowledgePointCode(today([]))).toBeNull();
    expect(pickKnowledgePointCode(null)).toBeNull();
  });

  it("404 归一为空状态，其余错误保留可读原因", () => {
    expect(isNotFound(new ApiError(404, "无计划"))).toBe(true);
    expect(isNotFound(new ApiError(500, "故障"))).toBe(false);
    expect(
      toPanelResult({ status: "rejected" as const, reason: new ApiError(404, "无计划") }),
    ).toEqual({ data: null, error: null });
    expect(
      toPanelResult({
        status: "rejected" as const,
        reason: new ApiError(500, "服务异常"),
      }),
    ).toEqual({ data: null, error: "服务异常" });
    expect(
      toPanelResult({ status: "fulfilled" as const, value: 7 }),
    ).toEqual({ data: 7, error: null });
  });

  it("刻度尺只按已生效计划项的真实完成数计算，没有计划时不编造进度", () => {
    const plan = {
      current_version: {
        items: [
          { id: "1", status: "completed" },
          { id: "2", status: "pending" },
          { id: "3", status: "pending" },
        ],
      },
    } as unknown as CurrentPlan;
    expect(computeLearningRuler(today([task("kp1", 3)]), plan)).toEqual({
      completed: 1,
      total: 3,
      dayIndex: 3,
      label: "1/3 项 · 第 3 天",
    });
    expect(computeLearningRuler(null, null)).toEqual({
      completed: 0,
      total: 0,
      dayIndex: null,
      label: "尚未建立学习计划",
    });
  });
});
