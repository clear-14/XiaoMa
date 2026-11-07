/** 展示用格式化工具（仅用于客户端渲染，避免服务端/客户端时区差异）。 */

const DIFFICULTY_LABELS: Record<string, string> = {
  beginner: "入门",
  intermediate: "进阶",
  advanced: "高级",
};

const TASK_STATUS_LABELS: Record<string, string> = {
  pending: "待开始",
  learning: "学习中",
  completed: "已完成",
};

export function difficultyLabel(value: string): string {
  return DIFFICULTY_LABELS[value] ?? value;
}

export function taskStatusLabel(value: string): string {
  return TASK_STATUS_LABELS[value] ?? value;
}

/** 后端时间为无时区的 UTC，浏览器按本地时区展示。 */
function parseBackendDate(value: string): Date {
  if (/(?:Z|[+-]\d{2}:?\d{2})$/.test(value)) {
    return new Date(value);
  }
  return new Date(`${value}Z`);
}

export function formatDateTime(value: string): string {
  const date = parseBackendDate(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

/** 会话列表使用：当天显示时分，其他日期显示月日。 */
export function formatConversationTime(value: string): string {
  const date = parseBackendDate(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  const now = new Date();
  const sameDay =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate();
  return new Intl.DateTimeFormat("zh-CN", {
    ...(sameDay
      ? { hour: "2-digit", minute: "2-digit", hour12: false }
      : { month: "numeric", day: "numeric" }),
  }).format(date);
}

/** 任务日期（YYYY-MM-DD）直接格式化，不做时区换算。 */
export function formatDateOnly(value: string): string {
  const parts = value.split("-");
  if (parts.length !== 3) {
    return value;
  }
  const [year, month, day] = parts;
  return `${year} 年 ${Number(month)} 月 ${Number(day)} 日`;
}
