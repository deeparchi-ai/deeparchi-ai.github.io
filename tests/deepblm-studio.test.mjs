import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, statSync} from 'node:fs';
import {studioStage, studioArt, studioIntents, appendStudioIntent} from '../assets/deepblm-studio.mjs';

const target = (name = '主营业务', type = 'text') => ({step: {id: 'company-info'}, field: {name, type}});

test('all 15 steps have the correct fixed semantic art group, including each boundary', () => {
  const actual = Array.from({length: 15}, (_, i) => studioStage(i).art);
  assert.deepEqual(actual, ['insight', 'insight', 'strategy', 'strategy', 'strategy', 'strategy', 'execution', 'execution', 'execution', 'execution', 'execution', 'foundation', 'foundation', 'review', 'review']);
  assert.equal(new Set(actual).size, 5);
  for (let i = 0; i < 15; i++) {
    assert.equal(new URL(studioArt(i)).pathname.split('/').pop(), `${actual[i]}.webp`);
    assert.equal(Object.isFrozen(studioStage(i)), true);
  }
  for (const index of [-1, 15, 1.5, NaN, '0', undefined]) assert.throws(() => studioStage(index), RangeError);
});

test('five deployable art files are actual small WebP assets with local non-scripted SVG sources', () => {
  let total = 0;
  for (const name of ['insight', 'strategy', 'execution', 'foundation', 'review']) {
    const file = new URL(`../assets/deepblm-art/${name}.webp`, import.meta.url);
    const bytes = readFileSync(file);
    assert.equal(bytes.toString('ascii', 0, 4), 'RIFF');
    assert.equal(bytes.toString('ascii', 8, 12), 'WEBP');
    assert.ok(statSync(file).size < 140000);
    total += bytes.length;
    const svg = readFileSync(new URL(`../assets/deepblm-art/svg/${name}.svg`, import.meta.url), 'utf8');
    assert.match(svg, /<svg/);
    assert.doesNotMatch(svg, /<script|<foreignObject|onload\s*=|href\s*=\s*["']https?:/i);
  }
  assert.ok(total < 600000);
});

test('intent chips are tailored to user action and constrained company identity, never data output', () => {
  assert.equal(studioIntents(target(), 'draft')[0].id, 'outline');
  assert.equal(studioIntents(target(), 'improve')[0].id, 'concise');
  assert.equal(studioIntents(target(), 'inspect')[0].id, 'evidence');
  assert.equal(studioIntents(target('行动', 'table'), 'draft')[1].id, 'accountable');
  assert.deepEqual(studioIntents(target('企业名称'), 'draft').map(x => x.id), ['identity']);
  assert.match(studioIntents(target('企业名称'), 'draft')[0].text, /不生成虚构/);
  assert.deepEqual(studioIntents(null, 'draft').map(x => x.id), ['tradeoffs', 'connections']);
  assert.throws(() => studioIntents(target(), 'unknown'), RangeError);
  for (const action of ['draft', 'improve', 'inspect']) {
    const chips = studioIntents(target(), action);
    assert.equal(new Set(chips.map(x => x.id)).size, chips.length);
    assert.ok(chips.every(x => Object.isFrozen(x) && x.text.length > 0));
  }
});

test('append preserves existing text byte-for-byte, including whitespace and embedded markup', () => {
  const original = '  虚构人工要求：保留原意。\n<script>not executable</script>\n';
  const text = studioIntents(target(), 'improve')[0].text;
  assert.deepEqual(appendStudioIntent(original, text), {value: original + '\n' + text, reason: 'appended'});
  assert.deepEqual(appendStudioIntent('', text), {value: text, reason: 'appended'});
});

test('duplicate intent does not accumulate lines or mutate user text', () => {
  const text = studioIntents(target(), 'draft')[0].text;
  const original = 'keep\r\n ' + text + ' \r\nend';
  assert.deepEqual(appendStudioIntent(original, text), {value: original, reason: 'duplicate'});
});

test('8000-code-unit boundary is atomic; over-limit selection never truncates requirements', () => {
  assert.deepEqual(appendStudioIntent('x'.repeat(7998), 'a'), {value: 'x'.repeat(7998) + '\na', reason: 'appended'});
  assert.deepEqual(appendStudioIntent('x'.repeat(7999), 'a'), {value: 'x'.repeat(7999), reason: 'limit'});
  assert.deepEqual(appendStudioIntent('x'.repeat(8000), 'a'), {value: 'x'.repeat(8000), reason: 'limit'});
  assert.deepEqual(appendStudioIntent('原文', ' '), {value: '原文', reason: 'empty'});
});
