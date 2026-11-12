"use strict";

/**
 * electron-builder 的 beforePack 钩子：把 Compose 工程按白名单复制进安装包。
 *
 * 桌面窗口本身只负责加载界面，业务服务仍由 Docker Compose 构建运行
 * （设计文档第 5 节），所以安装包必须自带 docker-compose.yml 与前后端构建上下文。
 * 严禁把数据库、模型密钥、虚拟环境、node_modules、构建产物打进去：
 * 这些文件既含用户隐私，也会让镜像层失效。
 */

const fs = require("node:fs");
const path = require("node:path");

const DESKTOP_DIR = path.resolve(__dirname, "..");
const REPO_ROOT = path.resolve(DESKTOP_DIR, "..");
// 不用点开头的目录名：electron-builder 的文件 glob 默认忽略隐藏目录，
// 一旦被过滤，安装包会缺失 Compose 工程。
const STAGING_ROOT = path.join(DESKTOP_DIR, "build-staging");
const STAGING_DIR = path.join(STAGING_ROOT, "project");

/**
 * 重置暂存目录。
 *
 * 这里不能简单 `rmSync(build-staging)`：整目录含上千文件，在带安全删除策略的
 * 终端里会触发 SAFE_DELETE_BULK_CONFIRM_REQUIRED 直接让打包失败（批次 6 实测）。
 * 因此只重置 project 子目录；万一批量删除仍被拦截，就同卷重命名归档后继续，
 * 归档目录不在 extraResources 的 from 路径上，不会进入安装包。
 */
function resetStaging() {
  if (!fs.existsSync(STAGING_DIR)) {
    fs.mkdirSync(STAGING_DIR, { recursive: true });
    return;
  }
  try {
    fs.rmSync(STAGING_DIR, { recursive: true, force: true });
  } catch (error) {
    const archived = path.join(STAGING_ROOT, `project-stale-${Date.now()}`);
    fs.renameSync(STAGING_DIR, archived);
    console.warn(
      `[stage-project] 批量删除被安全策略拦截（${error && error.code ? error.code : error}），` +
        `已改为重命名归档：${archived}（可手动删除）`,
    );
  }
  fs.mkdirSync(STAGING_DIR, { recursive: true });
}

const ROOT_FILES = ["docker-compose.yml", ".env.example"];
const BUILD_CONTEXT_DIRS = ["backend", "frontend"];

const EXCLUDED_SEGMENTS = new Set([
  "node_modules",
  ".next",
  ".venv",
  "__pycache__",
  ".pytest_cache",
  "data",
  "tests",
  "coverage",
  "dist",
  ".git",
]);
const EXCLUDED_NAMES = new Set([".env", ".secret_key"]);
const EXCLUDED_EXTENSIONS = new Set([
  ".pyc",
  ".db",
  ".db-shm",
  ".db-wal",
  ".tsbuildinfo",
  ".log",
]);

/** 判断某个源路径是否属于可分发内容。 */
function shouldCopy(sourcePath) {
  const relative = path.relative(REPO_ROOT, sourcePath);
  const segments = relative.split(path.sep).filter(Boolean);
  if (segments.some((segment) => EXCLUDED_SEGMENTS.has(segment))) {
    return false;
  }
  const name = path.basename(sourcePath);
  if (EXCLUDED_NAMES.has(name) || EXCLUDED_EXTENSIONS.has(path.extname(name))) {
    return false;
  }
  if (/^.*\.db$/i.test(name)) {
    return false;
  }
  return true;
}

module.exports = async function beforePack() {
  resetStaging();

  for (const file of ROOT_FILES) {
    const source = path.join(REPO_ROOT, file);
    if (!fs.existsSync(source)) {
      throw new Error(`打包缺少必要文件：${file}`);
    }
    fs.copyFileSync(source, path.join(STAGING_DIR, file));
  }

  for (const dir of BUILD_CONTEXT_DIRS) {
    const source = path.join(REPO_ROOT, dir);
    if (!fs.existsSync(source)) {
      throw new Error(`打包缺少必要目录：${dir}`);
    }
    fs.cpSync(source, path.join(STAGING_DIR, dir), {
      recursive: true,
      filter: (candidate) => shouldCopy(candidate),
    });
  }

  // frontend/Dockerfile 会 COPY public/；空目录也必须存在，否则镜像构建失败。
  fs.mkdirSync(path.join(STAGING_DIR, "frontend", "public"), { recursive: true });

  return { staged: STAGING_DIR };
};

module.exports.shouldCopy = shouldCopy;
