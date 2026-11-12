/** 访问密码登录令牌的浏览器本地存储。

令牌只保存在当前浏览器（localStorage），不写入 cookie 或 URL；
后端会话默认 24 小时过期，退出登录或令牌失效后需要重新输入密码。
*/

export const ACCESS_TOKEN_STORAGE_KEY = "xiaoma_access_token";
export const UNAUTHORIZED_EVENT = "xiaoma:unauthorized";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const token = window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
    return token && token.trim() ? token : null;
  } catch {
    return null;
  }
}

export function setAccessToken(token: string): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token);
}

export function clearAccessToken(): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
  } catch {
    // 隐私模式等场景下 localStorage 不可用：忽略即可
  }
}

/** 通知界面令牌已失效（由 API 层在收到 401 时触发）。 */
export function notifyUnauthorized(): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  }
}

export function authHeaders(): Record<string, string> {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}
