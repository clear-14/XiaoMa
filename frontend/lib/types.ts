/** 与后端 API 保持一致的数据类型（字段名不转换）。 */

/* ------------------------------ 聊天会话 ------------------------------ */

export interface ConversationKnowledgePoint {
  code: string;
  name: string;
  chapter_code: string;
  chapter_title: string;
}

export type MessageRole = "user" | "assistant";
/** V1.4 批次 1 后端状态机：streaming → completed / error / stopped。 */
export type MessageStatus = "completed" | "error" | "streaming" | "stopped";

/** 卡片协议：字段名与后端 app/schemas/cards.py、SSE card 事件完全一致。 */
export type CardTypeName =
  | "text"
  | "task_card"
  | "lesson_card"
  | "quiz_card"
  | "quiz_result_card"
  | "mistake_card"
  | "plan_card"
  | "plan_change_card"
  | "progress_card"
  | "error_card";

/** 单张完整卡片对象；payload 的具体判别联合在批次 4 的 lib/cards.ts 定义。 */
export interface CardEnvelope {
  card_version: string;
  type: string;
  payload: unknown;
}

/** 持久化在 messages.structured_data 的卡片集合（一条助手消息可带多张卡片）。 */
export interface CardCollection {
  card_version: string;
  type: string;
  cards: CardEnvelope[];
}

/** SSE `card` 事件帧：一次性下发完整 JSON，禁止增量拼接。 */
export interface CardSseFrame {
  conversation_id: string;
  message_id: string | null;
  card_version: string;
  message_type: string;
  structured_data: CardEnvelope;
}

export interface ConversationMessage {
  id: string;
  role: MessageRole;
  /** error / stopped 时为已生成的部分内容（可能为空字符串） */
  content: string;
  status: MessageStatus;
  /** status=error 时的失败原因 */
  error_message: string | null;
  model_name: string | null;
  created_at: string;
  /** V1.4 批次 1 新增：普通文本为 "text"，卡片消息为首张卡片类型。 */
  message_type?: CardTypeName | string;
  /** 卡片结构化数据；普通文本为 null。 */
  structured_data?: CardCollection | null;
  /** 卡片协议版本；普通文本为 null。 */
  card_version?: string | null;
}

export interface ConversationSummary {
  id: string;
  title: string;
  knowledge_point: ConversationKnowledgePoint | null;
  daily_task_id: string | null;
  message_count: number;
  last_activity_at: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends ConversationSummary {
  messages: ConversationMessage[];
}

export interface CreateConversationInput {
  title?: string;
  knowledge_point_code?: string;
  daily_task_id?: string;
}

/** SSE start / done 事件中与界面相关的字段。 */
export interface ConversationStreamInfo {
  conversation_id: string;
  message_id?: string | null;
  /** 非教学子图不调用模型时为 null */
  model?: string | null;
  title?: string;
  message_count?: number;
  user_message_id?: string;
  intent?: string;
  sub_intent?: string;
  subgraph?: string;
  /** ok=完成；unavailable=业务暂不可用；stopped=用户主动停止生成（V1.4 批次 5）。 */
  result_status?: "ok" | "unavailable" | "stopped";
}

export interface ConversationStreamError {
  conversation_id: string;
  message_id: string | null;
  message: string;
}

/* ------------------------------ 每日任务 ------------------------------ */

export interface DailyTaskKnowledgePoint {
  code: string;
  name: string;
  learning_goal: string;
  difficulty: string;
  estimated_minutes: number;
  mastery_criteria: string;
  chapter_code: string;
  chapter_title: string;
  resources: LearningResource[] | null;
  prerequisite_codes: string[];
}

/** 今日任务引用的真实课程层级标识（course / module / lesson / knowledge_point）。 */
export interface DailyTaskCourseRefs {
  course_id: string;
  module_id: string;
  lesson_id: string;
  knowledge_point_id: string;
  course_code: string;
  module_code: string;
  lesson_code: string;
  knowledge_point_code: string;
  lesson_title: string;
}

export interface DailyTask {
  id: string;
  /** 计划外自选任务不挂计划，故可为 null（阶段 7） */
  plan_id: string | null;
  task_date: string;
  day_index: number;
  /** 任务来源：plan 计划自动排期 / self_selected 用户自主加入今日学习 */
  source?: "plan" | "self_selected";
  status: "pending" | "learning" | "completed";
  /** 学习完成度标签（阶段 7）：未开始 / 学习中 / 已学完（未验证） */
  progress_label?: string;
  carried_over?: boolean;
  carried_over_days?: number;
  started_at: string | null;
  completed_at: string | null;
  knowledge_point: DailyTaskKnowledgePoint;
  /** 阶段 6：新生成的任务四个真实标识齐全；升级前历史任务可能为 null。 */
  course_refs: DailyTaskCourseRefs | null;
  mastery_status: string;
  mastery_evidence_count: number;
  completion_note: string | null;
}

/** 今日任务汇总（阶段 7）：只计数，不把「学完」当「掌握」。 */
export interface TodayTasksSummary {
  plan_total: number;
  plan_completed: number;
  self_selected_total: number;
  self_selected_completed: number;
  in_progress: number;
  carried_over: number;
  remaining_minutes: number;
}

export interface TodayTasks {
  task_date: string;
  generated: boolean;
  tasks: DailyTask[];
  /** 阶段 7 分组字段：旧后端/旧测试数据可能没有，前端用 resolve 函数兜底 */
  plan_tasks?: DailyTask[];
  self_selected_tasks?: DailyTask[];
  carried_over_tasks?: DailyTask[];
  summary?: TodayTasksSummary;
  note: string | null;
}

/* ---------------------- 自主选题与学习进度（阶段 7） ---------------------- */

export interface PrerequisiteWarning {
  knowledge_point_code: string;
  knowledge_point_name: string;
  status: string;
  status_label: string;
}

/** 加入今日学习的结果（幂等：当天已存在则 created=false）。 */
export interface SelfStudyResult {
  task: DailyTask;
  created: boolean;
  prerequisite_warnings: PrerequisiteWarning[];
  note: string | null;
}

/** 章节级进度：learning_percent 是学习完成度，mastery_percent 是已验证掌握度。 */
export interface ChapterProgress {
  chapter_code: string;
  chapter_title: string;
  order_index: number;
  kp_total: number;
  kp_started: number;
  kp_learned: number;
  kp_mastered: number;
  minutes_total: number;
  minutes_learned: number;
  learning_percent: number;
  mastery_percent: number;
}

export interface CourseProgress {
  course_code: string;
  course_name: string;
  course_publish_status: string;
  kp_total: number;
  kp_started: number;
  kp_learned: number;
  kp_mastered: number;
  minutes_total: number;
  minutes_learned: number;
  learning_percent: number;
  mastery_percent: number;
  chapters: ChapterProgress[];
  notes: string[];
}

export interface StudyCandidateKp {
  code: string;
  name: string;
  difficulty: string;
  estimated_minutes: number;
  chapter_code: string;
  mastery_status: string;
  mastery_status_label: string;
  today_task_status: string | null;
  today_task_source: string | null;
  can_start: boolean;
  block_reason: string | null;
  prerequisite_codes: string[];
  unmastered_prerequisite_codes: string[];
}

export interface StudyCandidateChapter {
  code: string;
  title: string;
  order_index: number;
  kp_total: number;
  kp_learned: number;
  kp_mastered: number;
  learning_percent: number;
  mastery_percent: number;
  knowledge_points: StudyCandidateKp[];
}

export interface StudyCandidates {
  course_code: string;
  course_name: string;
  course_publish_status: string;
  progress: CourseProgress;
  chapters: StudyCandidateChapter[];
  notes: string[];
}

/* ------------------------------ 课程体系 ------------------------------ */

export interface LearningResource {
  type: string;
  title: string;
  url: string | null;
}

export interface KnowledgePointSummary {
  id: string;
  code: string;
  name: string;
  difficulty: string;
  estimated_minutes: number;
  order_index: number;
}

export interface Chapter {
  id: string;
  code: string;
  title: string;
  description: string | null;
  order_index: number;
  knowledge_points: KnowledgePointSummary[];
}

export interface CourseSummary {
  id: string;
  code: string;
  name: string;
  description: string | null;
  chapter_count: number;
}

export interface CourseDetail extends CourseSummary {
  chapters: Chapter[];
}

export interface ChapterBrief {
  code: string;
  title: string;
}

export interface KnowledgePointDetail {
  id: string;
  code: string;
  name: string;
  learning_goal: string;
  difficulty: string;
  estimated_minutes: number;
  mastery_criteria: string;
  resources: LearningResource[] | null;
  order_index: number;
  chapter: ChapterBrief;
  prerequisites: KnowledgePointSummary[];
}

/* ------------------------------ 测验与错题 ------------------------------ */

export type QuizScopeType = "knowledge_point" | "chapter" | "stage";

export type QuizQuestionType =
  | "single_choice"
  | "multiple_choice"
  | "true_false"
  | "fill_blank"
  | "short_answer"
  | "code_analysis"
  | "code_writing";

export interface QuizKnowledgePoint {
  code: string;
  name: string;
  chapter_code: string;
  chapter_title: string;
}

export interface QuizQuestionOption {
  key: string;
  text: string;
}

export interface QuizQuestion {
  id: string;
  order: number;
  question_type: QuizQuestionType;
  stem: string;
  options: QuizQuestionOption[] | null;
  points: number;
  source: "builtin" | "ai";
  knowledge_point: QuizKnowledgePoint;
  user_answer: unknown;
  correct_answer: unknown;
  explanation: string | null;
  score: number | null;
  max_score: number;
  is_correct: boolean | null;
  grading_basis: GradingBasis | null;
}

export interface GradingBasis {
  type?: string;
  expected?: unknown;
  submitted?: unknown;
  missing?: string[];
  unexpected?: string[];
  reference?: string;
  keywords?: string[];
  matched_keywords?: string[];
  missing_keywords?: string[];
  matched_count?: number;
  keyword_count?: number;
  ratio?: number;
  note?: string;
}

export interface MasteryUpdate {
  knowledge_point_code: string;
  knowledge_point_name: string;
  achieved: boolean;
  reasons: string[];
}

export interface QuizAttempt {
  id: string;
  scope_type: QuizScopeType | "review";
  scope_ref: string | null;
  scope_name: string;
  status: "in_progress" | "submitted";
  /** 阶段 5：practice=常规练习，placement=诊断（跳级）测验 */
  purpose: "practice" | "placement";
  question_count: number;
  total_points: number;
  score: number | null;
  ai_requested: number;
  ai_accepted: number;
  ai_note: string | null;
  mastery_updates: MasteryUpdate[];
  started_at: string;
  submitted_at: string | null;
  questions: QuizQuestion[];
}

export interface QuizAttemptSummary {
  id: string;
  scope_type: QuizScopeType | "review";
  scope_name: string;
  status: "in_progress" | "submitted";
  /** 阶段 5：practice=常规练习，placement=诊断（跳级）测验 */
  purpose: "practice" | "placement";
  question_count: number;
  score: number | null;
  ai_accepted: number;
  started_at: string;
  submitted_at: string | null;
}

export interface EligibilityKnowledgePoint {
  code: string;
  name: string;
  chapter_code: string;
  chapter_title: string;
  status: string;
  question_count: number;
  quiz_available: boolean;
}

export interface EligibilityChapter {
  code: string;
  title: string;
  learned_knowledge_point_count: number;
  question_count: number;
  quiz_available: boolean;
}

export interface EligibilityStage {
  available: boolean;
  course_code: string | null;
  course_name: string | null;
  learned_knowledge_point_count: number;
  question_count: number;
  note: string | null;
}

export interface QuizEligibility {
  learned_knowledge_points: EligibilityKnowledgePoint[];
  chapters: EligibilityChapter[];
  stage: EligibilityStage;
}

export interface QuizCreateInput {
  scope_type: QuizScopeType;
  knowledge_point_code?: string;
  chapter_code?: string;
  ai_variant_count?: number;
}

export interface QuizAnswerInput {
  question_id: string;
  answer: unknown;
}

export interface Mistake {
  id: string;
  question: QuizQuestion;
  knowledge_point: QuizKnowledgePoint;
  attempt_count: number;
  last_answer: unknown;
  last_wrong_at: string;
  review_status: "pending" | "resolved";
  review_stage: number;
  next_review_at: string | null;
  resolved_at: string | null;
  pending_review_task_id: string | null;
}

export interface ReviewTask {
  id: string;
  mistake_id: string;
  due_at: string;
  interval_days: number;
  status: "pending" | "completed" | "skipped";
  is_due: boolean;
  last_result: "correct" | "wrong" | null;
  question: QuizQuestion;
  knowledge_point: QuizKnowledgePoint;
}

export interface ReviewResult {
  review_task: ReviewTask;
  question: QuizQuestion;
  mistake: Mistake;
  next_review_task: ReviewTask | null;
  message: string;
}

/* ------------------------------ 学习档案与概览 ------------------------------ */

export type CurrentLevel = "L0" | "L1" | "L2";

export interface Profile {
  username: string;
  learning_goal: string | null;
  current_level: CurrentLevel | null;
  daily_study_minutes: number | null;
  learning_preferences: Record<string, unknown> | null;
}

export interface ProfileUpdateInput {
  learning_goal?: string | null;
  current_level?: CurrentLevel | null;
  daily_study_minutes?: number | null;
  learning_preferences?: Record<string, unknown> | null;
}

export interface ChapterProgress {
  chapter_code: string;
  chapter_title: string;
  learned_count: number;
  mastered_count: number;
}

export interface LearningOverview {
  today: string;
  learning_goal: string | null;
  current_level: string | null;
  daily_study_minutes: number | null;
  plan_available: boolean;
  plan_confirmed: boolean;
  plan_course_name: string | null;
  plan_current_version_number: number | null;
  plan_pending_version_number: number | null;
  plan_total_items: number;
  plan_completed_items: number;
  plan_progress_percent: number;
  plan_current_day: number | null;
  plan_warning: string | null;
  learned_count: number;
  mastered_count: number;
  learning_count: number;
  pending_verification_count: number;
  review_due_count: number;
  quiz_attempt_count: number;
  quiz_submitted_count: number;
  quiz_average_score: number | null;
  latest_quiz_score: number | null;
  mistake_total_count: number;
  mistake_pending_count: number;
  mistake_resolved_count: number;
  mistake_due_count: number;
  chapters: ChapterProgress[];
  notes: string[];
}

/* ------------------------------ 学习计划 ------------------------------ */

export interface PlanCreateInput {
  course_code: string;
  learning_goal: string;
  current_level: CurrentLevel | null;
  daily_study_minutes: number;
  expected_duration_days: number;
  mastered_kp_codes: string[];
}

export interface PlanAdjustInput {
  learning_goal?: string;
  daily_study_minutes?: number;
  expected_duration_days?: number;
}

export interface PlanItem {
  id: string;
  knowledge_point_code: string;
  knowledge_point_name: string;
  estimated_minutes: number;
  day_index: number;
  status: "pending" | "completed";
  completed_at: string | null;
}

/** 阶段 6：学习计划版本生成时实际使用的八类输入快照。 */
export interface PlanContext {
  learning_goal: string;
  daily_study_minutes: number;
  current_level: string | null;
  mastered_kp_codes: string[];
  unmastered_kp_codes: string[];
  prerequisite_kp_codes: string[];
  remedial_kp_codes: string[];
  review_kp_codes: string[];
  course_estimated_minutes: number | null;
  scheduled_minutes: number;
  estimated_minutes_note: string | null;
  recent_quiz_scores: number[];
  quiz_average_score: number | null;
  quiz_attempt_count: number;
  placement_evidence_count: number;
  diagnosis_note: string;
  notes: string[];
}

export interface PlanVersion {
  version_number: number;
  status: string;
  learning_goal: string;
  daily_study_minutes: number;
  expected_duration_days: number;
  computed_duration_days: number;
  warning: string | null;
  current_level: string | null;
  mastered_kp_codes: string[] | null;
  skipped_kp_codes: string[] | null;
  self_reported_kp_codes: string[] | null;
  pending_verification_kp_codes: string[] | null;
  skip_note: string | null;
  plan_context: PlanContext;
  created_at: string;
  items: PlanItem[];
}

export interface PlanVersionSummary {
  version_number: number;
  status: string;
  learning_goal: string;
  daily_study_minutes: number;
  expected_duration_days: number;
  computed_duration_days: number;
  item_count: number;
  completed_count: number;
  created_at: string;
}

export interface Plan {
  id: string;
  course_code: string;
  course_name: string;
  status: string;
  start_date: string | null;
  current_version_number: number | null;
  pending_version_number: number | null;
  versions: PlanVersionSummary[];
  created_at: string;
}

export interface CurrentPlan extends Plan {
  current_version: PlanVersion | null;
  pending_version: PlanVersion | null;
}

/* --------------------------- 动态计划调整提案 --------------------------- */

export interface ProposalCreateInput {
  learning_goal?: string;
  daily_study_minutes?: number;
  expected_duration_days?: number;
  reason?: string;
  source?: "user" | "agent" | "api";
  declared_triggers?: string[];
}

export interface PlanSignal {
  code: string;
  label: string;
  detail: string;
}

export interface PlanSignals {
  signals: PlanSignal[];
  proposal_needed: boolean;
  summary: string;
}

export interface ProposalPreview {
  current: Record<string, string | number | null>;
  proposed: Record<string, string | number | null>;
  impacts: string[];
  signals: PlanSignal[];
  skipped_kp_codes: string[];
  mastered_kp_codes: string[];
  review_kp_codes: string[];
  remedial_kp_codes: string[];
  needs_review_count: number;
  recent_quiz_scores: number[];
}

export interface PlanAdjustmentProposal {
  id: string;
  plan_id: string;
  status: "proposed" | "confirmed" | "rejected";
  triggers: string[];
  trigger_labels: string[];
  reason: string;
  changes: Record<string, string | number>;
  preview: ProposalPreview;
  source: string;
  created_at: string;
  confirmed_at: string | null;
  rejected_at: string | null;
  resulting_version_number: number | null;
  requires_confirmation: boolean;
  note: string;
}

export interface ProposalConfirmResult {
  proposal: PlanAdjustmentProposal;
  plan: CurrentPlan;
  message: string;
}

/* ------------------------------ 模型配置 ------------------------------ */

export type ModelProvider = "deepseek" | "qwen" | "openai" | "custom";

export interface ModelConfig {
  id: string;
  name: string;
  provider: string;
  model_name: string;
  base_url: string | null;
  temperature: number;
  max_tokens: number;
  timeout: number;
  is_default: boolean;
  has_api_key: boolean;
  api_key_masked: string | null;
  created_at: string;
  updated_at: string;
}

export interface ModelConfigInput {
  name: string;
  provider: ModelProvider;
  model_name: string;
  base_url?: string | null;
  api_key?: string;
  temperature?: number;
  max_tokens?: number;
  timeout?: number;
  is_default?: boolean;
}

export interface TestConnectionResult {
  ok: boolean;
  model: string;
  latency_ms: number | null;
  reply: string | null;
  error: string | null;
}

/* ------------------------------ 数据备份 ------------------------------ */

export interface BackupInfo {
  name: string;
  size_bytes: number;
  created_at: string;
}

/* --------------------- 阶段 5：知识点掌握度与诊断 --------------------- */

/** 7 个掌握状态（与后端 app/models/mastery.py 一致）。 */
export type MasteryStatus =
  | "not_started"
  | "learning"
  | "self_reported_completed"
  | "understood"
  | "applied"
  | "mastered"
  | "needs_review";

export type EvidenceSource = "self_report" | "exercise" | "quiz" | "placement";

export interface MasteryKnowledgePoint {
  knowledge_point_code: string;
  knowledge_point_name: string;
  chapter_code: string;
  chapter_title: string;
  course_code: string;
  course_name: string;
  difficulty: string;
  status: MasteryStatus;
  status_label: string;
  accuracy: number | null;
  quiz_difficulty: string | null;
  evidence_count: number;
  verified_at: string | null;
  self_reported_at: string | null;
  review_due_at: string | null;
  next_action: string;
}

export interface MasteryEvidence {
  id: string;
  source: EvidenceSource;
  source_label: string;
  status_before: MasteryStatus;
  status_after: MasteryStatus;
  status_before_label: string;
  status_after_label: string;
  accuracy: number | null;
  quiz_difficulty: string | null;
  quiz_attempt_id: string | null;
  exercise_attempt_id: string | null;
  note: string | null;
  verified_at: string;
}

export interface ExerciseAttemptRecord {
  id: string;
  exercise_code: string;
  exercise_title: string;
  exercise_type: string;
  difficulty: string;
  answer: string;
  result: "passed" | "failed";
  coverage: number | null;
  grading_basis: Record<string, unknown> | null;
  graded_at: string;
}

export interface MasteryDetail {
  knowledge_point: MasteryKnowledgePoint;
  evidence: MasteryEvidence[];
  exercise_attempts: ExerciseAttemptRecord[];
}

export interface MasteryCounts {
  not_started: number;
  learning: number;
  self_reported_completed: number;
  understood: number;
  applied: number;
  mastered: number;
  needs_review: number;
  total: number;
}

export interface MasteryCourse {
  course_code: string;
  course_name: string;
  counts: MasteryCounts;
  mastered_percent: number;
}

export interface MasteryOverview {
  counts: MasteryCounts;
  mastered_percent: number;
  verified_mastered_count: number;
  self_reported_only_count: number;
  courses: MasteryCourse[];
  needs_review: MasteryKnowledgePoint[];
}

export interface SelfReportItem {
  knowledge_point_code: string;
  knowledge_point_name: string;
  status_before: MasteryStatus;
  status_after: MasteryStatus;
  changed: boolean;
  note: string;
}

export interface SelfReportResult {
  items: SelfReportItem[];
  note: string;
}

export interface ReviewSuggestion {
  knowledge_point: MasteryKnowledgePoint;
  reasons: string[];
  actions: string[];
  exercise_codes: string[];
  question_count: number;
}

export interface SkipCheckItem {
  knowledge_point_code: string;
  knowledge_point_name: string;
  status: MasteryStatus;
  status_label: string;
  reason: string;
}

export interface SkipCheck {
  course_code: string;
  course_name: string;
  skippable: SkipCheckItem[];
  needs_verification: SkipCheckItem[];
  blocked: SkipCheckItem[];
  notes: string[];
}

export interface ExerciseSubmitResult {
  attempt: ExerciseAttemptRecord;
  status_before: MasteryStatus;
  status_after: MasteryStatus;
  knowledge_point: MasteryKnowledgePoint;
  message: string;
}

/* ------------------------------ 诊断 ------------------------------ */

export type DimensionLevel = "mastered" | "partial" | "not_started" | "no_data";
export type RouteAction = "study" | "review" | "verify" | "skip" | "remedial";

export interface DiagnosisKnowledgePoint {
  knowledge_point_code: string;
  knowledge_point_name: string;
  chapter_title: string;
  difficulty: string;
  status: MasteryStatus;
  status_label: string;
  /** evidence=有验证证据，claim=仅自述，none=无记录 */
  source: "evidence" | "claim" | "none";
  accuracy: number | null;
  verified_at: string | null;
}

export interface DiagnosisDimension {
  code: string;
  name: string;
  description: string;
  course_code: string;
  course_name: string | null;
  available: boolean;
  level: DimensionLevel;
  level_label: string;
  mastered_count: number;
  understood_count: number;
  applied_count: number;
  needs_review_count: number;
  not_started_count: number;
  total: number;
  coverage_percent: number;
  knowledge_points: DiagnosisKnowledgePoint[];
  note: string | null;
}

export interface RouteStep {
  order_index: number;
  knowledge_point_code: string;
  knowledge_point_name: string;
  course_code: string;
  course_name: string;
  action: RouteAction;
  action_label: string;
  reason: string;
  estimated_minutes: number;
}

export interface DiagnosisInput {
  learning_goal?: string;
  target_course_code?: string;
  self_reported_kp_codes?: string[];
  dimension_codes?: string[];
}

export interface DiagnosisReport {
  generated_at: string;
  learning_goal: string | null;
  target_course_code: string | null;
  target_course_name: string | null;
  dimensions: DiagnosisDimension[];
  route: RouteStep[];
  skippable_kp_codes: string[];
  needs_verification_kp_codes: string[];
  remedial_kp_codes: string[];
  summary: string;
  notes: string[];
}

export interface PlacementInput {
  course_code?: string;
  knowledge_point_codes?: string[];
  questions_per_point?: number;
}

export interface PlacementPlan {
  course_code: string | null;
  course_name: string | null;
  knowledge_points: DiagnosisKnowledgePoint[];
  question_counts: Record<string, number>;
  notes: string[];
}
