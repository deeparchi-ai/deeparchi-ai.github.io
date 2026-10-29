import assert from 'node:assert/strict';
import test from 'node:test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {steps, LIMITS, normalizeImport, structuredExport, normalizeReport, normalizeConfig, validateEndpoint, TOOL_KEYS, parseBoundedJSON} from '../assets/deepblm-data.mjs';
import {REMEMBERED_KEY, canonicalConfig, validKey, matchesDestination, rememberedRecord, restoreRemembered} from '../assets/deepblm-credentials.mjs';
const read = name => readFile(new URL(`../${name}`, import.meta.url), 'utf8');
const allFields = Object.fromEntries(steps.flatMap(s => s.fields.map(f => [`${s.id}-${f.name}`, f.type === 'table' ? [f.columns.map((c, i) => `虚构验收 ${c} ${i}`), f.columns.map(() => '')] : `虚构验收：${s.title} / ${f.name}\n**保留内容**`])));
allFields['strategy-validation-completed'] = 'true';
allFields['revision-completed'] = false;
const snapshot = Object.fromEntries(steps.map(s => [s.id, {title: s.title, description: s.description, fields: Object.fromEntries(s.fields.map(f => [f.name, f.type === 'table' ? {type: 'table', columns: f.columns, data: allFields[`${s.id}-${f.name}`]} : {type: f.type, value: allFields[`${s.id}-${f.name}`]}]))}]));
const metadata = {validationReport: {content: '虚构校验报告 <img src=x onerror=alert(1)>', savedAt: 1, stepData: snapshot}};

test('both flat and structured exports retain every field in all 15 steps, table cells, flags and report snapshots', () => {
  assert.equal(steps.length, 15);
  assert.deepEqual(normalizeImport(JSON.stringify(allFields)), {formData: allFields, metadata: {}});
  const structured = structuredExport(allFields, metadata, 'fixture-only');
  const restored = normalizeImport(JSON.stringify(structured));
  assert.deepEqual(restored.formData, allFields);
  assert.deepEqual(restored.metadata.validationReport, metadata.validationReport);
  assert.deepEqual(restored.metadata.header, {title: 'BLM扩展框架战略规划', created: 'fixture-only'});
  const customHeader = normalizeImport({...structured, title: '虚构自定义规划标题'});
  assert.equal(structuredExport(customHeader.formData, customHeader.metadata).title, '虚构自定义规划标题');
  assert.equal(structuredExport(customHeader.formData, customHeader.metadata).created, 'fixture-only');
  assert.deepEqual(normalizeImport(JSON.stringify(structuredExport(restored.formData, restored.metadata))).formData, allFields);
  assert.equal(restored.formData['gap-业绩差距'][0].length, 5);
  const old = structuredExport({}, {}); delete old.metadata;
  old.steps[1].data['业绩差距'] = '';
  assert.deepEqual(normalizeImport(old).formData['gap-业绩差距'], []);
  assert.deepEqual(normalizeImport('{}').formData, {});
});

test('invalid imports reject unknown fields, table shapes, types, duplicate steps, prototype keys and resource limits', () => {
  const bad = [null, [], 'broken', '{"__proto__":{"polluted":true}}', '{"company-info-主营业务":{"constructor":"x"}}', '{"prototype":1}', '{"unrecognized":"x"}', '{"gap-业绩差距":[["wrong"]]}', '{"company-info-主营业务":42}', '{"revision-completed":"maybe"}', '{"company-info-企业名称":null}', JSON.stringify({'company-info-主营业务': 'x'.repeat(LIMITS.text + 1)}), JSON.stringify({'gap-业绩差距': Array.from({length: LIMITS.rows + 1}, () => Array(5).fill(''))}), JSON.stringify({'gap-业绩差距': [Array(5).fill('x'.repeat(LIMITS.cell + 1))]}), ' '.repeat(LIMITS.bytes + 1), '{"a":' + '['.repeat(20) + '0' + ']'.repeat(20) + '}', JSON.stringify({steps: [{id: 'values', data: {}}, {id: 'values', data: {}}]}), JSON.stringify({steps: [{id: 'made-up', data: {}}]}), JSON.stringify({steps: [], metadata: {version: 2}})];
  for (const input of bad) assert.throws(() => normalizeImport(input), String(input).slice(0, 70));
  assert.equal({}.polluted, undefined);
  assert.throws(() => parseBoundedJSON(JSON.stringify(Array(LIMITS.nodes + 1).fill(0))));
  assert.throws(() => normalizeImport({steps: [], metadata: {version: 1, completion: {secret: 'x'}}}));
  assert.throws(() => normalizeReport({content: 'x', extra: true}));
  assert.throws(() => normalizeReport({content: 'x', stepData: {values: {fields: {'核心价值观': {type: 'table', data: []}}}}}));
});

test('company short-field limit is retained in both import formats', () => {
  const id = 'company-info-企业名称';
  const valid = {[id]: '甲'.repeat(40)};
  assert.equal(normalizeImport(valid).formData[id].length, 40);
  assert.throws(() => normalizeImport({[id]: '甲'.repeat(41)}));
  const exported = structuredExport(valid);
  exported.steps[0].data['企业名称'] = '甲'.repeat(41);
  assert.throws(() => normalizeImport(exported));
});

test('preferences accept only nonsecret configuration; endpoints reject credentials and local/private literals', () => {
  const config = {provider: 'custom', endpoint: 'https://api.fixture-provider.example.org/v1/chat/completions', model: 'fixture-model-not-live'};
  assert.deepEqual(normalizeConfig(JSON.stringify(config)), config);
  for (const secret of ['apiKey', 'key', 'token', '__proto__']) assert.throws(() => normalizeConfig(JSON.parse(`{"provider":"custom","endpoint":"","model":"x","${secret}":"fixture-only"}`)));
  for (const url of ['http://api.fixture-provider.example.org', 'https://user:fixture@example.org', 'https://localhost', 'https://localhost.', 'https://api.local.', 'https://127.0.0.1', 'https://10.1.2.3', 'https://169.254.169.254', 'https://2130706433', 'https://[::1]', 'https://[::ffff:127.0.0.1]', 'https://api.local', 'https://api.internal', 'https://api.localhost', 'https://api.localdomain', 'https://api.home.arpa', 'https://127.0.0.1.nip.io', 'https://api.lvh.me', 'https://api.fixture-provider.example.org/?key=fixture', 'https://api.fixture-provider.example.org/#fragment', 'https://api.fixture-provider.example.org:8443']) assert.throws(() => validateEndpoint(url), url);
  assert.equal(validateEndpoint(config.endpoint), config.endpoint);
  assert.ok(!TOOL_KEYS.some(k => k.startsWith('da-')));
});

test('remembered credentials require explicit versioned opt-in, strict bounded shape and exact canonical destination', () => {
  const config = {provider: 'custom', endpoint: 'https://api.fixture-provider.example.org/v1/chat/completions', model: 'fixture-only'};
  const key = 'fixture-only-not-real';
  const record = rememberedRecord(key, config);
  assert.deepEqual(restoreRemembered(JSON.stringify(record), config), record);
  assert.deepEqual(canonicalConfig({...config, endpoint: config.endpoint + '/'}), config);
  assert.equal(matchesDestination(record, {...config, model: 'another-fixture-model'}), true);
  assert.equal(matchesDestination(record, {...config, provider: 'openai'}), false);
  assert.equal(matchesDestination(record, {...config, endpoint: config.endpoint + '/other'}), false);
  assert.ok(TOOL_KEYS.includes(REMEMBERED_KEY));
  for (const value of ['', ' ', 'a\nb', 'a\rb', 'x'.repeat(4097), null, 1]) assert.equal(validKey(value), false);
  for (const value of [null, [], {}, {...record, version: 2}, {...record, remembered: false}, {...record, remembered: 'true'},
    {...record, key: ''}, {...record, key: 'x'.repeat(4097)}, {...record, key: 'a\nb'}, {...record, key: {}},
    {...record, endpoint: config.endpoint + '/'}, {...record, provider: 'openai'}, {...record, endpoint: config.endpoint + '/other'},
    {...record, endpoint: 'https://localhost'}, {...record, consent: true}, {...record, extra: 'rejected'}, {apiKey: key}]) {
    assert.throws(() => restoreRemembered(JSON.stringify(value), config));
  }
  for (const raw of ['{broken', ' '.repeat(32769), JSON.stringify(record).replace('"version":1', '"__proto__":{},"version":1')]) {
    assert.throws(() => restoreRemembered(raw, config));
  }
  // HTML-like fixture secrets remain data. Even a valid credential cannot enter draft formats.
  const htmlRecord = rememberedRecord('<img/src=x/onerror=alert(1)>', config);
  assert.equal(restoreRemembered(JSON.stringify(htmlRecord), config).key, htmlRecord.key);
  assert.throws(() => normalizeImport(record));
  assert.throws(() => normalizeConfig(record));
  assert.doesNotMatch(JSON.stringify(structuredExport({})), /fixture-only-not-real|remembered-key/);
});

test('pinned local vendor assets match every manifest hash and byte count', async () => {
  const manifest = JSON.parse(await read('assets/vendor/manifest.json'));
  assert.equal(manifest.length, 3);
  for (const vendor of manifest) for (const file of vendor.files) {
    const bytes = await readFile(new URL(`../${file.path}`, import.meta.url));
    assert.equal(bytes.length, file.bytes, file.path);
    assert.equal(createHash('sha256').update(bytes).digest('hex'), file.sha256, file.path);
  }
});

test('public entry remains native and mobile loader has no storage, AI UI, analytics or eager vendors', async () => {
  const [home, entry, gate, workspace, security, css] = await Promise.all(['index.html', 'apps/deepblm.html', 'assets/deepblm-entry.mjs', 'assets/deepblm-workspace.mjs', 'assets/deepblm-security.mjs', 'assets/deepblm.css'].map(read));
  assert.match(home, /<a[^>]*href="apps\/deepblm.html"[^>]*data-demo="deep-blm"[^>]*data-tool-entry="deep-blm"[^>]*>打开规划工具（试用）<\/a>/);
  assert.match(entry, /img class="brand-logo" src="\.\.\/assets\/deeparchi-logo.png" width="498" height="512"/);
  assert.doesNotMatch(entry, /vendor\/|ai-key|site\.mjs|signals\.mjs|https?:\/\//);
  assert.match(gate, /if \(desktop.matches\)/);
  assert.doesNotMatch(gate, /localStorage|sessionStorage|fetch\(|vendor\//);
  assert.doesNotMatch(workspace, /da-ai-config|Cursor|allorigins|duckduckgo|signals\.mjs|site\.mjs|localStorage\.clear|sessionStorage|console\./i);
  assert.match(workspace, /autoDownloadFontAwesome: false/);
  assert.match(workspace, /spellChecker: false/);
  assert.equal((workspace.match(/\bfetch\(/g) || []).length, 1);
  assert.doesNotMatch(workspace, /on(?:click|input|change)=|eval\(|new Function|\.prototype\s*=/);
  assert.match(security, /window.DOMPurify.sanitize/);
  assert.match(security, /ALLOWED_TAGS: allowed/);
  assert.doesNotMatch(css, /@import|https?:\/\//);
  assert.match(entry, /script-src 'self'/);
  assert.doesNotMatch(entry, /unsafe-eval/);
});

test('workspace groups retain every step exactly once; completeness follows actual text and table values', async () => {
  const {groups, groupFor, missingFields, simpleField} = await import('../assets/deepblm-ui.mjs');
  assert.deepEqual(groups.map(g => g.name), ['现状与洞察', '战略选择', '执行与保障', '检查与修订']);
  assert.deepEqual(groups.flatMap(g => steps.slice(g.start, g.end).map(s => s.id)), steps.map(s => s.id));
  assert.equal(groupFor(12), '执行与保障');
  assert.equal(groupFor(13), '检查与修订');
  assert.equal(steps[0].fields.filter(f => simpleField(steps[0], f)).length, 4);
  const empty = missingFields(steps, {});
  assert.ok(empty.some(f => f.id === 'gap-业绩差距' && f.index === 1));
  assert.ok(!empty.some(f => f.index > 12));
  const values = {'company-info-企业名称': '   ', 'gap-业绩差距': [Array(5).fill(' ')]};
  assert.equal(missingFields(steps, values).length, empty.length);
  values['company-info-企业名称'] = '虚构验收';
  values['gap-业绩差距'][0][2] = '现状依据待核实';
  assert.equal(missingFields(steps, values).length, empty.length - 2);
  values['company-info-企业名称'] = '';
  assert.ok(missingFields(steps, values).some(f => f.id === 'company-info-企业名称'));
});
