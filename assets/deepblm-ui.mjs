// Presentation helpers only; draft schema and storage remain in the existing modules.
export const groups = [
  {name: '现状与差距', start: 0, end: 2},
  {name: '战略选择', start: 2, end: 6},
  {name: '战略执行', start: 6, end: 11},
  {name: '领导力与价值观', start: 11, end: 13, note: '贯穿战略与执行'},
  {name: '检查与修订', start: 13, end: 15},
];
export const groupFor = index => groups.find(g => index >= g.start && index < g.end).name;
export const hasContent = value => Array.isArray(value) ? value.some(row => row.some(cell => cell.trim())) : typeof value === 'string' && !!value.trim();
export const missingFields = (steps, data) => steps.slice(0, 13).flatMap((step, index) => step.fields.filter(field => !hasContent(data[`${step.id}-${field.name}`])).map(field => ({id: `${step.id}-${field.name}`, step, field, index})));
export const simpleField = (step, field) => step.id === 'company-info' && field.name !== '企业现状';
export const purposes = [
  '先说明你在经营什么，为后续分析提供共同起点。', '对照现状与目标，找出业绩和机会上的差距。',
  '梳理客户、竞争与市场变化，记录机会及依据。', '明确希望到达的位置，以及近期要实现的目标。',
  '选择值得探索的创新方向，安排试验与资源。', '明确服务谁、提供什么价值，以及如何持续获利。',
  '把业务选择转为具体行动，明确负责人和依赖。', '理解客户需求，规划体验与长期价值。',
  '让组织能力与文化支持关键任务。', '梳理支撑业务的架构与能力建设。', '估算投入与回报，明确资金安排。',
  '明确领导者贯穿战略制定与执行的行动与能力。', '把共同的价值准则贯穿于战略选择和日常行动。',
  '检查填写完整性，再人工核验各步骤的承接关系。', '记录修改建议，返回相应字段补充并复核。',
];
// Disclosure menus retain native Tab behavior and add arrow, Home/End and Escape support.
let menusWired = false;
export function wireMenu(details) {
  if (!menusWired) {
    menusWired = true;
    document.addEventListener('click', event => {
      for (const menu of document.querySelectorAll('.disclosure-menu[open]')) if (!menu.contains(event.target)) menu.open = false;
    });
  }
  const summary = details.querySelector('summary');
  const items = () => [...details.querySelectorAll('button:not(:disabled), a[href]')];
  details.addEventListener('keydown', event => {
    const list = items(), index = list.indexOf(document.activeElement);
    if (event.key === 'Escape') { details.open = false; summary.focus(); event.preventDefault(); }
    if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
      event.preventDefault(); details.open = true;
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? list.length - 1 : index < 0 ? (event.key === 'ArrowDown' ? 0 : list.length - 1) : (index + (event.key === 'ArrowDown' ? 1 : -1) + list.length) % list.length;
      list[next]?.focus();
    }
  });
  details.addEventListener('click', event => { if (event.target.closest('button, a')) details.open = false; });
  // Focus is temporarily on body during native Tab traversal; use the destination.
  details.addEventListener('focusout', event => { if (!details.contains(event.relatedTarget)) details.open = false; });
}
