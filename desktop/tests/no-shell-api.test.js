"use strict";

/**
 * 批次 2 的构建期检查（设计文档第 5 节「界面层零壳专有 API 依赖」）。
 * 同时校验状态页的离线完整性与打包白名单，三项都不依赖 GUI 进程。
 */

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const REPO_ROOT = path.resolve(__dirname, "..", "..");
const FRONTEND_DIR = path.join(REPO_ROOT, "frontend");
const STATUS_PAGE = path.join(__dirname, "..", "src", "status.html");

const SKIP_DIRS = new Set(["node_modules", ".next", "coverage", "dist", ".git"]);
const SOURCE_EXTENSIONS = new Set([".ts", ".tsx", ".js", ".jsx", ".mjs", ".css"]);
const FORBIDDEN = [
  /\bdesktopStatus\b/,
  /\bipcRenderer\b/,
  /require\(\s*["']electron["']\s*\)/,
  /from\s+["']electron["']/,
  /\bwindow\.electron\b/,
];

function collectSources(dir, acc = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      if (!SKIP_DIRS.has(entry.name)) {
        collectSources(path.join(dir, entry.name), acc);
      }
      continue;
    }
    if (SOURCE_EXTENSIONS.has(path.extname(entry.name))) {
      acc.push(path.join(dir, entry.name));
    }
  }
  return acc;
}

test("Next.js 界面层零 Electron 专有接口引用", () => {
  const sources = collectSources(FRONTEND_DIR);
  assert.ok(sources.length > 20, "前端源码文件数异常，检查扫描范围");
  const hits = [];
  for (const file of sources) {
    const content = fs.readFileSync(file, "utf8");
    for (const pattern of FORBIDDEN) {
      if (pattern.test(content)) {
        hits.push(`${path.relative(REPO_ROOT, file)} → ${pattern}`);
      }
    }
  }
  assert.deepEqual(hits, [], `界面层出现壳专有接口：\n${hits.join("\n")}`);
});

test("preload 在 sandbox 下可加载：不 require 本地模块，判定与契约一致", () => {
  const preload = fs.readFileSync(path.join(__dirname, "..", "src", "preload.js"), "utf8");
  const guard = require("../src/preload-guard.js");

  // sandbox: true 时 preload 只能 require Electron 内置模块，
  // 本地相对模块会抛 "module not found" 并中止整个 preload。
  // 批次 6 GUI 实测踩到过：状态页按钮与标题栏标记同时失效。
  // 先剥离注释，避免把说明文字里的示例当成真实调用。
  const code = preload
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|\s)\/\/[^\n]*/g, "$1");
  const localRequires = code.match(/require\(\s*["']\.{1,2}\//g) ?? [];
  assert.deepEqual(localRequires, [], "preload 不得 require 本地模块");

  // 内联判定必须与 preload-guard.js 的契约一致（仅 file: 暴露状态接口）
  assert.equal(guard.shouldExposeStatusApi("file:"), true);
  assert.equal(guard.shouldExposeStatusApi("http:"), false);
  assert.match(preload, /protocol === "file:"/);

  // 标题栏环境标记只在界面页注入，状态页不需要
  assert.match(preload, /window\.location\.protocol === "http:"/);
  assert.match(preload, /root\.dataset\.shell = "desktop"/);
});

test("状态页自包含：无外部资源、含三态与可访问性降级", () => {
  const html = fs.readFileSync(STATUS_PAGE, "utf8");
  assert.match(html, /<script src="\.\/status-renderer\.js"><\/script>/);
  assert.doesNotMatch(html, /<script[^>]+src="https?:/);
  assert.doesNotMatch(html, /<link[^>]+href="https?:/);
  assert.match(html, /prefers-reduced-motion/);
  assert.match(html, /focus-visible/);
  assert.match(html, /--color-accent: #D8502A/);
  assert.match(html, /<h1/);
  assert.match(html, /data-state="starting"/);
  assert.equal((html.match(/<h1/g) || []).length, 1, "状态页只能有一个 h1");
  for (const id of ["state-title", "state-lede", "state-label", "state-seconds", "state-detail", "retry", "choose-dir"]) {
    assert.match(html, new RegExp(`id="${id}"`));
  }
  assert.ok(fs.existsSync(path.join(__dirname, "..", "src", "status-renderer.js")));
});

test("打包白名单排除数据、密钥与依赖，保留构建上下文", () => {
  const stage = require("../scripts/stage-project.js");
  const shouldCopy = stage.shouldCopy;
  const at = (...parts) => path.join(REPO_ROOT, ...parts);

  assert.equal(shouldCopy(at("backend", "app", "main.py")), true);
  assert.equal(shouldCopy(at("frontend", "app", "layout.tsx")), true);
  assert.equal(shouldCopy(at("frontend", "Dockerfile")), true);
  // 批次 3 自托管字体必须随安装包分发，离线窗口不能回退到 CDN
  assert.equal(
    shouldCopy(at("frontend", "public", "fonts", "ibm-plex-mono-latin-400-normal.woff2")),
    true,
  );
  assert.ok(
    fs.existsSync(at("frontend", "public", "fonts", "ibm-plex-mono-latin-400-normal.woff2")),
  );
  assert.equal(shouldCopy(at("backend", "data", "xiaoma.db")), false);
  assert.equal(shouldCopy(at("backend", "data", ".secret_key")), false);
  assert.equal(shouldCopy(at("backend", ".env")), false);
  assert.equal(shouldCopy(at("frontend", "node_modules", "next", "package.json")), false);
  assert.equal(shouldCopy(at("frontend", ".next", "BUILD_ID")), false);
  assert.equal(shouldCopy(at("backend", "app", "__pycache__", "main.cpython-314.pyc")), false);
});
