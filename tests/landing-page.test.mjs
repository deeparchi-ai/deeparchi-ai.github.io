import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

const html = await readFile(new URL("../index.html", import.meta.url), "utf8");
const heroTitleHtml = html.match(/<h1 id="hero-title">([\s\S]*?)<\/h1>/)?.[1] ?? "";
const heroTitleText = heroTitleHtml.replace(/<[^>]+>/g, "");

test("presents the approved DeepArchi positioning and collaboration paths", () => {
  assert.match(html, /AI 原生服务公司/);
  assert.match(heroTitleText, /把专业判断变成/);
  assert.match(html, /战略咨询/);
  assert.match(html, /AI 原生交付/);
  assert.match(html, /工具平台/);
  assert.match(html, /探索解决方案/);
  assert.match(html, /探索合作/);
});

test("uses controlled Chinese headline wrapping instead of splitting key phrases", () => {
  assert.match(html, /line-break: strict/);
  assert.match(html, /text-wrap: balance/);
  assert.match(html, /class="no-break"/);
});

test("declares an inline favicon so page loads without a missing static asset", () => {
  assert.match(html, /<link rel="icon" href="data:image\/svg\+xml/);
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

test("explains all three services with four answers, retained scopes and project boundaries", () => {
  const section = html.match(/<section[^>]+id="capabilities"[^>]*>([\s\S]*?)<\/section>/)?.[1] ?? "";
  const cards = [...section.matchAll(/<article class="capability">([\s\S]*?)<\/article>/g)];
  const expected = [
    ["战略咨询", "AI 战略诊断 · 战略共创与转型路线图 · AI 原生能力、架构与组织设计。以 BLM 等框架为基础，明确阶段目标、投资重点与行动路径。"],
    ["AI 原生交付", "IP 守护 · Deep BLM · 技术架构规划 · Tech M&amp;A。"],
    ["工具平台", "OPC AI 工具箱 · Patent MCP · SanctionsSight · 认知外骨骼 · MACS。"],
  ];
  assert.equal(cards.length, expected.length);
  cards.forEach(([, card], index) => {
    assert.equal(card.match(/<h3>(.*?)<\/h3>/)?.[1], expected[index][0]);
    const list = card.match(/<ul class="service-list">([\s\S]*?)<\/ul>/)?.[1] ?? "";
    const items = [...list.matchAll(/<li>([\s\S]*?)<\/li>/g)];
    assert.equal(items.length, 4);
    items.forEach(([, item], itemIndex) => {
      const answer = item.match(/^<strong>([^<]+)<\/strong><span>([^<]+)<\/span>$/);
      assert.ok(answer, "each item has a question and answer");
      assert.equal(answer[1], ["适合谁", "解决什么", "交付什么", "如何开始"][itemIndex]);
      assert.ok(answer[2].trim(), "each answer is nonempty");
    });
    assert.equal(card.match(/<\/ul>\s*<p class="service-scope">服务范围：(.*?)<\/p>/)?.[1], expected[index][1]);
  });
  assert.match(section, /<\/article>\s*<\/div>\s*<p class="service-boundary">以上为合作范围与交付示例；具体交付内容、验收标准和支持边界，以双方确认的项目约定为准。<\/p>/);
});

test("publishes the owner-specified corporate contact email consistently", () => {
  assert.ok(html.includes('href="mailto:contact@deeparchi.com.cn"'));
  assert.ok(html.includes('<span>contact@deeparchi.com.cn</span>'));
  assert.doesNotMatch(html, /mailto:kuangmi@/);
});

function linksIn(markup) {
  return [...markup.matchAll(/<a\b([^>]*)>([\s\S]*?)<\/a>/g)].map(([, attributes, content]) => ({
    attributes: Object.fromEntries([...attributes.matchAll(/([\w-]+)="([^"]*)"/g)].map(([, key, value]) => [key, value])),
    content,
    text: content.replace(/<[^>]+>/g, ""),
  }));
}

function assertMailto(href, subject) {
  const url = new URL(href);
  assert.equal(url.protocol, "mailto:");
  assert.equal(url.pathname, "contact@deeparchi.com.cn");
  assert.deepEqual([...new URLSearchParams(url.search)], subject ? [["subject", subject]] : []);
  assert.equal(url.hash, "");
}

test("gives each asset an honest documentation or email path while retaining its status and description", () => {
  const cards = [...html.matchAll(/<article class="asset">([\s\S]*?)<\/article>/g)];
  const expected = [
    ["Patent MCP", "已上线", "面向 Agent 的开源专利检索与分析基础设施。", "查看开源文档 ↗", "https://github.com/deeparchi-ai/patent-mcp-server"],
    ["SanctionsSight", "已上线", "面向出海业务的制裁、风险与情报能力。", "预约演示 →", "DeepArchi｜SanctionsSight 演示预约"],
    ["认知外骨骼", "内测", "将个人专业判断转化为可协作的认知能力。", "咨询内测 →", "DeepArchi｜认知外骨骼 内测咨询"],
    ["MACS", "开发中", "持续演进中的多 Agent 能力与协同资产。", "查看开源进展 ↗", "https://github.com/deeparchi-ai/macs"],
  ];
  assert.equal(cards.length, expected.length);
  cards.forEach(([, card], index) => {
    const [name, status, description, label, destination] = expected[index];
    assert.equal(card.match(/<h4>(.*?)<\/h4>/)?.[1], name);
    assert.equal(card.match(/<p class="status[^\"]*">(.*?)<\/p>/)?.[1], status);
    assert.ok(card.includes(`<p>${description}</p>`));
    const links = linksIn(card);
    assert.equal(links.length, 1);
    const { attributes, text } = links[0];
    assert.equal(attributes.class, "asset-link");
    assert.equal(text, label);
    if (destination.startsWith("https:")) {
      assert.equal(new URL(attributes.href).href, destination);
      assert.equal(attributes.target, "_blank");
      assert.deepEqual(new Set(attributes.rel.split(/\s+/)), new Set(["noopener", "noreferrer"]));
    } else {
      assertMailto(attributes.href, destination);
    }
  });
  assert.ok(html.includes('<p class="evidence-note">开源项目可查看文档与代码；未提供公开入口的能力可预约沟通，具体开放范围以沟通确认为准。</p>'));
});

test("routes business, partnership and A2A enquiries to distinct subject-prefilled contact anchors", () => {
  const links = linksIn(html);
  const routes = [
    ["contact-consulting", "业务咨询", "场景与目标 ↗", "讨论你的关键议题 →", "path-link"],
    ["contact-partnership", "合作洽谈", "能力与分工 ↗", "发起合作对话 →", "path-link"],
    ["contact-a2a", "A2A 私测申请", "场景与接入边界 ↗", "申请 A2A 私测接入 →", "protocol-link"],
  ];
  const contact = html.match(/<section class="contact"[^>]*>([\s\S]*?)<\/section>/)?.[1] ?? "";
  for (const [id, label, guidance, inboundLabel, inboundClass] of routes) {
    assert.equal([...html.matchAll(new RegExp(`\\bid="${id}"`, "g"))].length, 1);
    const route = linksIn(contact).find(({ attributes }) => attributes.id === id);
    assert.ok(route, `${id} belongs to the contact section`);
    assert.equal(route.content, `<span>${label}</span><span>${guidance}</span>`);
    assertMailto(route.attributes.href, `DeepArchi｜${label}`);
    const inbound = links.find(({ text }) => text === inboundLabel);
    assert.equal(inbound?.attributes.class, inboundClass);
    assert.equal(inbound?.attributes.href, `#${id}`);
  }
  const mailLinks = links.filter(({ attributes }) => attributes.href?.startsWith("mailto:"));
  assert.equal(mailLinks.length, 6);
  mailLinks.forEach(({ attributes }) => assert.equal(new URL(attributes.href).pathname, "contact@deeparchi.com.cn"));
  assertMailto(links.find(({ attributes }) => attributes.href === "mailto:contact@deeparchi.com.cn")?.attributes.href);
  assert.ok(linksIn(contact).some(({ attributes }) => attributes.href === "https://github.com/deeparchi-ai"));
  assert.ok(links.filter(({ attributes }) => attributes.href === "#contact").length >= 2);
  assert.match(contact, /class="contact-copy">[^<]*业务咨询[^<]*合作洽谈[^<]*技术接入/);
  assert.match(contact, /class="contact-note">[^<]*预填邮件主题[^<]*未配置邮件客户端[^<]*邮箱地址[^<]*请勿发送密码、密钥或敏感业务数据/);
});

test("keeps A2A a controlled private preview with no runtime endpoint", () => {
  const card = [...html.matchAll(/<article class="protocol">([\s\S]*?)<\/article>/g)]
    .map(([, content]) => content).find((content) => content.includes("A2A / PRIVATE PREVIEW"));
  assert.ok(card);
  assert.match(card, /<h3>A2A 私测申请中<\/h3>/);
  assert.match(card, /当前以受控私测方式接入/);
  assert.match(card, /状态：私测 · 按场景与合作关系开放 · 不发布虚构服务地址/);
  assert.deepEqual(linksIn(card).map(({ attributes }) => attributes.href), ["#contact-a2a"]);
  assert.doesNotMatch(card, /(?:https?|wss?):\/\//i);
  assert.doesNotMatch(card, /自动(?:开通|接入|通过)|即时开通/);
});

test("uses RFC6068 URI encoding rather than form-encoded plus signs in mail subjects", () => {
  const mailLinks = linksIn(html).filter(({ attributes }) => attributes.href?.startsWith("mailto:"));
  const spacedSubjects = [];
  for (const { attributes } of mailLinks) {
    const url = new URL(attributes.href);
    assert.doesNotMatch(url.search, /\+/);
    if (!url.search) continue;
    const subject = decodeURIComponent(url.search.slice("?subject=".length));
    assert.equal(subject, url.searchParams.get("subject"));
    if (subject.includes(" ")) {
      assert.ok(url.search.includes("%20"));
      spacedSubjects.push(subject);
    }
  }
  assert.deepEqual(new Set(spacedSubjects), new Set([
    "DeepArchi｜SanctionsSight 演示预约",
    "DeepArchi｜认知外骨骼 内测咨询",
    "DeepArchi｜A2A 私测申请",
  ]));
});
