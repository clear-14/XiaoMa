import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

/**
 * 布局静态守卫：防止后续改动把三栏改回「固定宽度导致窄屏横向溢出」，
 * 或删掉离线字体、动效降级与安全区。浏览器像素级实测在批次 6 进行。
 */
const css = readFileSync(
  resolve(process.cwd(), "app", "globals.css"),
  "utf8",
);

describe("V1.4 窗口布局守卫", () => {
  it("三栏用弹性中栏且整体裁剪，375px 不产生横向滚动", () => {
    expect(css).toMatch(
      /grid-template-columns: var\(--win-left-col\) minmax\(0, 1fr\) var\(--win-right-col\)/,
    );
    expect(css).toMatch(/\.window-shell \{[\s\S]*?overflow: hidden/);
    expect(css).toMatch(/\.window-main \{[^}]*overflow-y: auto/);
    expect(css).toMatch(/@media \(max-width: 767px\)/);
    expect(css).toMatch(/@media \(max-width: 1279px\)/);
  });

  it("中栏显式占第 2 条网格轨道，窄屏抽屉脱离网格流后不会塌陷成 0 宽", () => {
    expect(css).toMatch(/\.window-main \{\s*grid-column: 2;\s*\}/);
    expect(css).toMatch(/\.window-rail \{\s*grid-column: 1;/);
    expect(css).toMatch(/\.window-right \{\s*grid-column: 3;/);
  });

  it("移动端左右栏改为抽屉，输入框留安全区", () => {
    expect(css).toMatch(/\.window-right \{[\s\S]*?position: fixed/);
    expect(css).toMatch(/\.window-rail \{[\s\S]*?position: fixed/);
    expect(css).toMatch(/env\(safe-area-inset-bottom\)/);
  });

  it("自托管字体与可访问性降级不被删掉", () => {
    expect((css.match(/@font-face/g) ?? []).length).toBeGreaterThanOrEqual(4);
    expect(css).toMatch(/url\("\/fonts\/ibm-plex-mono-latin-400-normal\.woff2"\)/);
    expect(css).toMatch(/outline: 2px solid var\(--primary\)/);
    expect(css).toMatch(/min-width: 44px; min-height: 44px/);
    expect(css).toMatch(/@media \(prefers-reduced-motion: reduce\)/);
  });

  it("设计令牌为暖白 / 近黑 / 深朱橙，且没有 CDN 字体", () => {
    expect(css).toMatch(/--bg: #faf8f5/);
    expect(css).toMatch(/--text: #1a1a18/);
    expect(css).toMatch(/--primary: #b33b18/);
    expect(css).toMatch(/--accent: #d8502a/);
    expect(css).not.toMatch(/fonts\.googleapis\.com/);
  });

  it("窗口壳内标题栏为系统窗口按钮让位，按钮在拖拽区里仍可点击", () => {
    // Windows：titleBarOverlay 的系统按钮占右上约 144×56，标题栏必须让位，
    // 否则「收起学习工作区」被压住 —— 批次 6 GUI 实测暴露的缺陷。
    expect(css).toMatch(
      /html\[data-shell="desktop"\]\[data-shell-platform="win"\] \.window-titlebar \{\s*padding-right: calc\(0\.75rem \+ 144px\);\s*\}/,
    );
    // 标题栏是 drag 区，其中的 button 必须 no-drag，否则点击被当作拖窗口。
    expect(css).toMatch(
      /\.window-titlebar button,\s*\.window-titlebar a \{ -webkit-app-region: no-drag; \}/,
    );
  });
});
