"use strict";

/**
 * 最小 preload 桥接。
 *
 * 关键约束：BrowserWindow 使用 webPreferences.sandbox = true 时，preload 运行在
 * 沙箱里，Electron 只允许 require 内置模块（electron / events / timers / url），
 * 任何本地相对模块都会抛 "module not found" 并中止整个 preload。
 * 批次 6 GUI 实测就踩到这一点：preload 因 require("./preload-guard") 失败而整体
 * 不执行，状态页的重试/选择目录按钮与标题栏环境标记同时失效。
 * 因此判定函数内联在这里；desktop/src/preload-guard.js 仍是该判定的契约说明与
 * 单测目标，两处一致性由 tests/no-shell-api.test.js 的源码断言绑定。
 *
 * 界面层零壳专有 API 依赖：Next.js 界面跑在 http://127.0.0.1:3000，
 * 只有 file: 的状态页会拿到 desktopStatus。
 */

const { contextBridge, ipcRenderer } = require("electron");

function shouldExposeStatusApi(protocol) {
  return protocol === "file:";
}

if (shouldExposeStatusApi(window.location.protocol)) {
  contextBridge.exposeInMainWorld("desktopStatus", {
    getState: () => ipcRenderer.invoke("status:get"),
    onState: (listener) => {
      const handler = (_event, state) => listener(state);
      ipcRenderer.on("status:state", handler);
      return () => ipcRenderer.removeListener("status:state", handler);
    },
    retry: () => ipcRenderer.send("status:retry"),
    chooseProjectDir: () => ipcRenderer.send("status:choose-dir"),
  });
}

/**
 * 给界面页打一个「运行在窗口壳里」的 DOM 标记。
 *
 * 这不是壳 API：只写 data-* 属性，界面源码不出现任何 Electron 引用，
 * 因此「界面层零壳专有 API 依赖」的约束不受影响。
 *
 * 界面需要它的唯一原因：主进程用 titleBarStyle=hidden + titleBarOverlay
 * 把系统的最小化/最大化/关闭按钮叠加在右上角（高 56、宽约 144），
 * 界面标题栏必须为这块区域让位，否则「收起学习工作区」按钮会被压住。
 */
function markShellEnvironment() {
  const root = document && document.documentElement;
  if (!root) {
    return;
  }
  root.dataset.shell = "desktop";
  root.dataset.shellPlatform = process.platform === "darwin" ? "mac" : "win";
}

if (window.location.protocol === "http:" || window.location.protocol === "https:") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", markShellEnvironment, { once: true });
  } else {
    markShellEnvironment();
  }
}
