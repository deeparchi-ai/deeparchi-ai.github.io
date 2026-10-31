import assert from 'node:assert/strict';
import test from 'node:test';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';

const read = file => readFile(new URL(`../${file}`, import.meta.url), 'utf8');
const [html, css, developers, privacy, js] = await Promise.all(
  ['index.html', 'assets/insight-services.css', 'developers.html', 'privacy.html', 'assets/site.mjs'].map(read));
const details = html.match(/<details id="insight-details"([^>]*)>([\s\S]*?)<\/details>/);
const dialog = html.match(/<dialog id="insight-dialog"([^>]*)>([\s\S]*?)<\/dialog>/);
const section = [details[0], details[2]];
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

test('insight is one of two professional services with honest subscription and consulting actions', () => {
  const main = html.match(/<main[^>]*>([\s\S]*?)<\/main>/)[1];
  assert.deepEqual([...main.matchAll(/<section\b[^>]*id="([^"]+)"/g)].map(m => m[1]), ['top', 'capabilities', 'service-method', 'online-tools', 'contact']);
  assert.doesNotMatch(html, /id="insight-services"|href="#insight-services"|tech-ma|Tech M(?:&amp;|&)A/);
  const cards = [...main.matchAll(/<article class="product" id="([^"]+)">([\s\S]*?)<\/article>/g)];
  assert.deepEqual(cards.map(m => m[1]), ['tech-insight', 'tech-transfer-poc']);
  const card = cards[0][2];
  assert.match(card, /<p class="badge available">订阅 \/ 定制服务<\/p>/);
  assert.match(card, /<h3>技术与战略洞察<\/h3>/);
  assert.match(card, /href="#insight-details"[^>]*>了解服务<\/a>/);
  assert.match(card, /data-intent="consulting" data-surface="cards"[^>]*>咨询服务<\/button>/);
  assert.doesNotMatch(card, /概念 Demo|data-demo|data-service|<details/);
  assert.match(html, /<meta name="description" content="[^"]*技术与战略洞察服务[^"]*在线工具[^"]*">/);
});

test('single canonical full text progressively moves from no-JS details into accessible native dialog', () => {
  assert.ok(dialog);
  assert.doesNotMatch(dialog[1] + details[1], /\bopen\b/);
  assert.match(dialog[1], /aria-labelledby="insight-title" aria-describedby="insight-intro"/);
  assert.match(dialog[2], /data-close aria-label="关闭服务详情" autofocus/);
  assert.match(details[0], /<summary>技术与战略洞察服务：完整服务详情<\/summary>/);
  assert.equal((html.match(/id="insight-content"/g) || []).length, 1);
  assert.match(js, /insight.append\(\$\('#insight-content'\)\)/);
  assert.match(js, /\$\('#insight-details'\).hidden = true/);
  assert.match(js, /insight.showModal\(\)/);
  assert.match(js, /insight.addEventListener\('close',.*insightTrigger.focus\(\)/);
  assert.match(js, /if \(insight.open\) insight.close\(\)/);
  assert.match(js, /insight.open \? insightTrigger : button/);
  assert.doesNotMatch(html, /\son(?:click|keydown|load)=/);
  for (const copy of [
    'AI 驱动研究 · 专家专业判断', '持续洞察变化，支持科学决策，推动业务创新',
    '依托 AI 驱动的持续研究能力与专家经验，为企业提供从趋势洞察、深度分析到专项决策与行动支持的系列服务，帮助企业识别机会、把握技术方向、优化竞争策略。'
  ]) assert.ok(section[1].includes(copy), copy);
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
  assert.doesNotMatch(section[0], /<script|data-demo|data-service|data-analytics|概念 Demo|招募试点|已上线|认证|保证|自动执行|\d+\s*元/);
});

test('both consulting CTAs keep generic service=null routing and static email fallback', () => {
  for (const id of ['insight-card-consulting', 'insight-consulting']) {
    const button = html.match(new RegExp(`<button[^>]*id="${id}"[^>]*>`))[0];
    assert.match(button, /data-intent="consulting"/);
    assert.match(button, /data-surface="(?:cards|support)"/);
    assert.doesNotMatch(button, /data-service|tech-ma|tech-insight/);
  }
  assert.match(section[1], /<a href="mailto:contact@deeparchi.com.cn">邮件咨询：contact@deeparchi.com.cn<\/a>/);
  // Both consent-time measurement and observer registration must ignore consulting cards.
  assert.match(js, /if \(!Object.hasOwn\(PRODUCTS, card.id\)\) return/);
  assert.match(js, /if \(Object.hasOwn\(PRODUCTS, card.id\)\) observer.observe\(card\)/);
  assert.doesNotMatch(js, /track\([^\n]*(?:tech-insight|tech-ma)/);
});

test('service CSS is scoped to insight card/dialog/disclosure and maintains responsive readable content', () => {
  assert.match(html, /<link rel="stylesheet" href="assets\/insight-services.css\?v=[a-f0-9]{12}">/);
  assert.doesNotMatch(developers + privacy, /insight-services.css/);
  assert.match(css, /grid-template-columns:repeat\(3,minmax\(0,1fr\)\)/);
  assert.match(css, /@media\(max-width:1100px\)[\s\S]*?\.insight-grid\{grid-template-columns:1fr\}/);
  assert.match(css, /@media\(max-width:600px\)/);
  assert.match(css, /font-size:16px;line-height:1.85/);
  assert.match(css, /min-width:0/);
  assert.match(css, /overflow-wrap:anywhere/);
  for (const line of css.split('\n').map(line => line.trim()).filter(line => line.includes('{') && !line.startsWith('@'))) {
    assert.match(line, /^(?:#tech-insight|#insight-dialog|#insight-details|:is\(#insight-dialog,#insight-details\))/);
  }
  assert.doesNotMatch(css, /@import|url\(|font-family:|overflow:hidden|line-clamp|[;{]height:\d/);
});

test('canonical insight details remains byte-identical', () => {
  assert.equal(createHash('sha256').update(details[0]).digest('hex'), '2e92344a7ce0c709c4ef6c84a0574d5f74884bbb5e16c446ccac01c59830be78');
});

test('canonical insight dialog remains byte-identical', () => {
  assert.equal(createHash('sha256').update(dialog[0]).digest('hex'), '154b217c981b63d69baea7fba695d9432d25eb5b8b0ff24bbb3a3e6815b89dea');
});
