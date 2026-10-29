// Page-memory writing sessions and honest per-field completion.
// No browser, storage or network: imports the shipped modules directly.
import test from 'node:test';
import assert from 'node:assert/strict';
import {writingSessions, resultEligible} from '../assets/deepblm-sessions.mjs';
import {hasContent, stepCompletion} from '../assets/deepblm-ui.mjs';

const at = (target, action = 'draft', revision = {planning: 0, connection: 0}) => ({
  state: 'success', target, action, ...revision, draft: `draft:${target}`, original: `original:${target}`,
});

test('resultEligible requires a successful result bound to target, action and both revisions', () => {
  const result = at('company-info-企业名称');
  assert.equal(resultEligible(result, {planning: 0, connection: 0}, 'company-info-企业名称', 'draft'), true);
  assert.equal(resultEligible(result, {planning: 1, connection: 0}, 'company-info-企业名称', 'draft'), false, 'planning revision changed');
  assert.equal(resultEligible(result, {planning: 0, connection: 1}, 'company-info-企业名称', 'draft'), false, 'connection revision changed');
  assert.equal(resultEligible(result, {planning: 0, connection: 0}, 'company-info-主营业务', 'draft'), false, 'other target');
  assert.equal(resultEligible(result, {planning: 0, connection: 0}, 'company-info-企业名称', 'inspect'), false, 'other action');
  for (const state of ['empty', 'loading', 'error', 'stale', 'adopted']) {
    assert.equal(resultEligible({...result, state}, {planning: 0, connection: 0}, 'company-info-企业名称', 'draft'), false, state);
  }
  assert.equal(resultEligible(null, {planning: 0, connection: 0}, 'company-info-企业名称', 'draft'), false);
  assert.equal(resultEligible(undefined, {planning: 0, connection: 0}, 'company-info-企业名称', 'draft'), false);
});

test('revisions are monotonic and independent per kind', () => {
  const store = writingSessions();
  assert.deepEqual(store.revision(), {planning: 0, connection: 0});
  store.invalidate('planning');
  assert.deepEqual(store.revision(), {planning: 1, connection: 0});
  store.invalidate('connection');
  assert.deepEqual(store.revision(), {planning: 1, connection: 1});
  store.invalidate();
  assert.deepEqual(store.revision(), {planning: 2, connection: 1}, 'default invalidation is a planning change');
  store.invalidate('planning');
  store.invalidate('planning');
  assert.equal(store.revision().planning, 4);
});

test('a stored result survives reads but not any revision change', () => {
  const store = writingSessions();
  store.set('company-info-企业名称', {question: '虚构要求', action: 'draft', result: at('company-info-企业名称')});
  const kept = store.get('company-info-企业名称');
  assert.equal(kept.question, '虚构要求');
  assert.equal(kept.action, 'draft');
  assert.equal(resultEligible(kept.result, store.revision(), 'company-info-企业名称', 'draft'), true);

  store.invalidate('planning');
  assert.equal(store.get('company-info-企业名称').result, undefined, 'planning change drops the old result');
  assert.equal(store.get('company-info-企业名称').question, '虚构要求', 'user text is retained');
  store.invalidate('connection');
  assert.equal(store.get('company-info-企业名称').result, undefined);
});

test('set refuses to persist a result that is already stale', () => {
  const store = writingSessions();
  const stale = at('company-info-企业名称');
  store.invalidate('planning');
  store.set('company-info-企业名称', {question: '', action: 'draft', result: stale});
  assert.equal(store.get('company-info-企业名称').result, undefined, 'an old revision can never be rehydrated');

  const fresh = at('company-info-企业名称', 'draft', store.revision());
  store.set('company-info-企业名称', {question: '', action: 'draft', result: fresh});
  assert.equal(store.get('company-info-企业名称').result.draft, 'draft:company-info-企业名称');

  store.set('company-info-企业名称', {question: '', action: 'inspect', result: {...fresh, action: 'draft'}});
  assert.equal(store.get('company-info-企业名称').result, undefined, 'result must match the stored action');
});

test('bounded in-memory store evicts least recently used targets', () => {
  const store = writingSessions({maxTargets: 2});
  store.set('company-info-企业名称', {question: 'a', action: 'draft'});
  store.set('company-info-主营业务', {question: 'b', action: 'draft'});
  assert.equal(store.get('company-info-企业名称').question, 'a');
  store.set('company-info-行业描述', {question: 'c', action: 'draft'});
  assert.equal(store.get('company-info-企业名称').question, 'a', 'recently read target stays');
  assert.equal(store.get('company-info-主营业务'), undefined, 'least recently used target is evicted');
  assert.equal(store.get('company-info-行业描述').question, 'c');
});

test('bounded store enforces the character budget across question, draft and original', () => {
  const store = writingSessions({maxCharacters: 100});
  store.set('gap-业绩差距', {question: 'q'.repeat(60), action: 'draft'});
  store.set('gap-机会差距', {question: 'w'.repeat(60), action: 'draft'});
  assert.equal(store.get('gap-业绩差距'), undefined, 'oldest entry is dropped once the budget is exceeded');
  assert.equal(store.get('gap-机会差距').question.length, 60);

  const big = writingSessions({maxCharacters: 100});
  big.set('company-info-企业名称', {
    question: '', action: 'draft',
    result: {...at('company-info-企业名称'), draft: 'd'.repeat(80), original: 'o'.repeat(80)},
  });
  assert.equal(big.get('company-info-企业名称'), undefined, 'an oversized single result cannot exceed the bound');
});

test('session questions stay bounded and never include unrelated secrets', () => {
  const store = writingSessions();
  store.set('company-info-企业名称', {question: 'x'.repeat(20000), action: 'improve'});
  const entry = store.get('company-info-企业名称');
  assert.ok(entry.question.length <= 8000, `question bounded, got ${entry.question.length}`);
  assert.equal(entry.action, 'improve');
  assert.equal('key' in entry, false);
  assert.equal('endpoint' in entry, false);
});

test('clear is scoped to one step or the whole draft only', () => {
  const store = writingSessions();
  store.set('company-info-企业名称', {question: 'a', action: 'draft'});
  store.set('company-info-企业现状', {question: 'b', action: 'draft'});
  store.set('discussion:company-info', {question: 'c', action: 'draft'});
  store.set('gap-业绩差距', {question: 'd', action: 'draft'});
  store.set('discussion:gap', {question: 'e', action: 'draft'});
  store.clear('company-info');
  assert.equal(store.get('company-info-企业名称'), undefined);
  assert.equal(store.get('company-info-企业现状'), undefined);
  assert.equal(store.get('discussion:company-info'), undefined);
  assert.equal(store.get('gap-业绩差距').question, 'd', 'other steps are untouched');
  assert.equal(store.get('discussion:gap').question, 'e');
  store.clear();
  assert.equal(store.get('gap-业绩差距'), undefined);
  assert.equal(store.get('discussion:gap'), undefined);
});

test('stepCompletion counts real nonblank values, never business correctness', () => {
  const step = {id: 'demo', fields: [{name: 'a'}, {name: 'b'}, {name: 'c'}]};
  assert.deepEqual(stepCompletion(step, {}), {filled: 0, total: 3, label: '未开始'});
  assert.deepEqual(stepCompletion(step, {'demo-a': '   ', 'demo-b': '\n\t', 'demo-c': ''}), {filled: 0, total: 3, label: '未开始'});
  assert.deepEqual(stepCompletion(step, {'demo-a': '虚构内容', 'demo-b': '  ', 'demo-c': ''}), {filled: 1, total: 3, label: '填写中'});
  assert.deepEqual(stepCompletion(step, {'demo-a': 'x', 'demo-b': 'y', 'demo-c': 'z'}), {filled: 3, total: 3, label: '已填写'});
  // Table cells: only a row with at least one nonblank cell counts as content.
  const table = {id: 't', fields: [{name: 'rows'}]};
  assert.equal(stepCompletion(table, {'t-rows': [['', '  '], ['', '']]}).label, '未开始');
  assert.equal(stepCompletion(table, {'t-rows': [['', '  '], ['事实', '']]}).filled, 1);
  assert.equal(stepCompletion(table, {'t-rows': []}).label, '未开始');
});

test('hasContent is the single source of truth for blank strings and table rows', () => {
  assert.equal(hasContent(undefined), false);
  assert.equal(hasContent(''), false);
  assert.equal(hasContent(' \n '), false);
  assert.equal(hasContent('待核实'), true);
  assert.equal(hasContent([]), false);
  assert.equal(hasContent([['', ' ']]), false);
  assert.equal(hasContent([['', '虚构']]), true);
  assert.equal(hasContent([[]]), false);
});
