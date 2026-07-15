import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

const html = await readFile(new URL("../index.html", import.meta.url), "utf8");

test("presents the approved DeepArchi positioning and collaboration paths", () => {
  assert.match(html, /从战略判断到持续运营/);
  assert.match(html, /战略咨询/);
  assert.match(html, /验证型交付/);
  assert.match(html, /工具平台/);
  assert.match(html, /探索解决方案/);
  assert.match(html, /探索合作/);
});

test("keeps BLM as a framework and uses the approved accountability title", () => {
  assert.match(html, /战略共创与转型路线图/);
  assert.match(html, /以 BLM 等框架为基础/);
  assert.match(html, /创始人兼首席架构师/);
  assert.doesNotMatch(html, /主理人/);
});

test("describes integrations without publishing unsafe or fabricated endpoints", () => {
  assert.match(html, /Patent MCP/);
  assert.match(html, /自部署/);
  assert.match(html, /A2A.*私测/);
  assert.doesNotMatch(html, /(?:localhost|127\.0\.0\.1|0\.0\.0\.0)/i);
  assert.doesNotMatch(html, /https:\/\/\{[^}]+\}/);
});
