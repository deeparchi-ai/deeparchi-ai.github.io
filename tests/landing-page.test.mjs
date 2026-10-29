import assert from 'node:assert/strict';
import test from 'node:test';
import {readFile} from 'node:fs/promises';
import {PRODUCTS} from '../assets/site.mjs';
import {SERVICES, validateConfig} from '../assets/signals.mjs';
const read = file => readFile(new URL(`../${file}`, import.meta.url), 'utf8');
const [html, css, js, dev, privacy, catalogText, configText] = await Promise.all(['index.html','assets/site.css','assets/site.mjs','developers.html','privacy.html','service-catalog.json','analytics-config.json'].map(read));
const catalog = JSON.parse(catalogText);

test('short acquisition page has approved positioning and no personal branding', () => {
  assert.match(html, /AI 原生服务 · 专家专业判断/);
  assert.match(html, /让重要的专业服务，<br>更容易获得。/);
  assert.match(html, /为你，也为你的 Agent。/);
  assert.match(html, /href="#capabilities">查看服务 Demo/);
  assert.match(html, /href="#contact">描述我的需求/);
  assert.doesNotMatch(html, /创始人|邝谧|WHY DEEPARCHI|已上线|节省\d|真实客户案例/);
  assert.match(html, /上海申渡架固信息技术有限公司/);
  assert.match(html, /<noscript>[\s\S]*mailto:contact@deeparchi.com.cn/);
});

test('catalogue, cards, selection and sample definitions share exactly four service identities', () => {
  assert.equal(catalog.version, '1');
  assert.equal(catalog.kind, 'concept-service-catalog');
  assert.equal(catalog.services.length, 4);
  assert.deepEqual(catalog.services.map(s => s.id), SERVICES);
  assert.deepEqual(Object.keys(PRODUCTS), SERVICES);
  const cards = [...html.matchAll(/<article class="product" id="([^"]+)">([\s\S]*?)<\/article>/g)];
  assert.deepEqual(cards.map(card => card[1]), SERVICES);
  assert.equal((html.match(/<option value=/g) || []).length, 4);
  for (const s of catalog.services) {
    assert.equal(s.name, PRODUCTS[s.id].name);
    assert.equal(cards.find(card => card[1] === s.id)[2].match(/<h3>(.*?)<\/h3>/)[1].replaceAll('&amp;', '&'), s.name);
    assert.match(html, new RegExp(`id="${s.id}"`));
    assert.match(html, new RegExp(`data-demo="${s.id}"`));
    assert.match(html, new RegExp(`data-service="${s.id}"`));
    assert.match(html, new RegExp(`<option value="${s.id}">`));
    assert.equal(s.availability, s.id === 'deep-blm' ? 'web-trial' : 'concept-demo');
    if (s.id === 'deep-blm') assert.equal(s.web_trial.url, 'apps/deepblm.html');
    assert.equal(s.production_ready, false);
    assert.equal(s.human_contact, 'contact@deeparchi.com.cn');
    assert.ok(s.proposed_input.length && s.proposed_output.length);
    assert.equal(PRODUCTS[s.id].output.length, 3);
    assert.match(PRODUCTS[s.id].problem, /虚构/);
  }
  assert.deepEqual(catalog.a2a, {available: false, endpoint: null});
});

test('Chinese typography and responsive/reduced-motion contracts remain local', () => {
  assert.match(css, /line-break:strict/);
  assert.match(css, /text-wrap:balance/);
  assert.match(css, /--sans:-apple-system,BlinkMacSystemFont,"PingFang SC"/);
  assert.doesNotMatch(css, /Songti SC|Iowan Old Style|--copper|--ink:#15302c/);
  assert.match(css, /prefers-reduced-motion:reduce/);
  assert.match(css, /grid-template-columns:repeat\(2/);
  assert.match(html, /aria-controls="nav-links"/);
  assert.match(html, /href="assets\/deeparchi-favicon\.png"/);
  assert.doesNotMatch(html+css, /https?:\/\/(?:fonts|cdn)|@import/);
});

test('homepage adds consulting before the concise demo sections and keeps A2A in a closed dialog', () => {
  const main = html.match(/<main\b[^>]*>([\s\S]*?)<\/main>/)[1];
  // Preserve the original copy budget outside the new, fully readable consulting section.
  const conciseMain = main.replace(/<section\b[^>]*\bid="insight-services"[\s\S]*?<\/section>/, '');
  assert.ok([...conciseMain.replace(/<[^>]+>/g, '').matchAll(/\p{Script=Han}/gu)].length <= 749 * .65);
  assert.deepEqual([...main.matchAll(/<section\b[^>]*\bid="([^"]+)"/g)].map(match => match[1]), ['top','insight-services','capabilities','integrate','contact']);
  assert.doesNotMatch(main, /hero-copy|class="outcome"|预期交付|SERVICE EXPLORATIONS|ALSO HERE TO HELP|a2a-workspace/);
  const cards = [...main.matchAll(/<article class="product" id="([^"]+)"[^>]*>([\s\S]*?)<\/article>/g)];
  assert.equal(cards.length,4);
  for (const [, id, card] of cards) {
    const paragraphs = [...card.matchAll(/<p\b[^>]*>(.*?)<\/p>/g)];
    assert.equal(paragraphs.length,2);
    assert.match(paragraphs[0][1], id === 'deep-blm' ? /规划工具 · 试用/ : /概念 Demo/);
    assert.ok([...paragraphs[1][1].matchAll(/\p{Script=Han}/gu)].length <= 24);
    assert.doesNotMatch(card, /<ul|<ol|<details/);
  }
  assert.match(main, /id="open-a2a"[^>]*aria-controls="a2a-dialog"/);
  assert.match(main, /概念演示 · 尚未连接真实 A2A 服务/);
  const dialog = html.match(/<dialog id="a2a-dialog"([^>]*)>([\s\S]*?)<\/dialog>/);
  assert.ok(dialog);
  assert.doesNotMatch(dialog[1], /\bopen\b/);
  assert.match(dialog[2], /aria-label="关闭协作演示"/);
  assert.match(dialog[2], /class="a2a-workspace"/);
  assert.equal((dialog[2].match(/<option value=/g)||[]).length,4);
  for (const product of Object.values(PRODUCTS)) {
    for (const output of product.output) assert.ok(!main.includes(output));
  }
  assert.match(main, /id="collaborate"/);
  assert.match(main, /data-intent="integration"[^>]*>工具集成/);
  assert.match(main, /id="contact-consulting"[^>]*>咨询服务/);
});

test('compact consent prompt retains explicit choices, optional scope and accessible details', () => {
  const banner = html.match(/<aside\b[^>]*data-analytics-banner[\s\S]*?<\/aside>/)[0];
  assert.match(banner, /可选匿名交互统计，不含需求正文/);
  for (const choice of ['accept','reject']) assert.match(banner, new RegExp(`data-consent="${choice}"`));
  assert.match(banner, /<details><summary>统计详情<\/summary><p data-analytics-status role="status">/);
  assert.match(banner, /href="privacy.html"/);
});

test('product actions have eight distinct service-specific accessible names', () => {
  const cards = [...html.matchAll(/<article class="product"[^>]*>([\s\S]*?)<\/article>/g)].map(match => match[1]).join('');
  const actions = [...cards.matchAll(/<(?:button|a)\b[^>]*(?:data-demo=|data-intent="product")[^>]*>/g)];
  assert.equal(actions.length,8);
  const names = actions.map(([tag]) => tag.match(/aria-label="([^"]+)"/)?.[1]);
  assert.ok(names.every(Boolean));
  assert.equal(new Set(names).size,8);
  assert.match(html,/id="contact-data-warning">请勿发送敏感数据、密码或密钥/);
});

test('public privacy and developer guidance use honest receiver and retention semantics', () => {
  assert.doesNotMatch(dev+privacy,/human 受众|已验证自然人/);
  assert.match(privacy,/不承诺 30 天自动删除/);
  assert.match(dev,/browser_interaction/);
  assert.match(privacy,/没有自动删除机制/);
  assert.match(privacy,/平台日志的具体字段与保留期限尚未核验/);
  assert.match(privacy,/长草稿改为复制后粘贴/);
  assert.doesNotMatch(js,/track\('demo_complete'/);
});

test('A2A is explicitly a sample with safe real resources and no fabricated runtime', () => {
  for (const stage of ['发现服务','描述需求','确认范围与授权','查看进度','接收交付样例']) assert.ok(html.includes(`<li>${stage}</li>`));
  assert.match(html, /本地样例演示，未连接真实 A2A 服务，不会执行真实任务或上传业务内容/);
  assert.match(js, /task_executed: false/);
  assert.match(dev, /不是协议符合性演示/);
  for (const link of ['https://a2a-protocol.org/latest/','https://github.com/deeparchi-ai/patent-mcp-server','https://github.com/deeparchi-ai/macs']) assert.ok(dev.includes(link));
  assert.doesNotMatch(html+dev+catalogText, /(?:localhost|127\.0\.0\.1|0\.0\.0\.0)|\.well-known\/|https:\/\/\{/);
  assert.match(dev, /不证明托管服务在线/);
});

test('draft handling exposes limits, safe text rendering and stable contact anchors', () => {
  assert.match(html, /id="problem"[^>]*required maxlength="500"/);
  assert.match(html, /id="result"[^>]*maxlength="500"/);
  assert.match(html, /id="constraints"[^>]*maxlength="300"/);
  assert.match(html, /准备的是邮件草稿，尚未发送；请在邮件客户端确认发送/);
  assert.doesNotMatch(html, /需求已提交|type="(?:email|tel)"/);
  assert.doesNotMatch(js, /innerHTML|insertAdjacentHTML|localStorage[.(]|location\.href\s*=/);
  for (const id of ['contact-consulting','contact-partnership','contact-a2a']) assert.equal(html.split(`id="${id}"`).length-1, 1);
  for (const document of [html, dev, privacy]) {
    for (const email of document.matchAll(/mailto:([^?"\s]+)/g)) assert.equal(email[1], 'contact@deeparchi.com.cn');
    for (const mailto of document.matchAll(/href="(mailto:[^"]+)"/g)) assert.ok(!mailto[1].includes('+'));
  }
  assert.match(privacy, /不收集点击统计/);
  const config = JSON.parse(configText);
  assert.ok(validateConfig(config));
  assert.equal(config.version,'1');
  assert.equal(config.site_id,'deeparchi');
  assert.equal(config.consent_required,true);
  assert.equal(config.endpoint,config.enabled ? 'https://qunling-001-d7gwxqdou24c9dad4.service.tcloudbase.com/demand/collect' : null);
});
