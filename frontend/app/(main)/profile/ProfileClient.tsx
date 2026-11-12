"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import EmptyState from "@/components/EmptyState";
import ErrorState from "@/components/ErrorState";
import LoadingState from "@/components/LoadingState";
import { getErrorMessage } from "@/lib/api";
import {
  getLearningOverview,
  getProfile,
  updateProfile,
  type LearningOverview,
  type Profile,
} from "@/lib/profile";
import type { CurrentLevel } from "@/lib/types";

const LEVEL_OPTIONS: { value: CurrentLevel; label: string }[] = [
  { value: "L0", label: "L0 零基础" },
  { value: "L1", label: "L1 碎片化学习" },
  { value: "L2", label: "L2 转行学习" },
];

export default function ProfileClient() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [overview, setOverview] = useState<LearningOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [learningGoal, setLearningGoal] = useState("");
  const [level, setLevel] = useState<CurrentLevel>("L0");
  const [dailyMinutes, setDailyMinutes] = useState("60");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveNotice, setSaveNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [profileData, overviewData] = await Promise.all([
        getProfile(),
        getLearningOverview(),
      ]);
      setProfile(profileData);
      setOverview(overviewData);
      setLearningGoal(profileData.learning_goal ?? "");
      setLevel((profileData.current_level as CurrentLevel | null) ?? "L0");
      setDailyMinutes(String(profileData.daily_study_minutes ?? 60));
    } catch (err) {
      setLoadError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!learningGoal.trim()) {
      setSaveError("请填写学习目标");
      return;
    }
    const minutes = Number(dailyMinutes);
    if (!Number.isInteger(minutes) || minutes < 1 || minutes > 1440) {
      setSaveError("每日可学习时间必须是 1–1440 之间的整数分钟");
      return;
    }
    setSaving(true);
    setSaveError(null);
    setSaveNotice(null);
    try {
      const updated = await updateProfile({
        learning_goal: learningGoal.trim(),
        current_level: level,
        daily_study_minutes: minutes,
      });
      setProfile(updated);
      setOverview(await getLearningOverview());
      setSaveNotice("学习档案已保存。接下来可以完成基础诊断并生成学习计划。");
    } catch (err) {
      setSaveError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <LoadingState label="加载学习档案…" />;
  }

  if (loadError) {
    return (
      <ErrorState
        title="无法加载学习档案"
        message={loadError}
        action={
          <button type="button" className="btn" onClick={() => void load()}>
            重试
          </button>
        }
      />
    );
  }

  const initialized = Boolean(
    profile?.learning_goal || profile?.current_level || profile?.daily_study_minutes,
  );

  return (
    <div className="profile-sections">
      <section className="card profile-form-card">
        <div className="section-head">
          <div>
            <h2 className="section-title">
              {initialized ? "编辑学习档案" : "初始化学习档案"}
            </h2>
            <p className="muted">
              学习目标、当前基础和每日学习时间会用于生成学习计划与调整 AI 讲解难度。
            </p>
          </div>
        </div>
        <form onSubmit={save}>
          <div className="form-group">
            <label className="form-label" htmlFor="profile-goal">
              学习目标
            </label>
            <textarea
              id="profile-goal"
              className="form-textarea"
              rows={3}
              required
              maxLength={500}
              value={learningGoal}
              onChange={(event) => setLearningGoal(event.target.value)}
              placeholder="例如：希望系统掌握 Python 基础，能独立写小脚本处理日常数据"
            />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label" htmlFor="profile-level">
                当前编程基础
              </label>
              <select
                id="profile-level"
                className="form-select"
                value={level}
                onChange={(event) => setLevel(event.target.value as CurrentLevel)}
              >
                {LEVEL_OPTIONS.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="profile-minutes">
                每日可学习时间（分钟）
              </label>
              <input
                id="profile-minutes"
                className="form-input"
                type="number"
                min={1}
                max={1440}
                required
                value={dailyMinutes}
                onChange={(event) => setDailyMinutes(event.target.value)}
              />
            </div>
          </div>
          {saveError && <div className="inline-error">{saveError}</div>}
          {saveNotice && <div className="notice notice-success">{saveNotice}</div>}
          <div className="row-actions form-actions">
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "保存中…" : "保存学习档案"}
            </button>
            {initialized && (
              <Link className="btn" href="/plan">
                前往学习计划
              </Link>
            )}
          </div>
        </form>
      </section>

      {overview && (
        <>
          <section className="card profile-section">
            <div className="section-head">
              <div>
                <h2 className="section-title">学习进度</h2>
                <p className="muted">数据来自真实的学习任务、测验与复习记录。</p>
              </div>
            </div>
            <div className="stats-grid">
              <div className="stat-card">
                <span className="stat-label">已学习知识点</span>
                <span className="stat-value">{overview.learned_count}</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">已掌握</span>
                <span className="stat-value">{overview.mastered_count}</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">测验平均分</span>
                <span className="stat-value">
                  {overview.quiz_average_score ?? "—"}
                </span>
              </div>
              <div className="stat-card">
                <span className="stat-label">待复习错题</span>
                <span className="stat-value">{overview.mistake_pending_count}</span>
              </div>
            </div>
            <div className="stat-note">
              <p>
                待验证：{overview.pending_verification_count} · 学习中：{" "}
                {overview.learning_count} · 到期复习：{overview.review_due_count} ·
                测验次数：{overview.quiz_submitted_count}
              </p>
              <p>
                计划进度：{overview.plan_completed_items}/{overview.plan_total_items}
                {overview.plan_total_items > 0
                  ? `（${overview.plan_progress_percent}%）`
                  : ""}
                {overview.plan_course_name ? ` · ${overview.plan_course_name}` : ""}
              </p>
            </div>
            {overview.notes.length > 0 && (
              <ul className="note-list">
                {overview.notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            )}
            {!overview.plan_available && (
              <EmptyState
                title="还没有学习计划"
                description="完成学习档案初始化后，可在学习计划页提交基础诊断并生成计划。"
                action={
                  <Link className="btn btn-primary" href="/plan">
                    去创建学习计划
                  </Link>
                }
              />
            )}
          </section>

          <section className="card profile-section">
            <h2 className="section-title">章节掌握情况</h2>
            {overview.chapters.length === 0 ? (
              <p className="muted">
                还没有已学习知识点。完成每日任务或在课程学习中开始学习后，这里会显示章节进度。
              </p>
            ) : (
              <ul className="chapter-progress-list">
                {overview.chapters.map((chapter) => {
                  const ratio =
                    chapter.learned_count > 0
                      ? Math.round(
                          (chapter.mastered_count / chapter.learned_count) * 100,
                        )
                      : 0;
                  return (
                    <li key={chapter.chapter_code} className="chapter-progress-item">
                      <div className="chapter-progress-head">
                        <span>{chapter.chapter_title}</span>
                        <span className="muted">
                          已掌握 {chapter.mastered_count}/{chapter.learned_count}
                        </span>
                      </div>
                      <div
                        className="progress-track"
                        role="progressbar"
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-valuenow={ratio}
                        aria-label={`${chapter.chapter_title}掌握率`}
                      >
                        <span className="progress-fill" style={{ width: `${ratio}%` }} />
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}
