"use strict";

/**
 * 应用菜单模板（纯函数，不 import electron）。
 * 窗口形态没有地址栏，因此把「重新检测服务」「选择项目目录」等运维动作
 * 放进菜单与快捷键；界面层本身不调用任何壳专有接口。
 *
 * @param {object} actions 主进程注入的回调
 */
function buildMenu(actions) {
  const isMac = process.platform === "darwin";
  const appMenu = isMac
    ? [
        {
          label: "Xiaoma",
          submenu: [
            { label: "关于小码", click: actions.about },
            { type: "separator" },
            { role: "hide" },
            { role: "hideOthers" },
            { role: "unhide" },
            { type: "separator" },
            { role: "quit" },
          ],
        },
      ]
    : [];

  return [
    ...appMenu,
    {
      label: "文件",
      submenu: [
        {
          label: "选择项目目录…",
          accelerator: "CmdOrCtrl+,",
          click: actions.chooseProjectDir,
        },
        { type: "separator" },
        {
          label: "重新检测本地服务",
          accelerator: "CmdOrCtrl+Shift+R",
          click: actions.retry,
        },
        { type: "separator" },
        { label: "退出", role: "quit" },
      ],
    },
    {
      label: "编辑",
      submenu: [
        { label: "撤销", role: "undo" },
        { label: "重做", role: "redo" },
        { type: "separator" },
        { label: "剪切", role: "cut" },
        { label: "复制", role: "copy" },
        { label: "粘贴", role: "paste" },
        { label: "全选", role: "selectAll" },
      ],
    },
    {
      label: "视图",
      submenu: [
        { label: "重新加载", accelerator: "CmdOrCtrl+R", click: actions.reload },
        {
          label: "切换开发者工具",
          accelerator: isMac ? "Alt+Command+I" : "Ctrl+Shift+I",
          click: actions.toggleDevTools,
        },
        { type: "separator" },
        { label: "实际大小", role: "resetZoom" },
        { label: "放大", role: "zoomIn" },
        { label: "缩小", role: "zoomOut" },
        { type: "separator" },
        { label: "全屏", role: "togglefullscreen" },
      ],
    },
    {
      label: "帮助",
      submenu: [
        { label: "在浏览器中打开", click: actions.openInBrowser },
        { label: "关于小码", click: actions.about },
      ],
    },
  ];
}

module.exports = { buildMenu };
