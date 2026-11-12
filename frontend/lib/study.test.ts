import { describe, expect, it } from "vitest";

import { groupTodayTasks } from "@/lib/study";
import type { DailyTask, TodayTasks } from "@/lib/types";

function task(overrides: Partial<DailyTask>): DailyTask {
  return {
    id: "t1",
    plan_id: "plan-1",
    task_date: "2026-11-09",
    day_index: 1,
    status: "pending",
    started_at: null,
    completed_at: null,
    knowledge_point: {
      code: "python-basics-01-01",
      name: "知识点",
      learning_goal: "目标",
      difficulty: "beginner",
      estimated_minutes: 30,
      mastery_criteria: "标准",
      chapter_code: "python-basics-01",
      chapter_title: "第一章",
      resources: null,
      prerequisite_codes: [],
    },
    course_refs: null,
    mastery_status: "not_started",
    mastery_evidence_count: 0,
    completion_note: null,
    ...overrides,
  };
}

describe("groupTodayTasks", () => {
  it("新响应直接使用后端分组与汇总", () => {
    const planTask = task({ id: "p1", source: "plan" });
    const selfTask = task({ id: "s1", source: "self_selected", plan_id: null });
    const data: TodayTasks = {
      task_date: "2026-11-09",
      generated: false,
      tasks: [planTask, selfTask],
      plan_tasks: [planTask],
      self_selected_tasks: [selfTask],
      carried_over_tasks: [],
      summary: {
        plan_total: 1,
        plan_completed: 0,
        self_selected_total: 1,
        self_selected_completed: 0,
        in_progress: 0,
        carried_over: 0,
        remaining_minutes: 60,
      },
      note: null,
    };

    const groups = groupTodayTasks(data);

    expect(groups.plan.map((t) => t.id)).toEqual(["p1"]);
    expect(groups.selfSelected.map((t) => t.id)).toEqual(["s1"]);
    expect(groups.summary.remaining_minutes).toBe(60);
  });

  it("旧响应只有 tasks 时按 source 兜底，缺 source 视为计划任务", () => {
    const legacy = task({ id: "old" });
    const data: TodayTasks = {
      task_date: "2026-11-09",
      generated: false,
      tasks: [legacy],
      note: null,
    };

    const groups = groupTodayTasks(data);

    expect(groups.plan.map((t) => t.id)).toEqual(["old"]);
    expect(groups.selfSelected).toEqual([]);
    expect(groups.summary.plan_total).toBe(1);
    expect(groups.summary.remaining_minutes).toBe(30);
  });

  it("缺少 summary 时按分组现算，已完成任务不计入剩余时长", () => {
    const done = task({ id: "d1", status: "completed" });
    const data: TodayTasks = {
      task_date: "2026-11-09",
      generated: false,
      tasks: [done],
      plan_tasks: [done],
      note: null,
    };

    const groups = groupTodayTasks(data);

    expect(groups.summary.plan_completed).toBe(1);
    expect(groups.summary.remaining_minutes).toBe(0);
  });

  it("空数据返回空分组与零汇总", () => {
    const groups = groupTodayTasks(null);
    expect(groups.plan).toEqual([]);
    expect(groups.selfSelected).toEqual([]);
    expect(groups.carriedOver).toEqual([]);
    expect(groups.summary.plan_total).toBe(0);
  });
});
