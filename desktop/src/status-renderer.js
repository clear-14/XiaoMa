"use strict";

/**
 * 服务状态页的渲染脚本（仅在 file:// 状态页运行，Next.js 界面层不加载本文件）。
 * 所有文案与状态都来自主进程推送的状态快照，页面自身不判断服务是否可用。
 */

(function () {
  const bridge = window.desktopStatus || null;

  const el = {
    body: document.body,
    title: document.getElementById("state-title"),
    lede: document.getElementById("state-lede"),
    label: document.getElementById("state-label"),
    seconds: document.getElementById("state-seconds"),
    detail: document.getElementById("state-detail"),
    version: document.getElementById("version"),
    retry: document.getElementById("retry"),
    chooseDir: document.getElementById("choose-dir"),
  };

  const COPY = {
    starting: {
      title: "小码正在启动本地服务",
      lede: "首次启动需要构建容器并执行数据库迁移，通常需要 30–90 秒。请保持 Docker Desktop 处于运行状态。",
      label: "STARTING",
    },
    ready: {
      title: "正在进入学习工作台",
      lede: "本地服务已就绪，窗口即将切换到对话式学习工作台。",
      label: "READY",
    },
    failed: {
      title: "本地服务未能启动",
      lede: "请按下方提示处理后点击「重新检测服务」；也可以指定包含 docker-compose.yml 的项目目录。",
      label: "FAILED",
    },
    offline: {
      title: "等待窗口进程连接",
      lede: "这个页面由小码桌面窗口壳加载，单独打开时不会启动本地服务。",
      label: "OFFLINE",
    },
  };

  function render(state) {
    const snapshot = state || {};
    const key = Object.prototype.hasOwnProperty.call(COPY, snapshot.state)
      ? snapshot.state
      : "offline";
    const copy = COPY[key];

    el.body.dataset.state = key;
    el.title.textContent = copy.title;
    el.lede.textContent = copy.lede;
    el.label.textContent = copy.label;
    el.seconds.textContent = String(Math.floor((snapshot.elapsedMs || 0) / 1000));
    el.detail.textContent = [snapshot.message, snapshot.error]
      .filter(Boolean)
      .join(" · ") || "等待状态更新…";
    el.version.textContent = snapshot.version
      ? `XIAOMA DESKTOP 1.4.1 · SERVICE ${snapshot.version}`
      : "XIAOMA DESKTOP 1.4.1";

    const canAct = Boolean(bridge) && (key === "failed" || key === "offline");
    el.retry.disabled = !canAct || key === "offline";
    el.chooseDir.disabled = !canAct;
  }

  function reveal() {
    document.querySelectorAll(".reveal").forEach((node) => node.classList.add("in"));
  }

  if (!bridge) {
    reveal();
    render({ state: "offline", message: "未检测到窗口壳桥接。" });
    return;
  }

  bridge
    .getState()
    .then(render)
    .catch((error) => {
      render({ state: "failed", message: String((error && error.message) || error) });
    });
  bridge.onState(render);

  el.retry.addEventListener("click", () => bridge.retry());
  el.chooseDir.addEventListener("click", () => bridge.chooseProjectDir());
  reveal();
})();
