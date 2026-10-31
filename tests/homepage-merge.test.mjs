import assert from 'node:assert/strict';
import test from 'node:test';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {canonicalReferrer, observeSource, validatePayload, createSignals} from '../assets/signals.mjs';
// Frozen byte fingerprints from PR15 779d1e1775ed838c6b573f655f7c14f2404dfc78.
const frozenFiles = {
  ".github/workflows/site-checks.yml": "68f0fac3f2bccc4bc64382562be5a2cef5a6ee70978fdf7d3da8710e25830198",
  ".gitignore": "05371ed6a21f2d135fd1d29281c0aaa956254169b40da5397e4b32008d1efc12",
  "CNAME": "b7a85760a477ae329b398bfa48f3d093fdff21a24eb94c8fd51182f9072b4aea",
  "analytics-config.json": "2029a5c6b00139777e3c20a985828f9e003790d2076594779f55f1778819889c",
  "apps/deepblm.html": "65b3f218f7c176ae0a3a22215f7b59eaba32b4b8e7c930b844b92a6ecc23be9f",
  "apps/patent-health-selfcheck.html": "8579f270def6cc3da6834e1f7bf53ab3cc22cff91152e7094317d9fddad5500c",
  "apps/sanctions-quickcheck.html": "3b794df53c16722bd4d814a3ab92d64b6996721e614e2b7b3c83c173e2c06ed7",
  "apps/source-slide-editor/assets/index-BozBbOlu.css": "4c902c22761309605234e39d0cb4c54dff69d9497d7de3f17ae159d5bce9ed78",
  "apps/source-slide-editor/assets/index-DvXwfkHx.js": "99db5614f2a1477f61a80377d06abe9052faefd21d9191ada6170d9e8ab5ca90",
  "apps/source-slide-editor/index.html": "f25609a2b0bd16b12c1b7a8c2eb10022ffc936dba8c0c8ba53d9e23735d0cb14",
  "apps/source-slide-editor/preview-host.html": "b0f60ca9ca226820b372f08a23330936aa06742407dc22a4622ead940a9eb9c9",
  "assets/deeparchi-favicon.png": "ecc52f19baffa81cc44309de247772767e4a5cd98f3a610194dc0d84af6e788f",
  "assets/deeparchi-logo.png": "21d0b1d6e7c5ffd6a39b20bbd680561c2dfc0bcd808116617212b5cf09c3c09c",
  "assets/deepblm-credentials.mjs": {
    "kind": "public-source-fingerprint",
    "sha256": "810c20d2d81364ebdf3952fb0c52b0c1249b92da4096802c8045f3ab3ad463ae"
  },
  "assets/deepblm-data.mjs": "1d8a38cd8d143d70172fb1d2a9f6f1b4c93b331ab36fdf1ce09e1ceddabb56c6",
  "assets/deepblm-entry.mjs": "f53a583dca39cf927391397b68a7c7248215a003567e2e4457a4fa79e3c37fed",
  "assets/deepblm-schema.mjs": "5bb32479cb7694ec0c4716542c8df0a9965467e59a6eccb3918dde112a227577",
  "assets/deepblm-security.mjs": "c142b20b638609c2724316249509a14248eec60e456c5178c8eff76b71392e80",
  "assets/deepblm-sessions.mjs": "6ce6e76d2469c9fdfccf0f30b0175cedbfb21dbe9db2f56831c15c74b9fed984",
  "assets/deepblm-ui.mjs": "d69aea9b2ce2cc84cd389358eccca7154a5f129395d0133c3cdeb8d0dcf75945",
  "assets/deepblm-workspace.mjs": "59b18a3a1abb45b5a300edb971f28526d3563b6b1ce8c21062c8c5401e2ff93a",
  "assets/deepblm.css": "55eae809814bf51ba1bf6ca0d9dbd796cd9f7228221cbee7d38bf54226afa0fe",
  "assets/insight-services.css": "cc40c4fd49fb0dbec564e6bd84168f54ff43bc2701bc585c38f387936e398d5f",
  "assets/signals.mjs": "d72684815971275d5d1ec242966825caa900d4ca8f78e13cc91815b62bdedc59",
  "assets/site.css": "738eb81c4c95dd36cb7ba7e8a7caf8ba5341f4f30bf457dc1d7ab168b5df5597",
  "assets/site.mjs": "603651731d9c7ca2c7c2030fb26d658532e8981664f72a966878bfefca5daf0e",
  "assets/vendor/dompurify/LICENSE": "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30",
  "assets/vendor/dompurify/purify.min.js": "cd37898f9782adf54820c413191b5691803f0f137c799d6edcfd38523b4c2c31",
  "assets/vendor/easymde/LICENSE": "98eee44a1cdad5ad0bb0ea976791ab57b5eef7ac4cafeb162f30e3808564a564",
  "assets/vendor/easymde/easymde.min.css": "6eee36340432776d682e7372ec4a7eb29be4fdb3ffada32c0bfa5e31a5ef34a2",
  "assets/vendor/easymde/easymde.min.js": "2c06bddfd0c89176db08ccf9d42e2beaa9b4f1a4ff8fb2ec0bf1bed25ce08e05",
  "assets/vendor/fontawesome/LICENSE.txt": "0aa8f86525273b2efa4f40f4272a188e187704252170e979dc06879adf68d43c",
  "assets/vendor/fontawesome/css/all.min.css": "1edb1725a9ea8ca4dcf2f5508cee183218aa1685e47c1b23056717f754f58ebf",
  "assets/vendor/fontawesome/webfonts/fa-brands-400.woff2": "748332090c4b8e20f95d0ff59f0be20fa9c889359d3b36d4b886d73376054207",
  "assets/vendor/fontawesome/webfonts/fa-regular-400.woff2": "8e7e5ea1b15f62ab14dbd41768e8fbcd21cc859a4ea5da812457ee714299fb35",
  "assets/vendor/fontawesome/webfonts/fa-solid-900.woff2": "7152a6933ee3d690ec2af3d09da9d701723d16aa3410a6d80f28ff8866f3b880",
  "assets/vendor/manifest.json": "67b525031307051cbca9198aec1dedaf3f0cd1cbb99d2491be6b60c3e0ff158d",
  "docs/superpowers/plans/2026-07-15-deeparchi-landing-page.md": "b481ce468a9900c5c4814eb2b2c8efee5fb5a6e6d8bf9d88be603002a9b31e25",
  "intake/index.html": "9226c401423bd8674ad23a10990b2e412395533ec19a5b1c6ce2af443d00eae7",
  "privacy.html": "0b7dda9fc91f8e788cfda539369db3743b875878dc0b00dd7787052d730f3801",
  "requirements-dev.txt": "e827fdacfd5dc97883736d6ea33ab26b369b1265e74df0bc25d932d3802260c9",
  "scripts/check_site.py": "599bbf6b38ad0317be61a09a55a33031779f9f0fa32e5348bd9fb9b27a9745a5",
  "tests/brand-assets.test.mjs": "5909259e9dad8d0f1a4499cc0cfd26c67164bf20fa0143251a81765b150f6bdd",
  "tests/deepblm-deep-ux-smoke.py": "661bc3a7a7128eb3828e1e230ea891bbdb0239aa9745dbec9f42b430d7ecdf9c",
  "tests/deepblm-sessions.test.mjs": "f73ae0de1cb4cd1ab5d606d8388609393cae4d6a80683d53acaf11c1441ee98d",
  "tests/deepblm-smoke.py": "f57c6dc74c312ca45d8ff3cf805f2508ec50b813fd0cccdf1d7b2481939f8048",
  "tests/deepblm.test.mjs": "fc070690cd72198a7d71ab8860cf9ae6d9c8fd12cc94c4668ec3e18e8dda02b2",
  "tests/signals.test.mjs": "8763ae01dc6e28b6506b12af25b8cff805f7cc1534278a23eacad78e7d0c6e13",
  "tests/test_check_site.py": "b868e19de20f9550e0d6078f5c2fa8550b0e33c801d1e5115afa7f4c0bd4e327"
};
const frozenBlocks = {
  "insight-dialog": "154b217c981b63d69baea7fba695d9432d25eb5b8b0ff24bbb3a3e6815b89dea",
  "a2a-dialog": "6179de4e6d9507e96bde5ee8d1170cadf462d1c987874487f800ad9825e32cf0",
  "demo-dialog": "d3e2226543732855dbf5a778378ca2fcc873667e4d68692f4cfe391b4a0b02ab",
  "demand-dialog": "52601dc8569679da6063a19c522469237be36294122f310860cfe0f7fb5db1fc"
};
const root = new URL('../', import.meta.url);
const read = path => readFileSync(new URL(path, root), 'utf8');
const sha = text => createHash('sha256').update(text).digest('hex');
const html = read('index.html');
const js = read('assets/site.mjs');
const css = read('assets/homepage.css');

test('transfer has one native primary entry and catalog targets its enclosed body', () => {
  const card = html.match(/<article class="product" id="tech-transfer-poc">[\s\S]*?<\/article>/)[0];
  assert.match(card, /<summary class="button primary"[^>]*>了解服务<\/summary>/);
  assert.equal((card.match(/<summary\b/g) || []).length, 1);
  assert.doesNotMatch(card, /<a\b[^>]*href="#transfer/);
  const service = JSON.parse(read('service-catalog.json')).services.find(s => s.id === 'tech-transfer-poc');
  assert.equal(service.details_url, 'index.html#transfer-details-body');
  assert.match(card, /<details[^>]*id="transfer-details"[^>]*>[\s\S]*<p id="transfer-details-body">[\s\S]*?<\/details>/);
  assert.doesNotMatch(html, /\son\w+\s*=/i);
});

test('PR15 production script and dialog transition order are frozen', () => {
  assert.equal(sha(js), '603651731d9c7ca2c7c2030fb26d658532e8981664f72a966878bfefca5daf0e');
  const transition = js.slice(js.indexOf("activeSource = {category, service, source}"), js.indexOf("track('intent_open'"));
  for (const dialog of ['demo', 'a2a', 'insight']) {
    assert.ok(transition.indexOf(`if (${dialog}.open) ${dialog}.close();`) >= 0);
    assert.ok(transition.indexOf(`if (${dialog}.open) ${dialog}.close();`) < transition.indexOf('demand.showModal();'));
  }
  for (const page of ['index.html','developers.html','privacy.html']) {
    assert.match(read(page), /src="assets\/site.mjs\?v=603651731d9c"/);
  }
});

test('protected PR15 files and production dialogs remain byte-identical; tool contracts survive compact copy', () => {
  for (const [path, expected] of Object.entries(frozenFiles)) {
    const fingerprint = typeof expected === 'string' ? expected : expected.sha256;
    if (typeof expected !== 'string') assert.equal(expected.kind, 'public-source-fingerprint');
    assert.equal(sha(readFileSync(new URL(path, root))), fingerprint, path);
  }
  for (const id of ['insight-dialog','a2a-dialog','demo-dialog','demand-dialog']) {
    const pattern = new RegExp(`<dialog id="${id}"[\\s\\S]*?</dialog>`);
    assert.equal(sha(html.match(pattern)[0]), frozenBlocks[id], id);
  }
  const tools = [
    ['deep-blm', 'Deep BLM', 'apps/deepblm.html', '推荐电脑端（≥1024px）；手机和平板展示使用说明。手工填写无需 AI。'],
    ['patent-health', '专利体检', 'apps/patent-health-selfcheck.html', '结果仅供自我评估，不构成法律意见或法律结论。'],
    ['sanctions-quickcheck', '制裁与出口管制速查', 'apps/sanctions-quickcheck.html', '未命中不等于不受限；不构成法律意见或合规放行结论。'],
    ['source-slide-editor', 'Source Slide Editor', 'apps/source-slide-editor/', '推荐电脑端；仅打开可信 HTML 文稿，预览会执行文稿脚本。']
  ];
  for (const [id, name, href, boundary] of tools) {
    const pattern = new RegExp(`<article class="tool-card" id="${id}">[\\s\\S]*?</article>`);
    const card = html.match(pattern)[0];
    assert.ok(card.includes(`<h3>${name}</h3>`), id);
    assert.ok(card.includes(`href="${href}"`), id);
    assert.ok(card.includes(boundary), id);
    assert.match(card, /aria-label="[^"]+"/);
    assert.doesNotMatch(card, /data-intent|data-service/);
    if (id === 'deep-blm') assert.match(card, /data-demo="deep-blm" data-tool-entry="deep-blm"/);
  }
  assert.equal(sha(css).slice(0,12), html.match(/homepage.css\?v=([a-f0-9]{12})/)[1]);
  for (const line of css.split('\n').filter(line => line.includes('{') && !line.trim().startsWith('@'))) {
    for (const selector of line.split('{')[0].split(',')) assert.ok(selector.trim().startsWith('.homepage '), selector);
  }
  assert.doesNotMatch(html, /noindex|设计提案|未发布|未启用统计/);
});

test('both businesses have equal card actions, native details and consulting service=null', () => {
  const cards = [...html.matchAll(/<article class="product" id="([^"]+)">([\s\S]*?)<\/article>/g)];
  assert.deepEqual(cards.map(m => m[1]), ['tech-insight','tech-transfer-poc']);
  for (const [,id,card] of cards) {
    assert.equal((card.match(/<li>/g)||[]).length,3, id);
    assert.equal((card.match(/class="button primary"/g)||[]).length,1, id);
    assert.equal((card.match(/data-intent="consulting" data-surface="cards"/g)||[]).length,1, id);
    assert.doesNotMatch(card, /data-service|data-demo/);
  }
  const catalog = JSON.parse(read('service-catalog.json'));
  for (const service of catalog.services) {
    assert.equal(service.availability, 'manual-contact');
    assert.equal(service.production_ready, false);
    assert.ok(html.includes(`id="${service.details_url.split('#')[1]}"`));
  }
  assert.match(html, /<details class="service-details" id="transfer-details">[\s\S]*?不承诺交易达成、技术验证通过或转化成功/);
  assert.match(js, /const service = category === 'consulting' \|\| !Object.hasOwn\(PRODUCTS, requestedService\) \? null : requestedService/);
  const experience = html.match(/<section[^>]*id="online-tools"[\s\S]*?<\/section>/)[0];
  assert.equal((experience.match(/class="tool-card"/g)||[]).length,4);
  assert.equal((html.match(/class="tool-card"/g)||[]).length,4);
  assert.match(experience, /id="open-a2a"/);
  assert.match(experience, /未连接真实 A2A 服务或运行中的 A2A 端点/);
  assert.equal((html.match(/href="apps\/deepblm.html"/g)||[]).length,1);
  assert.equal((html.match(/class="method-step"/g)||[]).length,3);
});

test('analytics canonicalReferrer retains only an HTTP(S) origin and rejects credentials', () => {
  for (const [raw, expected] of [
    ['https://Example.ORG/private/path?secret=query#fragment', 'https://example.org'],
    ['http://Example.ORG:8080/private?secret=query#fragment', 'http://example.org:8080'],
    [' https://example.org:443/path?q=secret#fragment ', 'https://example.org'],
    ['http://localhost:3000/private?secret=query#fragment', 'http://localhost:3000']
  ]) assert.equal(canonicalReferrer(raw), expected, raw);
  for (const raw of [
    'https://user:password@example.org/private', 'https://user@example.org/',
    'https://:password@example.org/', 'not a URL', '/relative/path',
    'https://bad host.example/', 'ftp://example.org/private',
    'javascript:alert(1)', 'data:text/plain,secret', '', '   ', null, undefined, 42
  ]) assert.equal(canonicalReferrer(raw), '', String(raw));
});

test('analytics observeSource distinguishes missing evidence, empty referrers and invalid input', () => {
  for (const doc of [undefined, null]) {
    assert.deepEqual(observeSource(doc), {state:'no_doc', origin:''});
  }
  const throwing = Object.defineProperty({}, 'referrer', {get() {throw new Error('unavailable');}});
  for (const doc of [{}, {referrer:undefined}, {referrer:null}, {referrer:42}, throwing]) {
    assert.deepEqual(observeSource(doc), {state:'no_prop', origin:''});
  }
  for (const referrer of ['', ' \t\n ']) {
    assert.deepEqual(observeSource({referrer}), {state:'empty', origin:''});
  }
  const prefix = 'https://example.org/';
  const atLimit = prefix + 'x'.repeat(2048 - prefix.length);
  assert.equal(atLimit.length, 2048);
  assert.deepEqual(observeSource({referrer:atLimit}), {state:'ok', origin:'https://example.org'});
  const longHostname = `${'a'.repeat(60)}.org`;
  assert.equal(longHostname.length, 64);
  for (const referrer of [
    `${atLimit}x`, `https://${longHostname}/`, 'https://bad host.example/',
    'not a URL', '/relative', 'https://user:password@example.org/private',
    'ftp://example.org/private', 'javascript:alert(1)', 'data:text/plain,secret'
  ]) assert.deepEqual(observeSource({referrer}), {state:'invalid', origin:''}, referrer);
  for (const [referrer, origin] of [
    ['https://example.org/private?secret=query#fragment', 'https://example.org'],
    ['http://example.org/private', 'http://example.org'],
    ['http://localhost:3000/private', 'http://localhost:3000']
  ]) assert.deepEqual(observeSource({referrer}), {state:'ok', origin});
});

const analyticsFields = {event:'demo_open', service:'ip-guard', category:'product', surface:'cards'};
const analyticsPayload = {
  ...analyticsFields, version:'1', audience:'browser_interaction', is_test:true,
  session_id:'session-123', event_id:'event-123'
};

test('analytics payload validation enforces source state/origin consistency and keeps legacy payloads valid', () => {
  assert.equal(validatePayload(analyticsPayload), true);
  assert.equal(validatePayload({...analyticsPayload, source_state:'ok', source_origin:'https://example.org'}), true);
  for (const state of ['empty', 'no_doc', 'no_prop', 'invalid']) {
    assert.equal(validatePayload({...analyticsPayload, source_state:state, source_origin:''}), true, state);
    assert.equal(validatePayload({...analyticsPayload, source_state:state, source_origin:'https://example.org'}), false, state);
  }
  assert.equal(validatePayload({...analyticsPayload, source_state:'ok', source_origin:''}), false);
  for (const state of ['ok', 'empty', 'no_doc', 'no_prop', 'invalid']) {
    assert.equal(validatePayload({...analyticsPayload, source_state:state}), false, state);
  }
  for (const state of ['unknown', 'internal', 'external', '', null, 42]) {
    for (const origin of ['', 'https://example.org']) {
      assert.equal(validatePayload({...analyticsPayload, source_state:state, source_origin:origin}), false);
    }
  }
});

function analyticsAdapter() {
  const calls = [];
  let sequence = 0;
  const adapter = createSignals({
    version:'1', enabled:true, endpoint:'https://metrics.example.org/receive', consent_required:true
  }, {
    isTest:true,
    idFactory:() => `analytics-${++sequence}`,
    transport:async (endpoint, body) => {calls.push({endpoint, body}); return {ok:true};}
  });
  adapter.setConsent(true);
  return {adapter, calls};
}

function analyticsDocument(t, doc) {
  const original = Object.getOwnPropertyDescriptor(globalThis, 'document');
  t.after(() => {
    if (original) Object.defineProperty(globalThis, 'document', original);
    else delete globalThis.document;
  });
  Object.defineProperty(globalThis, 'document', {configurable:true, writable:true, value:doc});
}

test('analytics track emits only source evidence through the explicit in-memory transport', async t => {
  for (const [name, doc, state, origin] of [
    ['HTTPS strips private URL parts', {referrer:'https://Example.ORG/private?secret=query#fragment'}, 'ok', 'https://example.org'],
    ['HTTP remains evidence', {referrer:'http://example.org/private'}, 'ok', 'http://example.org'],
    ['localhost remains evidence', {referrer:'http://localhost:3000/private'}, 'ok', 'http://localhost:3000'],
    ['missing document', undefined, 'no_doc', ''],
    ['missing property', {}, 'no_prop', ''],
    ['empty referrer', {referrer:''}, 'empty', ''],
    ['malformed referrer', {referrer:'https://bad host.example/private?secret=query#fragment'}, 'invalid', ''],
    ['credentials rejected', {referrer:'https://user:password@example.org/private'}, 'invalid', ''],
    ['oversized raw referrer', {referrer:`https://example.org/${'x'.repeat(2048)}`}, 'invalid', '']
  ]) {
    await t.test(name, async t => {
      analyticsDocument(t, doc);
      const {adapter, calls} = analyticsAdapter();
      assert.equal(await adapter.track(analyticsFields), true);
      assert.equal(calls.length, 1);
      assert.equal(calls[0].endpoint, 'https://metrics.example.org/receive');
      const body = calls[0].body;
      assert.deepEqual(body, {
        ...analyticsFields, version:'1', audience:'browser_interaction', is_test:true,
        session_id:'analytics-1', event_id:'analytics-2', source_state:state, source_origin:origin
      });
      assert.deepEqual(Object.keys(body).filter(key => key.startsWith('source_')).sort(), ['source_origin', 'source_state']);
      for (const key of ['source_class', 'source_reason', 'source_src']) assert.equal(Object.hasOwn(body, key), false);
      for (const label of ['internal', 'external']) assert.equal(Object.values(body).includes(label), false);
      assert.equal(validatePayload(body), true);
      assert.doesNotMatch(JSON.stringify(body), /private|secret|fragment|password|bad host/);
    });
  }
});

test('analytics track refuses caller-supplied source fields before invoking transport', async t => {
  analyticsDocument(t, {referrer:'https://example.org/private'});
  for (const [key, value] of [
    ['source_state', 'ok'], ['source_origin', 'https://forged.example.org'],
    ['source_class', 'external'], ['source_reason', 'caller'], ['source_src', 'internal'],
    ['source_custom', 'invented']
  ]) {
    const {adapter, calls} = analyticsAdapter();
    assert.equal(await adapter.track({...analyticsFields, [key]:value}), false, key);
    assert.deepEqual(calls, [], key);
  }
});
