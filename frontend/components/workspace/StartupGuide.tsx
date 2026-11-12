"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { ApiError, getErrorMessage } from "@/lib/api";
import { listCourses } from "@/lib/learning";
import { runDiagnosis } from "@/lib/mastery";
import { confirmPlan, createPlan, getCurrentPlan } from "@/lib/plans";
import { getProfile, updateProfile } from "@/lib/profile";
import type { CurrentLevel, DiagnosisReport } from "@/lib/types";
import { publishWorkspaceEvent } from "@/lib/workspace-bus";

const DONE_KEY = "xiaoma.v14.startup.done";

const LEVELS: { value: CurrentLevel; label: string; hint: string }[] = [
  { value: "L0", label: "L0 零基础", hint: "还没写过代码" },
  { value: "L1", label: "L1 碎片化学习", hint: "看过教程，学过一部分" },
  { value: "L2", label: "L2 转行学习", hint: "有其他语言或工作经验" },
];

const STEP_LABELS = [
  "欢迎",
  "学习档案",
  "学习目标",
  "编程基础",
  "每日时长",
  "基础诊断",
  "计划建议",
  "确认计划",
  "进入工作台",
];

type GuideState = "checking" | "hidden" | "visible";

/**
 * 首次启动引导（PRD §4.1 九步）。
 *
 * 触发条件是后端真实状态：学习档案未设目标，或尚无已生效的学习计划；
 * 用户主动「跳过」后写入本地标记，不改动任何业务数据。
 * 每一步都调用既有业务接口，失败时明确展示错误并允许重试，绝不伪造成功。
 */
export default function StartupGuide() {
  const router = useRouter();
  const [state, setState] = useState<GuideState>("checking");
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [username, setUsername] = useState("");
  const [goal, setGoal] = useState("");
  const [level, setLevel] = useState<CurrentLevel>("L0");
  const [minutes, setMinutes] = useState("60");
  const [courseCode, setCourseCode] = useState("");
  const [diagnosis, setDiagnosis] = useState<DiagnosisReport | null>(null);
  const [planId, setPlanId] = useState<string | null>(null);
  const [planSummary, setPlanSummary] = useState("");

  const finish = useCallback(() => {
    try {
      window.localStorage.setItem(DONE_KEY, "1");
    } catch {
      // 隐私模式下 localStorage 不可用：本次会话内仍然关闭引导
    }
    setState("hidden");
    publishWorkspaceEvent({ type: "panels:refresh" });
  }, []);

  useEffect(() => {
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      try {
        let done = false;
        try {
          done = window.localStorage.getItem(DONE_KEY) === "1";
        } catch {
          done = false;
        }
        if (done) {
          if (!cancelled) setState("hidden");
          return;
        }
        const [profile, courses] = await Promise.all([
          getProfile(),
          listCourses(),
        ]);
        let hasActivePlan = false;
        try {
          const plan = await getCurrentPlan();
          hasActivePlan = plan.status === "active";
        } catch (err) {
          if (!(err instanceof ApiError && err.status === 404)) {
            throw err;
          }
        }
        if (cancelled) return;
        setUsername(profile.username);
        setGoal(profile.learning_goal ?? "");
        setLevel(profile.current_level ?? "L0");
        setMinutes(String(profile.daily_study_minutes ?? 60));
        setCourseCode(courses[0]?.code ?? "");
        setState(
          Boolean(profile.learning_goal) && hasActivePlan ? "hidden" : "visible",
        );
      } catch (err) {
        if (!cancelled) {
          // 服务暂不可用时不阻塞主界面：本次会话不显示引导，下次启动再判断
          setError(getErrorMessage(err));
          setState("hidden");
        }
      }
    }, 0);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, []);

  /** 统一的异步步骤执行器：busy / error 状态由引导层负责，不吞异常。 */
  const runStep = useCallback(
    async (action: () => Promise<void>) => {
      setBusy(true);
      setError(null);
      try {
        await action();
        setStep((current) => Math.min(current + 1, STEP_LABELS.length - 1));
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  if (state !== "visible") {
    return null;
  }

  const next = () => setStep((current) => Math.min(current + 1, 8));

  const renderStep = () => {
    switch (step) {
      case 0:
        return (
          <>
            <p className="guide-lead">
              打开小码，就能知道今天学什么，并且可以直接和 AI 一起完成学习。
              首次使用会用几步建立你的学习档案与计划，全部数据保存在你自己的部署里。
            </p>
            <button type="button" className="btn btn-primary" onClick={next}>
              开始设置
            </button>
          </>
        );
      case 1:
        return (
          <>
            <p className="guide-lead">
              已读取到本机学习档案：<strong>{username || "默认用户"}</strong>。
              接下来依次设置目标、基础与每日学习时间，每一步都会即时保存到后端。
            </p>
            <button type="button" className="btn btn-primary" onClick={next}>
              下一步
            </button>
          </>
        );
      case 2:
        return (
          <>
            <label className="form-label" htmlFor="guide-goal">
              你想通过学习达成什么？
            </label>
            <textarea
              id="guide-goal"
              className="form-textarea"
              rows={3}
              value={goal}
              onChange={(event) => setGoal(event.target.value)}
              placeholder="例如：零基础学会 Python，能自己写小工具"
            />
            <button
              type="button"
              className="btn btn-primary"
              disabled={busy || !goal.trim()}
              onClick={() =>
                void runStep(async () => {
                  await updateProfile({ learning_goal: goal.trim() });
                })
              }
            >
              {busy ? "保存中…" : "保存并继续"}
            </button>
          </>
        );
      case 3:
        return (
          <>
            <p className="guide-lead">选择最接近你当前情况的编程基础。</p>
            <div className="guide-levels">
              {LEVELS.map((item) => (
                <button
                  key={item.value}
                  type="button"
                  className={`guide-level${level === item.value ? " active" : ""}`}
                  onClick={() => setLevel(item.value)}
                  aria-pressed={level === item.value}
                >
                  <strong>{item.label}</strong>
                  <span>{item.hint}</span>
                </button>
              ))}
            </div>
            <button
              type="button"
              className="btn btn-primary"
              disabled={busy}
              onClick={() =>
                void runStep(async () => {
                  await updateProfile({ current_level: level });
                })
              }
            >
              {busy ? "保存中…" : "保存并继续"}
            </button>
          </>
        );
      case 4:
        return (
          <>
            <label className="form-label" htmlFor="guide-minutes">
              每天大约能学习多少分钟？
            </label>
            <input
              id="guide-minutes"
              className="form-input"
              type="number"
              min={10}
              max={480}
              value={minutes}
              onChange={(event) => setMinutes(event.target.value)}
            />
            <button
              type="button"
              className="btn btn-primary"
              disabled={busy || Number(minutes) < 10}
              onClick={() =>
                void runStep(async () => {
                  await updateProfile({
                    daily_study_minutes: Number(minutes),
                  });
                })
              }
            >
              {busy ? "保存中…" : "保存并继续"}
            </button>
          </>
        );
      case 5:
        return (
          <>
            <p className="guide-lead">
              根据学习目标与课程知识点做一次基础诊断，结果由后端生成。
            </p>
            {diagnosis && (
              <div className="guide-result">
                <p>{diagnosis.summary}</p>
                <p className="panel-muted">
                  推荐路线 {diagnosis.route.length} 步 · 可跳过知识点{" "}
                  {diagnosis.skippable_kp_codes.length} 个
                </p>
              </div>
            )}
            <button
              type="button"
              className="btn btn-primary"
              disabled={busy}
              onClick={() =>
                void runStep(async () => {
                  const report = await runDiagnosis({
                    learning_goal: goal.trim(),
                    ...(courseCode ? { target_course_code: courseCode } : {}),
                  });
                  setDiagnosis(report);
                })
              }
            >
              {busy ? "诊断中…" : "完成基础诊断"}
            </button>
          </>
        );
      case 6:
        return (
          <>
            <p className="guide-lead">
              按档案与诊断结果生成一份学习计划草稿；草稿不会自动生效。
            </p>
            {diagnosis && (
              <div className="guide-result">
                <p>{diagnosis.summary}</p>
              </div>
            )}
            {planSummary && <div className="guide-result">{planSummary}</div>}
            <button
              type="button"
              className="btn btn-primary"
              disabled={busy || !courseCode}
              onClick={() =>
                void runStep(async () => {
                  const plan = await createPlan({
                    course_code: courseCode,
                    learning_goal: goal.trim(),
                    current_level: level,
                    daily_study_minutes: Number(minutes),
                    expected_duration_days: 30,
                    mastered_kp_codes: diagnosis?.skippable_kp_codes ?? [],
                  });
                  setPlanId(plan.id);
                  const version = plan.pending_version ?? plan.current_version;
                  setPlanSummary(
                    `课程：${plan.course_name} · 计划项 ${
                      version?.items.length ?? 0
                    } 个 · 预计 ${version?.computed_duration_days ?? "—"} 天`,
                  );
                })
              }
            >
              {busy ? "生成中…" : "生成计划建议"}
            </button>
          </>
        );
      case 7:
        return (
          <>
            <p className="guide-lead">
              请确认计划。未经确认，学习计划不会正式生效；之后仍可在「学习计划」中调整。
            </p>
            {planSummary && <div className="guide-result">{planSummary}</div>}
            <button
              type="button"
              className="btn btn-primary"
              disabled={busy || !planId}
              onClick={() =>
                void runStep(async () => {
                  if (!planId) throw new Error("计划尚未生成");
                  await confirmPlan(planId);
                })
              }
            >
              {busy ? "确认中…" : "确认并保存正式计划"}
            </button>
          </>
        );
      default:
        return (
          <>
            <p className="guide-lead">
              学习档案与计划已就绪。现在进入对话式学习工作台，今日任务和当前知识点会自动同步到右侧面板。
            </p>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => {
                finish();
                router.push("/workspace");
              }}
            >
              进入对话式学习工作台
            </button>
          </>
        );
    }
  };

  return (
    <div className="guide-overlay" role="dialog" aria-modal="true" aria-labelledby="guide-title">
      <div className="guide-card">
        <header className="guide-head">
          <div>
            <span className="guide-eyebrow">首次启动 · 小码 Xiaoma</span>
            <h1 id="guide-title" className="guide-title">
              {STEP_LABELS[step]}
            </h1>
          </div>
          <button
            type="button"
            className="btn btn-sm"
            onClick={finish}
            disabled={busy}
          >
            跳过
          </button>
        </header>

        <ol className="guide-steps" aria-label="引导进度">
          {STEP_LABELS.map((label, index) => (
            <li
              key={label}
              className={index === step ? "current" : index < step ? "done" : ""}
              aria-current={index === step ? "step" : undefined}
            >
              <span>{String(index + 1).padStart(2, "0")}</span>
            </li>
          ))}
        </ol>

        {error && (
          <div className="inline-error" role="alert">
            <span>{error}</span>
            <button type="button" className="btn btn-sm" onClick={() => setError(null)}>
              知道了
            </button>
          </div>
        )}

        <div className="guide-body">{renderStep()}</div>

        <footer className="guide-foot">
          <button
            type="button"
            className="btn btn-sm"
            disabled={step === 0 || busy}
            onClick={() => {
              setError(null);
              setStep((current) => Math.max(0, current - 1));
            }}
          >
            上一步
          </button>
          <span className="panel-muted">
            第 {step + 1} / {STEP_LABELS.length} 步
          </span>
        </footer>
      </div>
    </div>
  );
}
