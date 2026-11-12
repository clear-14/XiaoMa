"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { shouldExposeStatusApi } = require("../src/preload-guard");

test("壳专有桥接只对窗口壳自己的 file:// 状态页开放", () => {
  assert.equal(shouldExposeStatusApi("file:"), true);
});

test("Next.js 界面与浏览器辅助访问拿不到任何壳专有接口", () => {
  assert.equal(shouldExposeStatusApi("http:"), false);
  assert.equal(shouldExposeStatusApi("https:"), false);
  assert.equal(shouldExposeStatusApi(""), false);
  assert.equal(shouldExposeStatusApi("app:"), false);
});
