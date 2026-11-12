/**
 * 同源 API 代理（Next.js 服务端路由）。
 *
 * 浏览器只访问前端端口（/api/v1/...），由 Next.js 服务端转发到后端。
 * 好处：
 * - 局域网/公网部署时浏览器不需要知道后端地址，也不会错误请求访问者自己的
 *   localhost:8000；
 * - 访问密码 Bearer 令牌与 SSE 流都通过同源请求传递；
 * - Docker 中后端无需直接暴露到宿主机，减少攻击面。
 *
 * 后端地址由服务端环境变量 BACKEND_INTERNAL_URL 控制，默认本地开发
 * 使用 http://127.0.0.1:8000，Docker Compose 中为 http://backend:8000。
 */

const BACKEND_URL = (
  process.env.BACKEND_INTERNAL_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

const REQUEST_HEADERS_TO_SKIP = new Set([
  "host",
  "connection",
  "content-length",
  "accept-encoding",
  "transfer-encoding",
  "upgrade",
  "keep-alive",
]);

const RESPONSE_HEADERS_TO_SKIP = new Set([
  "content-encoding",
  "content-length",
  "transfer-encoding",
  "connection",
  "keep-alive",
]);

type RouteContext = { params: Promise<{ path: string[] }> };

async function proxy(request: Request, context: RouteContext): Promise<Response> {
  const { path } = await context.params;
  const requestUrl = new URL(request.url);
  const targetPath = path
    .map((segment) => encodeURIComponent(segment))
    .join("/");
  const target = `${BACKEND_URL}/api/v1/${targetPath}${requestUrl.search}`;

  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!REQUEST_HEADERS_TO_SKIP.has(key.toLowerCase())) {
      headers.set(key, value);
    }
  });

  const method = request.method.toUpperCase();
  const init: RequestInit & { duplex?: "half" } = {
    method,
    headers,
    redirect: "manual",
    signal: request.signal,
  };
  if (method !== "GET" && method !== "HEAD") {
    init.body = request.body;
    init.duplex = "half";
  }

  let upstream: Response;
  try {
    upstream = await fetch(target, init);
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      return new Response(null, { status: 499 });
    }
    return Response.json(
      { detail: "无法连接到后端服务，请确认后端已启动" },
      { status: 502 },
    );
  }

  const responseHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!RESPONSE_HEADERS_TO_SKIP.has(key.toLowerCase())) {
      responseHeaders.set(key, value);
    }
  });
  // 让反向代理/浏览器不要缓存 SSE 与 API 响应
  responseHeaders.set("Cache-Control", "no-store");
  if (upstream.headers.get("content-type")?.includes("text/event-stream")) {
    responseHeaders.set("X-Accel-Buffering", "no");
  }

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const OPTIONS = proxy;
