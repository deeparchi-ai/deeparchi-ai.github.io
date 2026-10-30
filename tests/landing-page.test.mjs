import assert from 'node:assert/strict';
import test from 'node:test';
import {readFile} from 'node:fs/promises';
import {PRODUCTS} from '../assets/site.mjs';
import {SERVICES, validateConfig} from '../assets/signals.mjs';
const read = file => readFile(new URL(`../${file}`, import.meta.url), 'utf8');
const [html, css, js, dev, privacy, catalogText, configText] = await Promise.all(['index.html','assets/site.css','assets/site.mjs','developers.html','privacy.html','service-catalog.json','analytics-config.json'].map(read));
const catalog = JSON.parse(catalogText);
const homeCSS = await read('assets/homepage.css');
const servicesHTML = html.match(/<section[^>]*id="capabilities"[\s\S]*?<\/section>/)[0];
const toolsHTML = html.match(/<section[^>]*id="online-tools"[\s\S]*?<\/section>/)[0];
const cards = [...servicesHTML.matchAll(/<article class="product" id="([^"]+)">([\s\S]*?)<\/article>/g)];

test('hero and navigation offer distinct service and self-service paths', () => {
  assert.equal(html.match(/<h1 id="hero-title">(.*?)<\/h1>/)[1].replace(/<br>/g, ''), 'AI原生服务，全新体验');
  assert.match(html, /复杂问题，与专家一起解答。<br>日常任务，用在线工具自主完成。/);
  assert.match(html, /href="#capabilities">了解专业服务/);
  assert.match(html, /href="#online-tools">使用在线工具/);
  const nav = html.match(/<div class="nav-links"[^>]*>([\s\S]*?)<\/div>/)[1];
  assert.deepEqual([...nav.matchAll(/href="([^"]+)">([^<]+)/g)].map(m => [m[1], m[2]]), [
    ['#capabilities','专业服务'], ['#online-tools','在线工具'], ['#integrate','协作接入'], ['#contact','联系我们']
  ]);
  assert.doesNotMatch(html, /创始人|邝谧|WHY DEEPARCHI|已上线|节省\d|真实客户案例/);
  assert.match(html, /上海申渡架固信息技术有限公司/);
  assert.match(html, /<noscript>[\s\S]*mailto:contact@deeparchi.com.cn/);
});

test('catalogue describes one manual service, four real tools and only one local A2A sample', () => {
  assert.equal(catalog.version, '1');
  assert.equal(catalog.kind, 'service-catalog');
  assert.deepEqual(catalog.organization, {name:'DeepArchi 深度架构', legal_name:'上海申渡架固信息技术有限公司', human_contact:'contact@deeparchi.com.cn'});
  assert.deepEqual(catalog.services.map(s => s.id), ['tech-insight']);
  assert.deepEqual(Object.keys(PRODUCTS), ['deep-blm']);
  assert.match(js, /category === 'consulting' \|\| !Object.hasOwn\(PRODUCTS, requestedService\) \? null : requestedService/);
  // Frozen receiver schema keeps its legacy enum; the UI emits only registered PRODUCTS.
  assert.deepEqual(SERVICES, ['ip-guard', 'deep-blm', 'architecture', 'tech-ma']);
  assert.deepEqual(cards.map(card => card[1]), ['tech-insight']);
  assert.deepEqual([...html.matchAll(/<option value="([^"]+)"/g)].map(m => m[1]), ['deep-blm']);
  const service = catalog.services[0];
  assert.equal(service.name, '技术与战略洞察服务');
  assert.equal(service.availability, 'manual-contact');
  assert.equal(service.production_ready, false);
  assert.equal(service.human_contact, 'contact@deeparchi.com.cn');
  assert.match(service.delivery_mode, /人工咨询/);
  assert.match(service.description, /无自动在线订阅、支付或 A2A 服务/);
  assert.equal(service.details_url, 'index.html#insight-details');
  assert.equal(PRODUCTS[service.id], undefined);
  const tools = [...toolsHTML.matchAll(/<article class="tool-card" id="([^"]+)">([\s\S]*?)<\/article>/g)];
  assert.deepEqual(catalog.tools.map(t => t.id), tools.map(t => t[1]));
  for (const [index, tool] of catalog.tools.entries()) {
    assert.equal(tool.name, tools[index][2].match(/<h3>(.*?)<\/h3>/)[1]);
    assert.equal(tool.url, tools[index][2].match(/href="([^"]+)"/)[1]);
    assert.equal(tool.availability, index === 0 ? 'web-trial' : 'web-tool');
    assert.ok(tool.boundaries.length > 20);
  }
  assert.equal(PRODUCTS['deep-blm'].output.length, 3);
  assert.match(PRODUCTS['deep-blm'].problem, /虚构/);
  assert.doesNotMatch(html + js + dev + catalogText, /tech-ma|Tech M(?:&amp;|&)A|ip-guard|IP\s*守护|sourceIP|architecture|技术架构规划/);
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

test('homepage hierarchy keeps details in the dialog and A2A in a compact secondary band', () => {
  const main = html.match(/<main\b[^>]*>([\s\S]*?)<\/main>/)[1];
  assert.deepEqual([...main.matchAll(/<section\b[^>]*\bid="([^"]+)"/g)].map(m => m[1]), ['top','capabilities','online-tools','integrate','contact']);
  assert.doesNotMatch(main, /insight-grid|insight-p[123]-title|a2a-workspace/);
  assert.equal(cards.length, 1);
  for (const [, id, card] of cards) {
    assert.equal(id, 'tech-insight');
    assert.match(card, /订阅 \/ 定制服务/);
    assert.doesNotMatch(card, /<ul|<ol|<details/);
  }
  assert.match(servicesHTML, /研究与专业判断解决具体问题，服务范围与交付成果由双方约定/);
  assert.doesNotMatch(servicesHTML, /deep-blm|Deep BLM/);
  assert.match(main, /id="open-a2a"[^>]*aria-controls="a2a-dialog"/);
  assert.match(main, /概念演示 · 未连接真实 A2A 服务/);
  assert.match(homeCSS, /\.homepage \.integration h2\{font-size:24px/);
  const dialog = html.match(/<dialog id="a2a-dialog"([^>]*)>([\s\S]*?)<\/dialog>/);
  assert.doesNotMatch(dialog[1], /\bopen\b/);
  assert.match(dialog[2], /仅保留 Deep BLM 一个虚构场景，演示样例，非真实客户交付；Deep BLM 工具试用不代表 A2A 服务可用/);
  assert.equal((dialog[2].match(/<option value=/g)||[]).length,1);
  for (const product of Object.values(PRODUCTS)) for (const output of product.output) assert.ok(!main.includes(output));
  assert.match(main, /id="collaborate"/);
  assert.match(main, /data-intent="integration"[^>]*>工具集成/);
  assert.match(main, /id="contact-consulting"[^>]*>咨询服务/);
});

test('four distinct native tool links carry accurate usage and scope boundaries', () => {
  const tools = [...toolsHTML.matchAll(/<article class="tool-card" id="([^"]+)">([\s\S]*?)<\/article>/g)];
  assert.deepEqual(tools.map(m => m[1]), ['deep-blm','patent-health','sanctions-quickcheck','source-slide-editor']);
  assert.deepEqual(tools.map(m => m[2].match(/<h3>(.*?)<\/h3>/)[1]), ['Deep BLM','专利体检','制裁与出口管制速查','Source Slide Editor']);
  assert.deepEqual(tools.map(m => m[2].match(/href="([^"]+)"/)[1]), ['apps/deepblm.html','apps/patent-health-selfcheck.html','apps/sanctions-quickcheck.html','apps/source-slide-editor/']);
  for (const [, , card] of tools) {
    assert.match(card, /class="tool-category"/);
    assert.match(card, /class="tool-hint"/);
    assert.match(card, /<a class="button outline" href="apps\/[^"]+"[^>]*aria-label="[^"]+"[^>]*>(?:使用|打开)/);
    assert.doesNotMatch(card, /data-intent|data-service/);
  }
  assert.match(tools[0][2], /data-demo="deep-blm" data-tool-entry="deep-blm"/);
  assert.match(tools[0][2], /≥1024px.*手机和平板展示使用说明/);
  assert.match(tools[1][2], /不构成法律意见或法律结论/);
  assert.match(tools[2][2], /未命中不等于不受限；不构成法律意见或合规放行结论/);
  assert.match(tools[3][2], /需 JavaScript/);
  assert.match(tools[3][2], /导出修改后的 HTML 文件/);
  assert.doesNotMatch(toolsHTML, /pptx|PPTX|data-demo="(?:patent|sanctions|source)/);
  assert.equal((html.match(/href="apps\/deepblm.html"/g)||[]).length, 1);
  assert.match(js, /#capabilities \.product, #online-tools #deep-blm/);
});

test('homepage styles are local, responsive and isolated from shared documents', () => {
  assert.match(html, /assets\/homepage.css\?v=[a-f0-9]{12}/);
  assert.doesNotMatch(html, /<style|style=|\son(?:click|keydown|load)=/);
  assert.doesNotMatch(dev + privacy, /homepage.css/);
  assert.match(homeCSS, /\.homepage \.product-grid\{display:block;max-width:840px;margin-inline:auto/);
  assert.match(css, /--blue:#0066cc;--hover:#0055ad/);
  assert.doesNotMatch(homeCSS, /--(?:blue|hover|ink|muted|line|soft):|#(?:075cb5|044a94|064f9b)/);
  for (const selector of ['hero', 'section-heading', 'contact']) assert.match(homeCSS, new RegExp(`\\.homepage \\.${selector}\\{text-align:center`));
  assert.match(homeCSS, /min-height:44px/);
  assert.match(homeCSS, /\.homepage \.tools-grid\{display:grid;grid-template-columns:repeat\(2,minmax\(0,1fr\)\)/);
  assert.match(homeCSS, /@media\(max-width:900px\)[\s\S]*grid-template-columns:minmax\(0,1fr\)/);
  assert.match(homeCSS, /@media\(forced-colors:active\)/);
  assert.doesNotMatch(homeCSS, /url\(|@import|gradient|animation:/);
});

test('compact consent prompt retains explicit choices, optional scope and accessible details', () => {
  const banner = html.match(/<aside\b[^>]*data-analytics-banner[\s\S]*?<\/aside>/)[0];
  assert.match(banner, /可选匿名交互统计，不含需求正文/);
  for (const choice of ['accept','reject']) assert.match(banner, new RegExp(`data-consent="${choice}"`));
  assert.match(banner, /<details><summary>统计详情<\/summary><p data-analytics-status role="status">/);
  assert.match(banner, /href="privacy.html"/);
});

test('single service has two distinct labelled actions with generic consulting attribution', () => {
  const cards = [...html.matchAll(/<article class="product"[^>]*>([\s\S]*?)<\/article>/g)].map(match => match[1]).join('');
  const actions = [...cards.matchAll(/<(?:button|a)\b[^>]*(?:data-demo=|data-intent="(?:product|consulting)"|id="open-insight")[^>]*>/g)];
  assert.equal(actions.length,2);
  const names = actions.map(([tag]) => tag.match(/aria-label="([^"]+)"/)?.[1]);
  assert.ok(names.every(Boolean));
  assert.equal(new Set(names).size,2);
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

 test('patent health is the real renamed ten-question local assessment', async () => {
  const app = await read('apps/patent-health-selfcheck.html');
  assert.match(app, /<title>专利体检<\/title>/);
  assert.match(app, /<h1 id="title">专利体检<\/h1>/);
  assert.match(app, /title: "专利体检"/);
  assert.match(app, /name="description" content="专利体检：专利布局健康度自评/);
  assert.match(app, /全部本地计算，不上传任何信息/);
  assert.equal((app.match(/text: "\d+\. /g) || []).length, 10);
});
