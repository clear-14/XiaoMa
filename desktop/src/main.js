"use strict";

/**
 * 小码 V1.4 桌面窗口壳主进程。
 *
 * 职责边界（docs/V1.4技术设计与契约.md 第 5 节）：
 * - 单实例、无地址栏窗口、尺寸位置记忆、应用菜单与快捷键；
 * - 启动本地 Docker Compose 服务，轮询 /api/v1/health 直到就绪；
 * - 服务未就绪或失败时在窗口内显示状态页，不把浏览器错误页抛给用户；
 * - 就绪后加载同一套 Next.js 界面；界面层不调用任何 Electron 专有接口。
 *
 * 本文件不停止本地服务：产品文档只定义了「打开软件时启动服务」，
 * 关闭窗口后容器继续由 Docker 运行，下次打开可直接复用。
 */

const { app, BrowserWindow, Menu, dialog, shell, ipcMain } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const ctrl = require("./service-controller");
const { buildMenu } = require("./menu");

const APP_DIR = __dirname;
const STATUS_PAGE = path.join(APP_DIR, "status.html");

const configFile = () => path.join(app.getPath("userData"), "config.json");
const windowStateFile = () => path.join(app.getPath("userData"), "window-state.json");

let mainWindow = null;
let currentState = ctrl.createInitialState(Date.now());
/** 每轮启动流程的唯一编号；重试时递增，让旧轮询链自然失效。 */
let startupToken = 0;
let pollTimer = null;
let startupBusy = false;

function readJson(file, fallback) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return fallback;
  }
}

function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(value, null, 2), "utf8");
}

/** 推送状态快照；状态页先 getState 再订阅推送，两种顺序都能拿到当前状态。 */
function publish(state) {
  currentState = state;
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send("status:state", state);
  }
}

function publishFailure(error, context = {}) {
  const info = ctrl.classifyFailure(error, context);
  publish({
    ...currentState,
    state: ctrl.STATE.FAILED,
    message: info.message,
    error: info.code,
    elapsedMs: Math.max(0, Date.now() - currentState.startedAt),
  });
}

/** 执行固定的 docker compose 命令；命令与参数均来自白名单，不拼接用户输入。 */
function runCommand(spec) {
  return new Promise((resolve, reject) => {
    const child = spawn(spec.command, spec.args, {
      cwd: spec.cwd,
      env: process.env,
      shell: process.platform === "win32",
      windowsHide: true,
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) {
        resolve({ stdout, stderr });
      } else {
        const detail = stderr.trim() || stdout.trim() || "无输出";
        reject(new Error(`docker ${spec.args.join(" ")} 退出码 ${code}：${detail}`));
      }
    });
  });
}

function resolveDir() {
  return ctrl.resolveProjectDir({
    isPackaged: app.isPackaged,
    appDir: APP_DIR,
    resourcesPath: process.resourcesPath,
    env: process.env,
    userConfig: readJson(configFile(), {}),
    existsSync: fs.existsSync,
  });
}

async function fetchHealth() {
  const response = await fetch(ctrl.HEALTH_URL, {
    signal: AbortSignal.timeout(5_000),
  });
  if (!response.ok) {
    throw new Error(`健康检查返回 HTTP ${response.status}`);
  }
  const payload = await response.json();
  if (!ctrl.isHealthyResponse(payload)) {
    throw new Error("健康检查响应缺少 status=ok 或 version 字段");
  }
  return payload;
}

/**
 * 启动服务容器。首次构建镜像不计入 120 秒宽限期：
 * 镜像构建可能远长于迁移时间，宽限期只约束「容器起来后等待健康检查」。
 *
 * 批次 8：先探活再执行 compose。已有健康的小码服务（容器仍在运行、或开发者
 * 已启动同一份工程）时直接复用——否则固定 container_name 会让 up 直接失败，
 * 而且在失败之前还会白构建一轮镜像。
 *
 * @returns {Promise<"ready"|"started"|"failed"|"stale">}
 */
async function startServices(token) {
  const resolved = resolveDir();
  if (!resolved.path) {
    publishFailure(new Error("未找到 docker-compose.yml"), { missingProjectDir: true });
    return "failed";
  }

  try {
    const payload = await fetchHealth();
    if (token !== startupToken) {
      return "stale";
    }
    publish({
      ...ctrl.createInitialState(Date.now()),
      state: ctrl.STATE.READY,
      message: "检测到本地服务已就绪，正在进入工作台…",
      version: payload.version,
    });
    return "ready";
  } catch {
    // 探活没通过：服务确实没起来，按原流程启动容器。
  }
  if (token !== startupToken) {
    return "stale";
  }

  let action = "up-build";
  try {
    const ps = await runCommand(ctrl.buildComposeCommand("ps", resolved.path));
    action = ctrl.decideComposeAction(ctrl.parseComposePs(ps.stdout));
  } catch (error) {
    const info = ctrl.classifyFailure(error);
    if (info.code === "docker-unavailable") {
      publishFailure(error);
      return "failed";
    }
    // 其他 ps 失败（例如编排从未创建）按首次构建处理，由 up 给出最终结论。
    action = "up-build";
  }
  if (token !== startupToken) {
    return "stale";
  }

  publish({
    ...currentState,
    message: action === "up-build" ? "正在构建并启动本地服务容器…" : "正在拉起本地服务容器…",
  });
  await runCommand(ctrl.buildComposeCommand(action, resolved.path));
  return "started";
}

/** 服务就绪后加载业务界面（探活复用与轮询就绪两条路径共用）。 */
async function loadWorkspace() {
  if (mainWindow && !mainWindow.isDestroyed()) {
    await mainWindow.loadURL(ctrl.APP_URL);
  }
}

async function pollOnce(token) {
  if (token !== startupToken) {
    return;
  }
  let event;
  try {
    const payload = await fetchHealth();
    event = { type: "poll", ok: true, version: payload.version };
  } catch (error) {
    const info = ctrl.classifyFailure(error);
    event = { type: "poll", ok: false, error: info.code };
  }
  if (token !== startupToken) {
    return;
  }

  const next = ctrl.reduceHealthState(currentState, event, Date.now());
  publish(next);

  if (next.state === ctrl.STATE.READY) {
    await loadWorkspace();
    return;
  }
  if (next.state === ctrl.STATE.FAILED) {
    return;
  }
  pollTimer = setTimeout(() => {
    void pollOnce(token);
  }, ctrl.POLL_INTERVAL_MS);
}

async function startup() {
  const token = ++startupToken;
  if (pollTimer) {
    clearTimeout(pollTimer);
    pollTimer = null;
  }
  if (startupBusy) {
    return;
  }
  startupBusy = true;
  publish({ ...ctrl.createInitialState(Date.now()), message: "正在连接本地服务…" });

  try {
    const outcome = await startServices(token);
    if (token !== startupToken || outcome === "stale" || outcome === "failed") {
      return;
    }
    if (outcome === "ready") {
      // 已有可用服务：不重启容器，直接进工作台。
      await loadWorkspace();
      return;
    }
    // 容器已启动，从这里重新开始计算迁移等待宽限期。
    publish({
      ...ctrl.createInitialState(Date.now()),
      message: "容器已启动，正在等待数据库迁移完成（30–90 秒）…",
    });
    await pollOnce(token);
  } catch (error) {
    if (token === startupToken) {
      publishFailure(error);
    }
  } finally {
    if (token === startupToken) {
      startupBusy = false;
    }
  }
}

async function chooseProjectDir() {
  if (!mainWindow || mainWindow.isDestroyed()) {
    return;
  }
  const result = await dialog.showOpenDialog(mainWindow, {
    title: "选择小码项目目录（需包含 docker-compose.yml）",
    properties: ["openDirectory"],
  });
  if (result.canceled || result.filePaths.length === 0) {
    return;
  }
  const dir = result.filePaths[0];
  if (!fs.existsSync(path.join(dir, "docker-compose.yml"))) {
    await dialog.showMessageBox(mainWindow, {
      type: "warning",
      title: "目录无效",
      message: "该目录不包含 docker-compose.yml，项目目录未更改。",
    });
    return;
  }
  writeJson(configFile(), { ...readJson(configFile(), {}), projectDir: dir });
  await startup();
}

const actions = {
  chooseProjectDir: () => void chooseProjectDir(),
  retry: () => void startup(),
  reload: () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.reload();
    }
  },
  toggleDevTools: () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.toggleDevTools();
    }
  },
  openInBrowser: () => void shell.openExternal(ctrl.APP_URL),
  about: () =>
    void dialog.showMessageBox(mainWindow, {
      type: "info",
      title: "关于小码",
      message: "小码 Xiaoma 1.4.1",
      detail:
        "桌面窗口壳 1.4.1。业务界面由本地 Next.js 服务提供，数据与模型服务由 Docker Compose 容器运行；关闭窗口不会停止本地服务。",
    }),
};

function createWindow() {
  const saved = readJson(windowStateFile(), {});
  const options = {
    width: Number.isFinite(saved.width) ? saved.width : 1440,
    height: Number.isFinite(saved.height) ? saved.height : 900,
    minWidth: 1024,
    minHeight: 640,
    show: false,
    title: "小码 Xiaoma",
    backgroundColor: "#FAF8F5",
    webPreferences: {
      preload: path.join(APP_DIR, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      spellcheck: false,
    },
  };
  if (Number.isFinite(saved.x) && Number.isFinite(saved.y)) {
    options.x = saved.x;
    options.y = saved.y;
  }
  // Windows / macOS 用系统原生窗口控制叠加层，界面层无需自己实现最小化等按钮。
  // overlay 高度须与 frontend/app/globals.css 的 --win-titlebar-height 保持一致（56），
  // 否则系统按钮与界面标题栏在垂直方向错位；界面据此为右上按钮区让出水平空间。
  if (process.platform === "win32") {
    options.titleBarStyle = "hidden";
    options.titleBarOverlay = { color: "#FAF8F5", symbolColor: "#1A1A18", height: 56 };
  } else if (process.platform === "darwin") {
    options.titleBarStyle = "hiddenInset";
  }

  mainWindow = new BrowserWindow(options);
  if (saved.maximized) {
    mainWindow.maximize();
  }

  const saveState = () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      writeJson(windowStateFile(), {
        ...mainWindow.getBounds(),
        maximized: mainWindow.isMaximized(),
      });
    }
  };
  mainWindow.on("close", saveState);
  mainWindow.once("ready-to-show", () => mainWindow.show());

  // preload 在 sandbox 下若加载失败，窗口仍能显示，但界面会静默失去
  // 「标题栏为系统按钮让位」的环境标记，问题很难被发现。显式记录到 stderr。
  mainWindow.webContents.on("preload-error", (_event, preloadPath, error) => {
    console.error(`[preload-error] ${preloadPath}: ${error && error.message ? error.message : error}`);
  });

  // 外链交给系统浏览器，不在窗口内弹出第二个无地址栏窗口。
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    void shell.openExternal(url);
    return { action: "deny" };
  });
  mainWindow.webContents.on("did-fail-load", (_event, errorCode, errorDescription, validatedURL) => {
    if (validatedURL && validatedURL.startsWith(ctrl.APP_URL)) {
      void mainWindow.loadFile(STATUS_PAGE);
      publishFailure(new Error(`界面加载失败：${errorDescription} (${errorCode})`));
    }
  });
}

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      if (mainWindow.isMinimized()) {
        mainWindow.restore();
      }
      mainWindow.focus();
    }
  });

  ipcMain.handle("status:get", () => currentState);
  ipcMain.on("status:retry", () => void startup());
  ipcMain.on("status:choose-dir", () => void chooseProjectDir());

  app.whenReady().then(() => {
    Menu.setApplicationMenu(Menu.buildFromTemplate(buildMenu(actions)));
    createWindow();
    mainWindow.webContents.once("did-finish-load", () => void startup());
    void mainWindow.loadFile(STATUS_PAGE);
  });

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
  app.on("window-all-closed", () => {
    if (process.platform !== "darwin") {
      app.quit();
    }
  });
}
