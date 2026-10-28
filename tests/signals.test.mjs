import assert from 'node:assert/strict';
import test from 'node:test';
import {validateConfig, validatePayload, privacyBlocked, createSignals, mailDraft} from '../assets/signals.mjs';
const fixture = {version:'1', enabled:true, endpoint:'https://metrics.example.org/receive', consent_required:true};
const fields = {event:'demo_open',service:'ip-guard',category:'product',surface:'cards'};
const payload = {...fields,version:'1',audience:'browser_interaction',is_test:true,session_id:'session-123',event_id:'event-123'};
let sequence = 0;
const idFactory = () => `fixture-${++sequence}`;

test('configuration fails closed for disabled, malformed or unsafe receivers', () => {
  assert.ok(validateConfig({version:'1',enabled:false,endpoint:null,consent_required:true}));
  assert.ok(validateConfig(fixture));
  for (const change of [{endpoint:null},{endpoint:'http://metrics.example.org/a'},{endpoint:'https://127.0.0.1/a'},{endpoint:'https://localhost/a'},{endpoint:'https://foo.local/a'},{endpoint:'https://foo.test/a'},{endpoint:'https://a:b@example.org/a'},{endpoint:'https://metrics.example.org/a?q=x'},{endpoint:'https://metrics.example.org/a#x'},{endpoint:'javascript:alert(1)'},{consent_required:false},{enabled:'true'},{version:'2'},{script:'evil'},{site_id:'free text with email@'},{enabled:false}]) assert.equal(validateConfig({...fixture,...change}),null,JSON.stringify(change));
  assert.equal(validateConfig(null),null);
});

test('payload schema rejects unknown fields, events, products, free text and invalid steps', () => {
  assert.ok(validatePayload(payload));
  for (const change of [{problem:'secret'},{email:'secret@example.org'},{url:'https://example.org/'},{event:'unknown'},{service:'unknown'},{category:'unknown'},{surface:'unknown'},{audience:'agent'},{audience:'human'},{version:'2'},{session_id:'user@example.org'},{event_id:'short'},{is_test:1},{step:1},{service:null}]) assert.equal(validatePayload({...payload,...change}),false,JSON.stringify(change));
  assert.ok(validatePayload({...payload,event:'a2a_step',step:5}));
  for (const step of [undefined,0,6,1.1,'1']) assert.equal(validatePayload({...payload,event:'a2a_step',step}),false);
});

test('RFC6068 draft preserves Chinese, literal plus, HTML-like text and line breaks only in local mailto', () => {
  const problem = '<img src=x onerror=alert(1)> + 中文 & x\n第二行';
  const draft = mailDraft({source:'产品需求 / Tech M&A',problem,result:'result',constraints:'constraint'});
  const url = new URL(draft.uri);
  assert.equal(url.pathname,'contact@deeparchi.com.cn');
  assert.equal(url.searchParams.get('subject'),'DeepArchi｜产品需求 / Tech M&A 需求意向');
  assert.ok(url.searchParams.get('body').includes(problem));
  assert.ok(draft.text.includes(problem));
  assert.ok(draft.uri.includes('%20'));
  assert.ok(!draft.uri.includes('+'));
  assert.equal(url.hash,'');
  for (const change of [{problem:' '},{problem:'x'.repeat(501)},{result:'x'.repeat(501)},{constraints:'x'.repeat(301)},{source:'bad\nheader'}]) assert.throws(() => mailDraft({source:'通用需求',problem:'ok',...change}));
});

test('consent, DNT/GPC, disabled config and local/test guard send nothing', async () => {
  const calls = [];
  const transport = async (...args) => {calls.push(args);return {ok:true};};
  for (const navigatorLike of [{doNotTrack:'1'},{doNotTrack:'yes'},{globalPrivacyControl:true}]) {
    assert.ok(privacyBlocked(navigatorLike));
    const adapter = createSignals(fixture,{navigatorLike,transport,idFactory});
    adapter.setConsent(true);
    assert.equal(await adapter.track(fields),false);
  }
  const disabled = createSignals({...fixture,enabled:false,endpoint:null},{transport,idFactory});
  disabled.setConsent(true);
  assert.equal(await disabled.track(fields),false);
  const adapter = createSignals(fixture,{transport,idFactory});
  assert.equal(await adapter.track(fields),false);
  adapter.setConsent(false);
  assert.equal(await adapter.track(fields),false);
  for (const guard of [{local:true},{isTest:true}]) {
    const guarded = createSignals(fixture,{...guard,idFactory});
    guarded.setConsent(true);
    assert.equal(await guarded.track(fields),false);
  }
  assert.deepEqual(calls,[]);
});

test('fixture transport receives only allowlisted data after consent; dedupe and refusal work', async () => {
  const calls = [];
  const adapter = createSignals(fixture,{isTest:true,idFactory,transport:async (endpoint,body) => {calls.push({endpoint,body});return {ok:true};}});
  adapter.setConsent(true);
  assert.equal(await adapter.track({...fields,problem:'NEVER SEND'}),false);
  assert.equal(await adapter.track(fields),true);
  assert.equal(await adapter.track(fields),false);
  assert.equal(calls.length,1);
  assert.ok(validatePayload(calls[0].body));
  assert.equal(calls[0].body.is_test,true);
  assert.ok(!JSON.stringify(calls).includes('NEVER SEND'));
  adapter.setConsent(false);
  assert.equal(await adapter.track({...fields,event:'demo_complete'}),false);
  adapter.setConsent(true);
  assert.equal(await adapter.track(fields),true);
  assert.notEqual(calls[0].body.session_id,calls[1].body.session_id);
});

test('fixture network failure does not throw or block contact', async () => {
  const adapter = createSignals(fixture,{isTest:true,idFactory,transport:async () => {throw new Error('fixture offline');}});
  adapter.setConsent(true);
  assert.equal(await adapter.track(fields),false);
  assert.ok(mailDraft({source:'通用需求',problem:'继续使用'}).uri.startsWith('mailto:'));
});
