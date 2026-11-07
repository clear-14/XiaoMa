/** 与后端 API 保持一致的数据类型（字段名不转换）。 */

/* ------------------------------ 聊天会话 ------------------------------ */

export interface ConversationKnowledgePoint {
  code: string;
  name: string;
  chapter_code: string;
  chapter_title: string;
}

export type MessageRole = "user" | "assistant";
export type MessageStatus = "completed" | "error";

export interface ConversationMessage {
  id: string;
  role: MessageRole;
  /** status=error 时为已生成的部分内容（可能为空字符串） */
  content: string;
  status: MessageStatus;
  /** status=error 时的失败原因 */
  error_message: string | null;
  model_name: string | null;
  created_at: string;
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
  result_status?: "ok" | "unavailable";
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

export interface DailyTask {
  id: string;
  plan_id: string;
  task_date: string;
  day_index: number;
  status: "pending" | "learning" | "completed";
  started_at: string | null;
  completed_at: string | null;
  knowledge_point: DailyTaskKnowledgePoint;
}

export interface TodayTasks {
  task_date: string;
  generated: boolean;
  tasks: DailyTask[];
  note: string | null;
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
