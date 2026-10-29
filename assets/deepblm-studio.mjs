// Presentation only. No storage, network, credentials, fabricated business data or model execution.
const stages = Object.freeze([
  {end: 2, art: 'insight', icon: 'lens', caption: '看清起点', accent: '#087c97'},
  {end: 6, art: 'strategy', icon: 'orbit', caption: '做出选择', accent: '#6651b2'},
  {end: 11, art: 'execution', icon: 'layers', caption: '让战略发生', accent: '#2167b6'},
  {end: 13, art: 'foundation', icon: 'foundation', caption: '以共同准则引领', accent: '#596ca0'},
  {end: 15, art: 'review', icon: 'check', caption: '在复核中前进', accent: '#33776b'},
].map(Object.freeze));
export function studioStage(index) {
  if (!Number.isInteger(index) || index < 0 || index >= 15) throw new RangeError('Unknown planning step');
  return stages.find(stage => index < stage.end);
}
export function studioArt(index) {
  return new URL(`./deepblm-art/${studioStage(index).art}.webp`, import.meta.url).href;
}
const intent = (id, label, text) => Object.freeze({id, label, text});
export function studioIntents(target, action) {
  if (!target) return [
    intent('tradeoffs', '梳理关键取舍', '梳理当前规划中的关键取舍，分别列出已知依据、假设与需要我确认的问题，不代替我作出决策。'),
    intent('connections', '连接前后步骤', '检查各步骤之间的承接关系，只提出值得人工核验的问题，不把缺失的资料当作事实。'),
  ];
  if (!['draft', 'improve', 'inspect'].includes(action)) throw new RangeError('Unknown writing action');
  if (action === 'inspect') return [
    intent('evidence', '核对证据', '重点核对每项判断的依据；明确区分事实、假设与待核实内容，指出需要补充的证据。'),
    intent('gaps', '找出承接缺口', '检查本字段与前后规划步骤的承接，列出缺口和待确认的问题，不补造数据。'),
  ];
  if (target.field.name === '企业名称') return [
    intent('identity', '核实正式名称', '仅使用已有资料中的企业正式名称；资料不足则标为待补充，不生成虚构企业名称。'),
  ];
  const result = action === 'draft' ? [
    intent('outline', '先搭起结构', '先给出清晰、精简、可继续补充的结构；缺失的事实和数字明确标为待补充，不编造结论。'),
  ] : [
    intent('concise', '更清晰精炼', '在保留已知事实、原意和不确定性的前提下精炼表达，使内容更清晰可执行，不新增未经证实的数据。'),
  ];
  result.push(target.field.type === 'table'
    ? intent('accountable', '明确行动与依据', '在既定表格列内明确行动、依据和需要确认的内容；不添加列，未知责任人、日期和数字均标为待核实。')
    : intent('grounded', '补齐验证思路', '为关键判断补充可执行的验证思路；区分已知依据与尚待验证的假设，不声称已经完成验证。'));
  return result;
}
// A chip prepares the next request; it must never overwrite text or initiate generation.
export function appendStudioIntent(current, text, limit = 8000) {
  const value = String(current ?? '');
  if (typeof text !== 'string' || !text.trim()) return {value, reason: 'empty'};
  if (value.split(/\r?\n/).some(line => line.trim() === text.trim())) return {value, reason: 'duplicate'};
  const next = `${value}${value ? '\n' : ''}${text}`;
  if (next.length > limit) return {value, reason: 'limit'};
  return {value: next, reason: 'appended'};
}
const paths = Object.freeze({
  sparkles: ['M12 3l2.4 6.6L21 12l-6.6 2.4L12 21l-2.4-6.6L3 12l6.6-2.4Z', 'M20 2v4M18 4h4'],
  lens: ['M10.5 3a7.5 7.5 0 1 0 0 15a7.5 7.5 0 0 0 0-15Z', 'm16 16 5 5M7 10.5h7M10.5 7v7'],
  orbit: ['M12 8a4 4 0 1 0 0 8a4 4 0 0 0 0-8Z', 'M3 12c0-4 18-4 18 0s-18 4-18 0Z', 'M12 3c4 0 4 18 0 18s-4-18 0-18Z'],
  layers: ['m3 8 9-5 9 5-9 5Z', 'm3 12 9 5 9-5M3 16l9 5 9-5'],
  foundation: ['M5 9v11M19 9v11M3 20h18M3 8l9-5 9 5Z', 'M10 12v8M14 12v8'],
  check: ['M5 3h10l4 4v14H5Z', 'M14 3v5h5M8 14l3 3 5-6'],
  arrow: ['M4 12h15m-6-6 6 6-6 6'],
});
export function studioIcon(name = 'sparkles') {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  for (const [key, value] of Object.entries({viewBox: '0 0 24 24', width: '20', height: '20', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true', focusable: 'false', class: 'studio-icon'})) svg.setAttribute(key, value);
  for (const d of paths[name] || paths.sparkles) {
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path'); path.setAttribute('d', d); svg.append(path);
  }
  return svg;
}
