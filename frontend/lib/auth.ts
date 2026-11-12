/** 访问密码登录 API（PRD 11.1）。 */

import { api } from "@/lib/api";
import {
  clearAccessToken,
  getAccessToken,
  notifyUnauthorized,
  setAccessToken,
} from "@/lib/access-token";

export interface AuthStatus {
  required: boolean;
  authenticated: boolean;
}

interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
}

/** 查询当前部署是否需要登录，以及当前令牌是否有效。 */
export function getAuthStatus(): Promise<AuthStatus> {
  return api.get<AuthStatus>("/auth/status");
}

/** 使用访问密码登录；成功后令牌只保存在浏览器本地。 */
export async function login(password: string): Promise<void> {
  const data = await api.post<LoginResponse>("/auth/login", { password });
  setAccessToken(data.access_token);
}

/** 退出登录：通知后端吊销令牌（失败也不阻塞本地清理）。 */
export async function logout(): Promise<void> {
  try {
    await api.post<void>("/auth/logout");
  } catch {
    // 令牌可能已过期或后端不可达；退出登录始终应清理本地状态
  } finally {
    clearAccessToken();
    notifyUnauthorized();
  }
}

export function hasAccessToken(): boolean {
  return Boolean(getAccessToken());
}
