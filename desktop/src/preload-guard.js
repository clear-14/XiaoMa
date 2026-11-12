"use strict";

/**
 * 壳专有接口的暴露边界（纯函数，便于单测）。
 *
 * 设计文档第 5 节要求「界面层零壳专有 API 依赖」：Next.js 界面运行在
 * http://127.0.0.1:3000，必须完全不知道自己被装在 Electron 里，这样
 * 浏览器 / 移动端辅助访问与既有前端测试才不会退化。
 *
 * 只有窗口壳自己的 file:// 状态页需要桥接（显示启动进度、点击重试、
 * 选择项目目录），因此仅对该协议暴露 desktopStatus。
 *
 * @param {string} protocol window.location.protocol，形如 "file:" / "http:"
 */
function shouldExposeStatusApi(protocol) {
  return protocol === "file:";
}

module.exports = { shouldExposeStatusApi };
