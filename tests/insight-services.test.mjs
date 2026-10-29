import assert from 'node:assert/strict';
import test from 'node:test';
import {readFile} from 'node:fs/promises';

const read = file => readFile(new URL(`../${file}`, import.meta.url), 'utf8');
const [html, css, developers, privacy] = await Promise.all(
  ['index.html', 'assets/insight-services.css', 'developers.html', 'privacy.html'].map(read));
const section = html.match(/<section\b[^>]*id="insight-services"[^>]*>([\s\S]*?)<\/section>/);
const services = [
  {
    name: '持续洞察与技术雷达服务', mode: '标准订阅', focus: '持续跟踪 · 趋势洞察',
    description: '围绕约定的行业、技术或竞争领域，持续跟踪重要技术、产品、厂商及市场动态，识别发展趋势、潜在机会与风险。',
    deliverables: ['季度技术与竞争雷达报告', '重点变化与趋势分析', '业务机会提示', '季度成果交流']
  },
  {
    name: '深度洞察与专家决策支持服务', mode: '专业订阅', focus: '约定领域深度研究 · 专家针对性建议',
    description: '在持续洞察基础上，聚焦约定的重点领域与专题，结合企业业务背景，开展深入的技术、产品与竞争分析，提供针对性的专业判断与决策建议。',
    deliverables: ['季度深度研究报告', '重点专题与竞争比较', '专家针对性建议', '定期专家交流']
  },
  {
    name: '专项决策与行动支持服务', mode: '定制服务', focus: '专项论证 · 行动支持',
    description: '围绕企业特定的技术选择、产品规划、竞争策略或业务发展需求，组织专项研究和方案设计，并在约定范围内提供行动准备、实施协调与复盘支持。',
    deliverables: ['专项分析与论证报告', '解决方案及行动计划', '执行支持成果，按项目需求约定。']
  }
];

test('consulting is a labelled static section between hero and concept demos with its own nav link', () => {
  assert.ok(section);
  assert.match(section[0], /aria-labelledby="insight-services-title"/);
  assert.match(section[1], /<h2 id="insight-services-title">技术与竞争洞察服务<\/h2>/);
  assert.match(section[1], /AI 驱动研究 · 专家专业判断/);
  assert.match(section[1], /持续洞察变化，支持科学决策，推动业务创新/);
  assert.match(section[1], /依托 AI 驱动的持续研究能力与专家经验，为企业提供从趋势洞察、深度分析到专项决策与行动支持的系列服务，帮助企业识别机会、把握技术方向、优化竞争策略。/);
  assert.ok(html.indexOf('id="top"') < section.index);
  assert.ok(section.index < html.indexOf('id="capabilities"'));
  assert.match(html, /<div class="nav-links"[^>]*>[\s\S]*?<a href="#insight-services">洞察服务<\/a>/);
  assert.match(html, /<meta name="description" content="[^"]*技术与竞争洞察服务[^"]*概念 Demo[^"]*">/);
});

test('all three services retain authoritative names, descriptions, modes and exact deliverable lists', () => {
  const cards = [...section[1].matchAll(/<article class="insight-card"[^>]*>([\s\S]*?)<\/article>/g)];
  assert.equal(cards.length, 3);
  for (const [index, service] of services.entries()) {
    const card = cards[index][1];
    assert.match(cards[index][0], new RegExp(`aria-labelledby="insight-p${index + 1}-title"`));
    assert.ok(card.includes(`<h3 id="insight-p${index + 1}-title">${service.name}</h3>`));
    for (const copy of [service.mode, service.focus, service.description]) assert.ok(card.includes(copy), copy);
    assert.ok(card.includes(`<span>P${index + 1}</span>`));
    assert.deepEqual([...card.matchAll(/<li>(.*?)<\/li>/g)].map(match => match[1]), service.deliverables);
  }
  assert.match(section[1], /P1、P2采用持续订阅模式；P3根据具体项目需求定制。具体服务范围、交付周期与成果形式以双方约定为准。/);
  for (const copy of ['持续跟踪', '动态更新，而非一次性研究', 'AI＋专家', '智能研究与专业判断结合', '业务导向', '从趋势洞察到可执行建议']) assert.ok(section[1].includes(copy));
  assert.doesNotMatch(section[0], /<script|<details|\bhidden\b(?!>咨询洞察服务)|data-demo|data-service|data-analytics|概念 Demo|招募试点|已上线|认证|保证|自动执行|\d+\s*元/);
});

test('one generic consulting CTA reuses allowed routing and a visible static email fallback', () => {
  const buttons = [...section[1].matchAll(/<button\b[^>]*>[^<]*<\/button>/g)];
  assert.equal(buttons.length, 1);
  assert.match(buttons[0][0], /id="insight-consulting" data-intent="consulting" data-surface="support" data-js hidden>咨询洞察服务/);
  assert.doesNotMatch(buttons[0][0], /data-service/);
  assert.match(section[1], /<a href="mailto:contact@deeparchi.com.cn">邮件咨询：contact@deeparchi.com.cn<\/a>/);
});

test('homepage-only responsive styles use local system typography and readable static content', () => {
  assert.match(html, /<link rel="stylesheet" href="assets\/insight-services.css">/);
  assert.doesNotMatch(developers + privacy, /insight-services.css/);
  assert.match(css, /grid-template-columns:repeat\(3,minmax\(0,1fr\)\)/);
  assert.match(css, /@media\(max-width:1100px\)[\s\S]*?\.insight-grid\{grid-template-columns:1fr\}/);
  assert.match(css, /@media\(max-width:600px\)/);
  assert.match(css, /font-size:16px;line-height:1.85/);
  assert.match(css, /min-width:0/);
  assert.match(css, /overflow-wrap:anywhere/);
  assert.doesNotMatch(css, /@import|url\(|font-family:|display:none|overflow:hidden|line-clamp|[;{]height:\d/);
});
