"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const ctrl = require("../src/service-controller");

const existsFor = (dirs) => (candidate) => dirs.some((dir) => candidate === path.join(dir, "docker-compose.yml"));

test("项目目录解析：环境变量优先级最高", () => {
  const result = ctrl.resolveProjectDir({
    isPackaged: false,
    appDir: "/repo/desktop/src",
    resourcesPath: "/resources",
    env: { XIAOMA_PROJECT_DIR: "/custom" },
    userConfig: { projectDir: "/saved" },
    existsSync: existsFor(["/custom", "/saved", "/repo"]),
  });
  assert.equal(result.path, "/custom");
  assert.equal(result.source, "env");
  assert.equal(result.candidates[0].present, true);
});

test("项目目录解析：用户配置覆盖打包资源", () => {
  const result = ctrl.resolveProjectDir({
    isPackaged: true,
    appDir: "/app/src",
    resourcesPath: "/resources",
    env: {},
    userConfig: { projectDir: "/saved" },
    existsSync: existsFor(["/saved", "/resources/project"]),
  });
  assert.equal(result.path, "/saved");
  assert.equal(result.source, "user-config");
});

test("项目目录解析：开发态回退到仓库根", () => {
  const repo = path.resolve("fixture-repo");
  const result = ctrl.resolveProjectDir({
    isPackaged: false,
    appDir: path.join(repo, "desktop", "src"),
    resourcesPath: "/resources",
    env: {},
    userConfig: {},
    existsSync: existsFor([repo]),
  });
  assert.equal(result.path, repo);
  assert.equal(result.source, "dev");
});

test("项目目录解析：打包态使用 resources/project", () => {
  const result = ctrl.resolveProjectDir({
    isPackaged: true,
    appDir: "/app/src",
    resourcesPath: "/resources",
    env: {},
    userConfig: {},
    existsSync: existsFor(["/resources/project"]),
  });
  assert.equal(result.path, path.join("/resources", "project"));
  assert.equal(result.source, "resources");
});

test("项目目录解析：无有效候选时返回 null，不猜测目录", () => {
  const result = ctrl.resolveProjectDir({
    isPackaged: false,
    appDir: "/repo/desktop/src",
    resourcesPath: "/resources",
    env: {},
    userConfig: {},
    existsSync: () => false,
  });
  assert.equal(result.path, null);
  assert.equal(result.source, null);
  assert.ok(result.candidates.every((item) => item.present === false));
});

test("Compose 命令构造：动作白名单与工作目录", () => {
  assert.deepEqual(ctrl.buildComposeCommand("up-build", "/repo"), {
    command: "docker",
    args: ["compose", "up", "-d", "--build"],
    cwd: "/repo",
  });
  assert.deepEqual(ctrl.buildComposeCommand("ps", "/repo").args, [
    "compose", "ps", "--format", "json",
  ]);
  assert.deepEqual(ctrl.buildComposeCommand("up", "/repo").args, ["compose", "up", "-d"]);
  assert.throws(() => ctrl.buildComposeCommand("rm -rf", "/repo"), /未知的 Compose 动作/);
  assert.throws(() => ctrl.buildComposeCommand("up", null), /工程目录未确定/);
});

test("Compose ps 输出解析：数组、逐行 JSON、空输出与非法内容", () => {
  assert.equal(ctrl.parseComposePs('[{"Name":"xiaoma-backend"}]').length, 1);
  assert.equal(ctrl.parseComposePs('{"Name":"xiaoma-backend"}').length, 1);
  assert.equal(
    ctrl.parseComposePs('{"Name":"a"}\n{"Name":"b"}').length,
    2,
  );
  assert.deepEqual(ctrl.parseComposePs(""), []);
  assert.equal(ctrl.parseComposePs("not-json-at-all"), null);
});

test("容器已存在时只拉起，不存在或状态未知时首次构建", () => {
  assert.equal(ctrl.decideComposeAction([]), "up-build");
  assert.equal(ctrl.decideComposeAction(null), "up-build");
  assert.equal(ctrl.decideComposeAction([{ Name: "xiaoma-backend" }]), "up");
});

test("健康状态机：成功进 ready，宽限期内失败仍为 starting", () => {
  const initial = ctrl.createInitialState(1_000);
  const pending = ctrl.reduceHealthState(
    initial,
    { type: "poll", ok: false, error: "service-unreachable" },
    2_000,
  );
  assert.equal(pending.state, ctrl.STATE.STARTING);
  assert.equal(pending.attempts, 1);
  assert.equal(pending.elapsedMs, 1_000);

  const ready = ctrl.reduceHealthState(
    pending,
    { type: "poll", ok: true, version: "1.4.0" },
    3_000,
  );
  assert.equal(ready.state, ctrl.STATE.READY);
  assert.equal(ready.version, "1.4.0");
  assert.equal(ready.error, null);
});

test("健康状态机：超过迁移宽限期才判失败，且 reset 重新开始", () => {
  const initial = ctrl.createInitialState(0);
  const failed = ctrl.reduceHealthState(
    initial,
    { type: "poll", ok: false, error: "timeout" },
    ctrl.STARTUP_GRACE_MS,
  );
  assert.equal(failed.state, ctrl.STATE.FAILED);
  assert.equal(failed.error, "timeout");

  const timedOut = ctrl.reduceHealthState(
    initial,
    { type: "timeout", message: "已超时" },
    1_000,
  );
  assert.equal(timedOut.state, ctrl.STATE.FAILED);
  assert.equal(timedOut.message, "已超时");

  const reset = ctrl.reduceHealthState(failed, { type: "reset" }, 500_000);
  assert.equal(reset.state, ctrl.STATE.STARTING);
  assert.equal(reset.startedAt, 500_000);
  assert.equal(reset.attempts, 0);
});

test("错误分类：给出可操作的中文结论，不吞掉异常", () => {
  assert.equal(
    ctrl.classifyFailure(new Error("failed to connect to the docker API: daemon is not running")).code,
    "docker-unavailable",
  );
  assert.equal(ctrl.classifyFailure(new Error("fetch failed: ECONNREFUSED")).code, "service-unreachable");
  assert.equal(
    ctrl.classifyFailure(new Error("anything"), { missingProjectDir: true }).code,
    "project-missing",
  );
  assert.equal(ctrl.classifyFailure(new Error("")).code, "unknown");
  assert.match(
    ctrl.classifyFailure(new Error("daemon is not running")).message,
    /Docker Desktop/,
  );
});

test("健康响应校验：只认 status=ok 且带 version 的响应", () => {
  assert.equal(ctrl.isHealthyResponse({ status: "ok", version: "1.4.0" }), true);
  assert.equal(ctrl.isHealthyResponse({ status: "ok" }), false);
  assert.equal(ctrl.isHealthyResponse({ status: "degraded", version: "1.4.0" }), false);
  assert.equal(ctrl.isHealthyResponse(null), false);
});
