"use strict";

/**
 * 窗口壳的服务启动控制器：只放确定性逻辑，不 import electron。
 *
 * 这样主进程可以用真实 Docker 调用它，测试可以用注入的 fetch / existsSync
 * 覆盖同一套状态机与命令构造，不需要启动 GUI（图形界面进程）。
 * 对应 docs/V1.4技术设计与契约.md 第 5 节「启动本地服务 → 轮询健康检查」。
 */

const path = require("node:path");

/** 数据库迁移首次需要 30–90 秒，留 120 秒宽限期，期间连接失败不判为失败。 */
const STARTUP_GRACE_MS = 120_000;
/** 健康检查轮询间隔。 */
const POLL_INTERVAL_MS = 2_000;
/** 前端同源服务地址与经 Next.js 代理的健康检查路径。 */
const APP_URL = "http://127.0.0.1:3000";
const HEALTH_URL = `${APP_URL}/api/v1/health`;

const STATE = Object.freeze({
  STARTING: "starting",
  READY: "ready",
  FAILED: "failed",
});

/**
 * 解析 Compose 工程目录。
 *
 * 优先级：环境变量 → 用户配置（窗口内「选择项目目录」写入）→ 打包资源 → 开发仓库。
 * 只有包含 docker-compose.yml 的候选才被选中，避免窗口加载一个空目录后
 * 报出与真实原因无关的错误。
 *
 * @param {object} options
 * @param {boolean} options.isPackaged 是否为打包后的应用
 * @param {string} options.appDir 主进程所在目录（desktop/src）
 * @param {string} options.resourcesPath Electron 的 process.resourcesPath
 * @param {object} options.env 环境变量（默认 process.env）
 * @param {object} options.userConfig userData/config.json 的内容
 * @param {(p: string) => boolean} options.existsSync 注入的文件存在判断
 */
function resolveProjectDir(options) {
  const {
    isPackaged,
    appDir,
    resourcesPath,
    env = {},
    userConfig = {},
    existsSync,
  } = options;

  const candidates = [];
  const push = (value, source) => {
    if (typeof value === "string" && value.trim()) {
      candidates.push({ path: value.trim(), source });
    }
  };

  push(env.XIAOMA_PROJECT_DIR, "env");
  push(userConfig.projectDir, "user-config");
  if (isPackaged) {
    candidates.push({ path: path.join(resourcesPath, "project"), source: "resources" });
  } else {
    // desktop/src -> desktop -> 仓库根
    candidates.push({ path: path.resolve(appDir, "..", ".."), source: "dev" });
  }

  const checked = candidates.map((item) => ({
    ...item,
    present: existsSync(path.join(item.path, "docker-compose.yml")),
  }));
  const found = checked.find((item) => item.present);

  return {
    path: found ? found.path : null,
    source: found ? found.source : null,
    candidates: checked,
  };
}

/** 构造 docker compose 命令。动作白名单防止拼装任意命令。 */
function buildComposeCommand(action, projectDir) {
  const argsByAction = {
    ps: ["compose", "ps", "--format", "json"],
    up: ["compose", "up", "-d"],
    "up-build": ["compose", "up", "-d", "--build"],
    stop: ["compose", "stop"],
  };
  const args = argsByAction[action];
  if (!args) {
    throw new Error(`未知的 Compose 动作：${action}`);
  }
  if (!projectDir) {
    throw new Error("Compose 工程目录未确定");
  }
  return { command: "docker", args, cwd: projectDir };
}

/**
 * 解析 `docker compose ps --format json` 输出。
 * 新版输出 JSON 数组，部分版本按行输出多个 JSON 对象；无法解析时返回 null，
 * 调用方据此退回到「首次构建」动作，不把解析失败误判为「服务已运行」。
 */
function parseComposePs(stdout) {
  const text = String(stdout ?? "").trim();
  if (!text) {
    return [];
  }
  try {
    const parsed = JSON.parse(text);
    return Array.isArray(parsed) ? parsed : [parsed];
  } catch {
    const lines = text.split(/\r?\n/).filter(Boolean);
    try {
      return lines.map((line) => JSON.parse(line));
    } catch {
      return null;
    }
  }
}

/** 容器已存在时只拉起、不重建镜像；不存在或状态未知时执行首次构建。 */
function decideComposeAction(psResult) {
  if (psResult === null || psResult.length === 0) {
    return "up-build";
  }
  return "up";
}

/** 初始状态快照，状态页首次拉取与轮询推送使用同一形状。 */
function createInitialState(now) {
  return {
    state: STATE.STARTING,
    attempts: 0,
    startedAt: now,
    elapsedMs: 0,
    message: "正在连接本地服务…",
    version: null,
    error: null,
  };
}

/**
 * 健康检查状态机（纯函数）。
 *
 * 宽限期内连接失败保持 starting 并继续轮询；健康检查成功立即 ready；
 * 超过宽限期或显式 timeout 事件才 failed。绝不把「还没连上」写成「已就绪」。
 *
 * @param {object} prev 上一状态
 * @param {{type: "poll"|"timeout"|"reset", ok?: boolean, version?: string, error?: string, message?: string}} event
 * @param {number} now 当前时间戳（毫秒）
 */
function reduceHealthState(prev, event, now) {
  if (event.type === "reset") {
    return createInitialState(now);
  }
  const elapsedMs = Math.max(0, now - prev.startedAt);
  const attempts = prev.attempts + (event.type === "poll" ? 1 : 0);

  if (event.type === "poll" && event.ok) {
    return {
      ...prev,
      state: STATE.READY,
      attempts,
      elapsedMs,
      message: "服务已就绪，正在进入工作台…",
      version: event.version ?? null,
      error: null,
    };
  }

  if (event.type === "timeout" || elapsedMs >= STARTUP_GRACE_MS) {
    return {
      ...prev,
      state: STATE.FAILED,
      attempts,
      elapsedMs,
      message: event.message ?? "本地服务启动超时，请检查 Docker Desktop 是否运行。",
      error: event.error ?? "timeout",
    };
  }

  return {
    ...prev,
    state: STATE.STARTING,
    attempts,
    elapsedMs,
    message: prev.message,
    version: null,
    error: event.error ?? null,
  };
}

/**
 * 把底层错误归类为可操作的中文提示。
 * service-unreachable 属于宽限期内的正常现象，由调用方继续轮询。
 */
function classifyFailure(error, context = {}) {
  const text = String((error && error.message) || error || "");
  if (context.missingProjectDir) {
    return {
      code: "project-missing",
      message: "未找到 docker-compose.yml。请在「文件 → 选择项目目录」中指定小码项目目录。",
    };
  }
  if (/dockerDesktopLinuxEngine|daemon|cannot connect|not running|ENOENT|spawn/i.test(text)) {
    return {
      code: "docker-unavailable",
      message: "未检测到运行中的 Docker Desktop。请先启动 Docker Desktop，再点击重试。",
    };
  }
  if (/ECONNREFUSED|fetch failed|aborted|timeout/i.test(text)) {
    return {
      code: "service-unreachable",
      message: "本地服务尚未响应，数据库迁移可能需要 30–90 秒，正在继续等待…",
    };
  }
  if (/permission|denied|access/i.test(text)) {
    return {
      code: "docker-permission",
      message: "Docker 拒绝了本次操作，请确认当前账号有权限运行容器。",
    };
  }
  return {
    code: "unknown",
    message: `启动失败：${text || "未知错误"}`,
  };
}

/** 校验健康检查响应体，防止把任意 200 响应当成后端就绪。 */
function isHealthyResponse(payload) {
  return Boolean(payload) && payload.status === "ok" && typeof payload.version === "string";
}

module.exports = {
  APP_URL,
  HEALTH_URL,
  STATE,
  STARTUP_GRACE_MS,
  POLL_INTERVAL_MS,
  resolveProjectDir,
  buildComposeCommand,
  parseComposePs,
  decideComposeAction,
  createInitialState,
  reduceHealthState,
  classifyFailure,
  isHealthyResponse,
};
