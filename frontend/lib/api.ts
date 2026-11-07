/** 统一 API 请求封装：所有前端请求必须经由本模块访问后端。 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const DEFAULT_TIMEOUT_MS = 10_000;

/** 后端请求异常：status 为 0 表示网络/超时/流中断类错误。 */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** 从后端统一错误结构 {"detail": ...} 中提取可读信息。 */
async function extractErrorMessage(res: Response): Promise<string> {
  try {
    const data: unknown = await res.json();
    if (typeof data === "object" && data !== null && "detail" in data) {
      const detail = (data as { detail?: unknown }).detail;
      if (typeof detail === "string" && detail.trim()) {
        return detail;
      }
      if (Array.isArray(detail)) {
        // FastAPI 参数校验错误：detail 为数组
        const messages = detail.map((item) => {
          if (typeof item === "object" && item !== null && "msg" in item) {
            return String((item as { msg: unknown }).msg);
          }
          return "参数不合法";
        });
        if (messages.length > 0) {
          return messages.join("；");
        }
      }
    }
  } catch {
    // 响应体不是 JSON：回退到状态码提示
  }
  return `请求失败（HTTP ${res.status}）`;
}

/** 把任意异常转换为可展示的中文提示。 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "发生未知错误，请稍后重试";
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const { headers: optHeaders, ...rest } = options;

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...rest,
      signal: options.signal ?? AbortSignal.timeout(DEFAULT_TIMEOUT_MS),
      headers: { "Content-Type": "application/json", ...(optHeaders ?? {}) },
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "TimeoutError") {
      throw new ApiError(0, "请求超时，请稍后重试");
    }
    if (err instanceof DOMException && err.name === "AbortError") {
      throw err;
    }
    throw new ApiError(0, "无法连接到服务器，请确认后端服务已启动");
  }

  if (!res.ok) {
    throw new ApiError(res.status, await extractErrorMessage(res));
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  /**
   * timeoutMs 用于可能长时间运行的请求（如 AI 变式题生成与验证）；
   * 不传时使用默认 10 秒超时。
   */
  post: <T>(path: string, body?: unknown, timeoutMs?: number) =>
    request<T>(path, {
      method: "POST",
      body: body === undefined ? undefined : JSON.stringify(body),
      ...(timeoutMs ? { signal: AbortSignal.timeout(timeoutMs) } : {}),
    }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

export interface SseEvent {
  event: string;
  data: unknown;
}

/**
 * 发起 POST 并以 SSE 方式逐条回调服务端事件。
 *
 * 不使用固定超时：教学回复可能持续较长时间，由调用方通过 AbortSignal 取消。
 * HTTP 非 2xx（如未配置默认模型返回 409）在流开始前以 ApiError 抛出；
 * 网络中断在流开始后以 ApiError(status=0) 抛出。
 */
export async function streamApi(
  path: string,
  body: unknown,
  onEvent: (event: SseEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      body: JSON.stringify(body),
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw err;
    }
    throw new ApiError(0, "无法连接到服务器，请确认后端服务已启动");
  }

  if (!res.ok) {
    throw new ApiError(res.status, await extractErrorMessage(res));
  }

  const reader = res.body?.getReader();
  if (!reader) {
    throw new ApiError(0, "当前浏览器不支持流式响应");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  const dispatch = (block: string) => {
    let eventName = "message";
    const dataLines: string[] = [];
    for (const rawLine of block.split("\n")) {
      const line = rawLine.endsWith("\r") ? rawLine.slice(0, -1) : rawLine;
      if (line.startsWith("event:")) {
        eventName = line.slice("event:".length).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice("data:".length).trimStart());
      }
    }
    if (dataLines.length === 0) {
      return;
    }
    try {
      onEvent({ event: eventName, data: JSON.parse(dataLines.join("\n")) });
    } catch {
      throw new ApiError(0, "服务器返回了无法解析的流式数据");
    }
  };

  while (true) {
    let chunk: ReadableStreamReadResult<Uint8Array>;
    try {
      chunk = await reader.read();
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        throw err;
      }
      throw new ApiError(0, "连接中断，回复可能未完整保存");
    }
    if (chunk.done) {
      break;
    }
    buffer = (buffer + decoder.decode(chunk.value, { stream: true })).replace(
      /\r\n/g,
      "\n",
    );
    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      dispatch(block);
      boundary = buffer.indexOf("\n\n");
    }
  }

  buffer = (buffer + decoder.decode()).replace(/\r\n/g, "\n");
  if (buffer.trim()) {
    dispatch(buffer);
  }
}
