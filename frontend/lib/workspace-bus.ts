/**
 * V1.4 批次 3：窗口内视图/会话事件总线。
 *
 * 设计约束（技术设计 §2.3 / §8.3）：三栏骨架挂在 layout 上始终存在，
 * 左栏的会话操作需要通知中栏的既有对话实现，又不能让界面层依赖
 * Electron 专有接口。因此只用浏览器原生 CustomEvent 传递纯数据，
 * 浏览器 / 移动端辅助通道同样可用。
 *
 * 本模块不读取 DOM 之外的任何状态，parse 为纯函数，便于单测。
 */

export const WORKSPACE_EVENT_NAME = "xiaoma:workspace";

export type WorkspaceBusEvent =
  | { type: "conversation:new" }
  | { type: "conversation:select"; id: string }
  | { type: "conversation:deleted"; id: string }
  /** 会话列表发生变化（新建 / 重命名 / 删除 / 流结束），左栏应重新拉取真实数据。 */
  | { type: "conversation:changed" }
  /** 学习业务数据发生变化，右侧四面板应刷新。 */
  | { type: "panels:refresh" };

const VALID_TYPES: ReadonlySet<string> = new Set([
  "conversation:new",
  "conversation:select",
  "conversation:deleted",
  "conversation:changed",
  "panels:refresh",
]);

/** 只接受结构完整的事件；任何畸形载荷都被丢弃，绝不把未知数据交给组件。 */
export function parseWorkspaceEvent(detail: unknown): WorkspaceBusEvent | null {
  if (typeof detail !== "object" || detail === null) {
    return null;
  }
  const event = detail as Record<string, unknown>;
  if (typeof event.type !== "string" || !VALID_TYPES.has(event.type)) {
    return null;
  }
  switch (event.type) {
    case "conversation:new":
    case "conversation:changed":
    case "panels:refresh":
      return { type: event.type };
    case "conversation:select":
    case "conversation:deleted":
      return typeof event.id === "string" && event.id.length > 0
        ? { type: event.type, id: event.id }
        : null;
    default:
      return null;
  }
}

/** 在服务端渲染或缺少 CustomEvent 的环境下静默返回 false，不抛异常。 */
export function publishWorkspaceEvent(event: WorkspaceBusEvent): boolean {
  if (
    typeof window === "undefined" ||
    typeof window.CustomEvent === "undefined"
  ) {
    return false;
  }
  window.dispatchEvent(
    new window.CustomEvent(WORKSPACE_EVENT_NAME, { detail: event }),
  );
  return true;
}

/** 返回取消订阅函数；监听到的每个事件都先经过纯函数校验。 */
export function subscribeWorkspaceEvent(
  listener: (event: WorkspaceBusEvent) => void,
): () => void {
  if (typeof window === "undefined") {
    return () => undefined;
  }
  const handler = (raw: Event) => {
    const detail = (raw as CustomEvent<unknown>).detail;
    const event = parseWorkspaceEvent(detail);
    if (event) {
      listener(event);
    }
  };
  window.addEventListener(WORKSPACE_EVENT_NAME, handler);
  return () => window.removeEventListener(WORKSPACE_EVENT_NAME, handler);
}
