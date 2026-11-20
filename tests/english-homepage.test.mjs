import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {EN, translator, analyticsStatus, englishMailDraft} from '../assets/homepage-locale.mjs';
import {createSignals, mailDraft} from '../assets/signals.mjs';

const root = new URL('../', import.meta.url);
const read = path => readFileSync(new URL(path, root), 'utf8');
const baseline = JSON.parse(read('tests/fixtures/english-baseline.json'));
const english = read('en.html');
const chinese = read('index.html');
const sha = text => createHash('sha256').update(text).digest('hex');
const unversion = html => html.replace(/(assets\/(?:site.mjs|homepage.css)\?v=)[a-f0-9]{12}/g, '$1HASH');

test('Chinese homepage preserves baseline bytes except language links, alternates and authorized asset versions', () => {
  const stripped = chinese.replace(/  <link rel="alternate"[^>]+>\n/g, '')
    .replace('<a class="language-switch" href="en.html" lang="en" hreflang="en" aria-label="English homepage">English</a>', '');
  assert.equal(sha(unversion(stripped)), baseline.normalized_sha256['index.html']);
  for (const page of ['developers.html','privacy.html']) assert.equal(sha(unversion(read(page))), baseline.normalized_sha256[page], page);
  for (const path of ['assets/signals.mjs','analytics-config.json','CNAME','service-catalog.json',
    'apps/deepblm.html','apps/patent-health-selfcheck.html','apps/sanctions-quickcheck.html',
    'apps/source-slide-editor/index.html']) assert.equal(sha(read(path)), baseline.normalized_sha256[path], path);
  const css = read('assets/homepage.css');
  assert.equal(sha(css.slice(0, css.indexOf('/* English copy'))), baseline.normalized_sha256['assets/homepage.css']);
  for (const selector of css.slice(css.indexOf('/* English copy')).matchAll(/([^{}]+)\{/g)) {
    if (selector[1].trim().startsWith('@')) continue;
    for (const part of selector[1].replace(/\/\*.*?\*\//s, '').split(',')) assert.match(part, /:lang\(en\)/);
  }
});

test('static English document has reciprocal language links, matching structure and complete local cache versions', () => {
  assert.match(english, /<html lang="en">/);
  assert.match(chinese, /href="en.html" lang="en" hreflang="en" aria-label="English homepage">English/);
  assert.match(english, /href="index.html" lang="zh-CN" hreflang="zh-CN" aria-label="Chinese homepage">中文 \(Chinese\)/);
  for (const page of [english, chinese]) {
    assert.match(page, /rel="alternate" hreflang="zh-CN" href="index.html"/);
    assert.match(page, /rel="alternate" hreflang="en" href="en.html"/);
    for (const asset of ['assets/site.mjs','assets/homepage.css','assets/site.css','assets/insight-services.css']) {
      assert.ok(page.includes(`${asset}?v=${sha(read(asset)).slice(0,12)}`), asset);
    }
  }
  assert.deepEqual([...english.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]), [...chinese.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]));
  assert.match(read('assets/site.mjs'), new RegExp(`homepage-locale.mjs\\?v=${sha(read('assets/homepage-locale.mjs')).slice(0,12)}`));
  const escape = text => text.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#x27;');
  let generated = chinese;
  for (const [source,target] of Object.entries(EN).sort((a,b)=>b[0].length-a[0].length)) generated = generated.replaceAll(source,escape(target));
  generated = generated.replace('lang="zh-CN"','lang="en"').replace('href="en.html" lang="en" hreflang="en" aria-label="English homepage">English','href="index.html" lang="zh-CN" hreflang="zh-CN" aria-label="Chinese homepage">中文 (Chinese)');
  assert.equal(english,generated);
});

test('English text has no unexpected Han and clearly labels every Chinese destination', () => {
  const permitted = english.replace('Legal company name: 上海申渡架固信息技术有限公司', '').replace('>中文 (Chinese)<', '><');
  assert.doesNotMatch(permitted, /\p{Script=Han}/u);
  for (const match of english.matchAll(/<a\b([^>]*href="(?:apps\/[^"#]+|developers.html|privacy.html|service-catalog.json)"[^>]*)>([\s\S]*?)<\/a>/g)) {
    assert.match(match[2], /Chinese/, match[0]);
    const aria = match[1].match(/aria-label="([^"]+)"/);
    if (aria) assert.match(aria[1], /Chinese/);
  }
  assert.equal((english.match(/href="apps\//g)||[]).length, 4);
  assert.doesNotMatch(english, /<style|\son\w+=|https?:\/\/(?:fonts|cdn)/);
});

test('equivalent business disclaimers and no-JS service details are delivered as static HTML', () => {
  for (const text of [
    'we do not guarantee a transaction, successful technical validation or commercialization.',
    'Service scope, delivery schedule and deliverable format are subject to mutual agreement.',
    'P1 and P2 are ongoing subscriptions; P3 is customized to project needs.',
    'Results are for self assessment only and do not constitute legal advice or legal conclusions.',
    'No match does not mean unrestricted. Results do not constitute legal advice or a compliance clearance decision.',
    'Open only trusted HTML documents: previews execute document scripts.',
    'The Deep BLM tool trial does not imply A2A service availability.',
    'executes no real tasks and uploads no business content.',
    'This is an email draft; nothing has been sent.',
    'This page does not collect your personal email address or phone number.',
    'Consent lasts only for this page and can be withdrawn at any time. DNT/GPC is respected.'
  ]) assert.ok(english.includes(text), text);
  assert.match(english, /<details id="insight-details"[\s\S]*P1[\s\S]*P2[\s\S]*P3/);
  assert.match(english, /<noscript>[\s\S]*mailto:contact@deeparchi.com.cn/);
  assert.match(english, /id="transfer-details-body"/);
});

test('dictionary covers runtime literals while Chinese messages remain exactly identical', () => {
  const t = translator('en');
  const zh = translator();
  for (const [source, value] of Object.entries(EN)) {
    assert.equal(zh(source), source);
    assert.equal(t(source), value);
    assert.doesNotMatch(value.replace('上海申渡架固信息技术有限公司',''), /\p{Script=Han}/u);
  }
  const runtime = read('assets/site.mjs');
  for (const [, literal] of runtime.matchAll(/\bt\('([^']+)'/g)) assert.ok(EN[literal], literal);
  assert.match(t('样例服务目录：{name}。当前仅提供概念展示，未发现或连接运行中的 Agent。', {name:'Deep BLM'}), /catalog: Deep BLM/);
  assert.throws(() => t('missing key'), /Missing English message/);
  assert.deepEqual([...runtime.matchAll(/track\('[^\n]+/g)].map(m=>m[0]), baseline.track_calls);
});

test('every analytics status is localized only at display, including fail-closed and DNT/GPC', () => {
  const config = {version:'1',enabled:true,endpoint:'https://metrics.example.org/receive',consent_required:true};
  for (const local of [false,true]) for (const raw of [null,{}, {...config,enabled:false,endpoint:null},config]) {
    for (const navigatorLike of [{},{doNotTrack:'1'},{globalPrivacyControl:true}]) {
      const signals = createSignals(raw, {local,navigatorLike});
      for (const choice of [false,true,false]) {
        signals.setConsent(choice);
        const source = signals.status();
        assert.equal(analyticsStatus(source,translator()), source);
        const status = analyticsStatus(source,translator('en'));
        assert.doesNotMatch(status, /\p{Script=Han}/u);
        assert.ok(status.length > 20);
        if (local) assert.match(status, /no live reporting/);
      }
    }
  }
});

test('English email drafts preserve content safely, RFC6068 encoding, limits and copy fallback without sending', () => {
  const input = {source:'Service inquiry',problem:'<b>Plan</b> + 50% & details\nSecond line',result:'',constraints:''};
  const draft = englishMailDraft(input);
  const uri = new URL(draft.uri);
  assert.equal(uri.protocol,'mailto:');
  assert.equal(uri.pathname,'contact@deeparchi.com.cn');
  assert.match(uri.searchParams.get('subject'), /Service inquiry/);
  assert.ok(uri.searchParams.get('body').includes(input.problem));
  assert.match(draft.text, /Desired outcome: Not provided\r\nConstraints: Not provided/);
  assert.match(draft.text, /^To: contact@deeparchi.com.cn\nSubject: DeepArchi/);
  assert.ok(draft.uri.includes('%2B') && draft.uri.includes('%20'));
  assert.ok(!draft.uri.includes('+') && !uri.hash);
  for (const problem of ['', '  ', 'x'.repeat(501), null]) assert.throws(()=>englishMailDraft({...input,problem}));
  for (const patch of [{source:'x\r\nInjected: true'}, {result:'x'.repeat(501)}, {constraints:'x'.repeat(301)}]) assert.throws(()=>englishMailDraft({...input,...patch}));
  const long = englishMailDraft({...input,problem:'&'.repeat(500),result:'&'.repeat(500),constraints:'&'.repeat(300)});
  assert.equal(long.tooLong,true);
  assert.equal(new URL(long.uri).searchParams.has('body'),false);
  assert.ok(long.text.includes('&'.repeat(500)));
  assert.match(mailDraft({...input,source:'咨询服务'}).text,/收件人：/);
});
