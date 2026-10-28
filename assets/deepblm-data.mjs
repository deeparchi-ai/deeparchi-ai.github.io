import {steps} from './deepblm-schema.mjs';
export {steps};
export const LIMITS = Object.freeze({bytes: 4 * 1024 * 1024, text: 100000, cell: 8000, rows: 200, depth: 9, nodes: 60000});
export const DRAFT_KEY = 'deepblm-draft-v1';
export const STEP_KEY = 'deepblm-step-v1';
export const CONFIG_KEY = 'deepblm-preferences-v1';
export const TOOL_KEYS = [DRAFT_KEY, STEP_KEY, CONFIG_KEY, 'blm-strategy-data', 'blm-strategy-step', 'blm-validation-report', 'blm-ai-config', 'blm-ai-tasks', 'blm-welcome-dismissed', 'blm-ai-agent-position'];
const fields = new Map(steps.flatMap(s => s.fields.map(f => [`${s.id}-${f.name}`, f])));
const completion = ['strategy-validation-completed', 'revision-completed'];
const own = (o, k) => Object.hasOwn(o, k);
const bad = () => { throw new Error('文件格式或内容超出支持范围，原草稿未更改。'); };
const record = o => o !== null && typeof o === 'object' && !Array.isArray(o) && [Object.prototype, null].includes(Object.getPrototypeOf(o));
function keys(o, allowed) { if (!record(o) || Object.keys(o).some(k => !allowed.includes(k))) bad(); }
function str(v, max = LIMITS.text) { if (typeof v !== 'string' || v.length > max) bad(); return v; }
function inspect(v, depth = 0, count = {n: 0}) {
  if (depth > LIMITS.depth || ++count.n > LIMITS.nodes) bad();
  if (v && typeof v === 'object') {
    if (!Array.isArray(v) && !record(v)) bad();
    for (const k of Object.keys(v)) {
      if (['__proto__', 'prototype', 'constructor'].includes(k)) bad();
      inspect(v[k], depth + 1, count);
    }
  } else if (!['string', 'number', 'boolean'].includes(typeof v) && v !== null) bad();
}
export function parseBoundedJSON(text) {
  if (typeof text !== 'string' || new TextEncoder().encode(text).length > LIMITS.bytes) bad();
  let value;
  try { value = JSON.parse(text); } catch { bad(); }
  inspect(value);
  return value;
}
function fieldValue(f, value) {
  if (f.type !== 'table') return str(value, f.maxlength ?? LIMITS.text); // Preserve declared short-field limits.
  if (value === '') return []; // Legacy structured exports use '' for untouched tables.
  if (!Array.isArray(value) || value.length > LIMITS.rows) bad();
  return value.map(row => {
    if (!Array.isArray(row) || row.length !== f.columns.length) bad();
    return row.map(cell => str(cell, LIMITS.cell));
  });
}
function flag(value) { if (![true, false, 'true', 'false'].includes(value)) bad(); return value; }
function flat(value) {
  keys(value, [...fields.keys(), ...completion]);
  const output = {};
  for (const [key, v] of Object.entries(value)) output[key] = fields.has(key) ? fieldValue(fields.get(key), v) : flag(v);
  return output;
}
// The legacy report has a typed snapshot of all fields; retain it without accepting arbitrary objects.
export function normalizeReport(value) {
  keys(value, ['content', 'savedAt', 'stepData']);
  const out = {content: str(value.content)};
  if (own(value, 'savedAt')) {
    if (!Number.isSafeInteger(value.savedAt) || value.savedAt < 0) bad();
    out.savedAt = value.savedAt;
  }
  if (own(value, 'stepData')) {
    keys(value.stepData, steps.map(s => s.id));
    out.stepData = {};
    for (const [id, info] of Object.entries(value.stepData)) {
      const step = steps.find(s => s.id === id);
      keys(info, ['title', 'description', 'fields']);
      keys(info.fields, step.fields.map(f => f.name));
      const copy = {fields: {}};
      for (const k of ['title', 'description']) if (own(info, k)) copy[k] = str(info[k]);
      for (const [name, item] of Object.entries(info.fields)) {
        const f = step.fields.find(f => f.name === name);
        keys(item, f.type === 'table' ? ['type', 'columns', 'data'] : ['type', 'value']);
        if (item.type !== f.type) bad();
        if (f.type === 'table') {
          if (JSON.stringify(item.columns) !== JSON.stringify(f.columns)) bad();
          copy.fields[name] = {type: 'table', columns: [...f.columns], data: fieldValue(f, item.data)};
        } else copy.fields[name] = {type: f.type, value: fieldValue(f, item.value)};
      }
      out.stepData[id] = copy;
    }
  }
  return out;
}
export function normalizeImport(input) {
  const value = typeof input === 'string' ? parseBoundedJSON(input) : parseBoundedJSON(JSON.stringify(input));
  if (!record(value)) bad();
  if (!own(value, 'steps')) return {formData: flat(value), metadata: {}};
  keys(value, ['title', 'created', 'steps', 'metadata']);
  if (own(value, 'title')) str(value.title);
  if (own(value, 'created')) str(value.created, 100);
  if (!Array.isArray(value.steps) || value.steps.length > steps.length) bad();
  const formData = {}, seen = new Set();
  for (const item of value.steps) {
    keys(item, ['id', 'title', 'data']);
    const step = steps.find(s => s.id === item.id);
    if (!step || seen.has(step.id)) bad();
    seen.add(step.id);
    if (own(item, 'title')) str(item.title);
    keys(item.data, step.fields.map(f => f.name));
    for (const [name, v] of Object.entries(item.data)) formData[`${step.id}-${name}`] = fieldValue(step.fields.find(f => f.name === name), v);
  }
  const metadata = {};
  // Preserve the structured document header as internal metadata; serialize it back at top level.
  if (own(value, 'title') || own(value, 'created')) {
    metadata.header = {};
    if (own(value, 'title')) metadata.header.title = value.title;
    if (own(value, 'created')) metadata.header.created = value.created;
  }
  if (own(value, 'metadata')) {
    keys(value.metadata, ['version', 'completion', 'validationReport']);
    if (value.metadata.version !== 1) bad();
    metadata.version = 1;
    if (own(value.metadata, 'completion')) {
      keys(value.metadata.completion, completion);
      for (const [k, v] of Object.entries(value.metadata.completion)) formData[k] = flag(v);
    }
    if (own(value.metadata, 'validationReport')) metadata.validationReport = normalizeReport(value.metadata.validationReport);
  }
  return {formData, metadata};
}
export function structuredExport(formData, metadata = {}, created) {
  const checked = flat(formData);
  const out = {title: metadata.header?.title ?? 'BLM扩展框架战略规划', created: created ?? metadata.header?.created ?? new Date().toISOString(), steps: steps.map(s => ({id: s.id, title: s.title, data: Object.fromEntries(s.fields.map(f => [`${f.name}`, checked[`${s.id}-${f.name}`] ?? (f.type === 'table' ? [] : '')]))})), metadata: {version: 1, completion: {}}};
  for (const key of completion) if (own(checked, key)) out.metadata.completion[key] = checked[key];
  if (metadata.validationReport) out.metadata.validationReport = normalizeReport(metadata.validationReport);
  normalizeImport(out); // Enforce aggregate limits before saving or exporting.
  return out;
}
export function validateEndpoint(raw) {
  let u;
  try { u = new URL(raw); } catch { throw new Error('请输入完整的 HTTPS API 地址。'); }
  const h = u.hostname.toLowerCase().replace(/\.$/, '');
  // Reject literal addresses, private/local names and URL credentials. DNS must be managed by the endpoint owner.
  if (u.protocol !== 'https:' || u.username || u.password || u.hash || u.search || u.port && u.port !== '443' || !h.includes('.') || h.includes(':') || /^[\d.]+$/.test(h) || /(?:^|\.)(?:localhost|local|localdomain|internal|intranet|corp|lan|home|test|invalid|example)$/.test(h) || /(?:^|\.)(?:home\.arpa|nip\.io|sslip\.io|localtest\.me|lvh\.me|localhost\.direct)$/.test(h)) throw new Error('API 地址须为公共 HTTPS 域名，不能包含凭据、查询参数或本地地址。');
  return u.href.replace(/\/$/, '');
}
export const PROVIDERS = Object.freeze({deepseek: {endpoint: 'https://api.deepseek.com/chat/completions', model: 'deepseek-chat'}, openai: {endpoint: 'https://api.openai.com/v1/chat/completions', model: ''}, custom: {endpoint: '', model: ''}});
export function normalizeConfig(input) {
  const v = typeof input === 'string' ? parseBoundedJSON(input) : input;
  keys(v, ['provider', 'endpoint', 'model']);
  if (!own(PROVIDERS, v.provider)) bad();
  const endpoint = str(v.endpoint, 500);
  if (endpoint) validateEndpoint(endpoint);
  return {provider: v.provider, endpoint, model: str(v.model, 100)};
}
