import {createSignals, mailDraft, EMAIL} from './signals.mjs';

export const PRODUCTS = Object.freeze({
  'ip-guard': {name: 'IP 守护', problem: '虚构团队正在设计一款模块化设备，希望先整理创新点与待核实的知识产权问题。', output: ['创新主题与检索范围（待确认）', '检索路径与证据记录模板', '风险问题与人工核验清单']},
  'deep-blm': {name: 'Deep BLM', problem: '虚构团队考虑进入一个新业务方向，需要梳理客户假设、能力差距与验证顺序。', output: ['基于 BLM 的战略议题图', '客户与价值主张假设清单', '能力差距与分阶段验证计划']},
  architecture: {name: '技术架构规划', problem: '虚构团队准备扩展一个业务系统，希望比较模块拆分、数据边界与演进顺序。', output: ['业务目标与系统约束表', '候选架构比较与取舍记录', '能力边界与演进路线草案']},
  'tech-ma': {name: 'Tech M&A', problem: '虚构团队讨论一项技术并购，希望先列清需要证据支持的能力、依赖与整合议题。', output: ['技术尽调问题与证据清单', '能力依赖与待核实风险模板', '整合议题与后续核验计划']}
});
const CATEGORIES = {product: '产品需求', a2a: 'A2A 意向', consulting: '咨询服务', integration: '工具集成', general: '通用需求', partnership: '伙伴合作'};
const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
let signals = createSignals(null);
const track = (event, service, category, surface, extra = {}) => signals.track({event, service: service || null, category, surface, ...extra});

export async function initAnalytics({transport} = {}) {
  const panels = $$('[data-analytics]');
  let decisionMade = false;
  try {
    const response = await fetch('analytics-config.json', {credentials: 'omit', cache: 'no-store'});
    if (response.ok) {
      const config = await response.json();
      const local = location.protocol !== 'https:' || !['www.deeparchi.com.cn', 'deeparchi.com.cn'].includes(location.hostname);
      const isTest = new URLSearchParams(location.search).get('internal_test') === '1';
      signals = createSignals(config, {navigatorLike: navigator, local, isTest, transport: isTest ? transport : undefined});
    } else signals = createSignals({});
  } catch { signals = createSignals({}); /* Fail closed without exposing URLs or errors. */ }
  const render = () => {
    panels.forEach(panel => {
      panel.querySelector('[data-analytics-status]').textContent = signals.status();
      panel.querySelector('[data-analytics-options]').hidden = !signals.available();
      if (panel.hasAttribute('data-analytics-banner')) panel.hidden = !signals.available() || decisionMade;
    });
    const feedback = $('[data-analytics-feedback]');
    if (feedback) feedback.textContent = decisionMade ? signals.status() : '';
  };
  panels.forEach(panel => panel.querySelectorAll('[data-consent]').forEach(button => { button.onclick = () => {
    const accept = button.dataset.consent === 'accept';
    signals.setConsent(accept);
    decisionMade = true;
    render();
    // Measure only cards visible NOW after opt-in, never replay pre-consent views.
    if (accept) $$('.product').forEach(card => {
      const rect = card.getBoundingClientRect();
      const visible = Math.max(0, Math.min(innerHeight, rect.bottom) - Math.max(0, rect.top));
      if (rect.height > 0 && visible >= rect.height * .5) track('product_view', card.id, 'product', 'cards');
    });
  }; }));
  // No cookie/localStorage or replay: consent and IDs last only for this page.
  render();
}

function initHome() {
  const menu = $('.menu-button');
  const nav = $('#nav-links');
  const closeMenu = () => { nav.classList.remove('open'); menu.setAttribute('aria-expanded', 'false'); menu.setAttribute('aria-label', '打开导航菜单'); };
  menu.addEventListener('click', () => {
    const open = nav.classList.toggle('open');
    menu.setAttribute('aria-expanded', String(open));
    menu.setAttribute('aria-label', open ? '关闭导航菜单' : '打开导航菜单');
  });
  nav.addEventListener('click', event => { if (event.target.closest('a')) closeMenu(); });
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && nav.classList.contains('open')) { closeMenu(); menu.focus(); } });

  const demo = $('#demo-dialog');
  const a2a = $('#a2a-dialog');
  const a2aTrigger = $('#open-a2a');
  const demand = $('#demand-dialog');
  const form = $('#demand-form');
  let demoTrigger;
  let demandTrigger;
  let activeSource;
  let draft;
  [demo, a2a, demand].forEach(dialog => {
    dialog.querySelector('[data-close]').addEventListener('click', () => dialog.close());
    dialog.addEventListener('keydown', event => {
      if (event.key !== 'Tab') return;
      const controls = [...dialog.querySelectorAll('a[href],button,input,select,textarea,[tabindex]')]
        .filter(element => !element.disabled && element.tabIndex >= 0 && element.getClientRects().length && getComputedStyle(element).visibility !== 'hidden');
      const first = controls[0];
      const last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault(); last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault(); first?.focus();
      }
    });
    dialog.addEventListener('click', event => {
      const rect = dialog.getBoundingClientRect();
      if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) dialog.close();
    });
  });
  demo.addEventListener('close', () => { if (!demand.open) demoTrigger?.focus(); });
  a2aTrigger.addEventListener('click', () => { stage = 0; renderStage(); a2a.showModal(); });
  a2a.addEventListener('close', () => { if (!demand.open) a2aTrigger.focus(); });
  demand.addEventListener('close', () => { form.reset(); clearDraft(); demandTrigger?.focus(); });
  function clearDraft() {
    draft = undefined;
    $('#draft').hidden = true;
    $('#draft-text').textContent = '';
    $('#draft-mailto').removeAttribute('href');
    $('#copy-status').textContent = '';
  }

  $$('[data-demo]').forEach(button => button.addEventListener('click', () => {
    const id = button.dataset.demo;
    const product = PRODUCTS[id];
    if (!product) return;
    if (button.matches('a[data-tool-entry]')) {
      // Native navigation; demo_open counts entry interest, never tool completion.
      track('demo_open', id, 'product', 'cards');
      return;
    }
    demoTrigger = button;
    $('#demo-title').textContent = product.name;
    $('#demo-problem').textContent = product.problem;
    $('#demo-output').replaceChildren(...product.output.map(text => { const li = document.createElement('li'); li.textContent = text; return li; }));
    $('#demo-intent').dataset.service = id;
    demo.showModal();
    track('demo_open', id, 'product', 'cards');

  }));

  $$('[data-intent]').forEach(button => button.addEventListener('click', () => {
    const category = button.dataset.intent;
    if (!CATEGORIES[category]) return;
    const service = category === 'a2a' && button.dataset.surface === 'a2a' ? $('#a2a-product').value : button.dataset.service || null;
    const product = PRODUCTS[service];
    const source = `${CATEGORIES[category]}${product ? ` / ${product.name}` : ''}`;
    demandTrigger = demo.open ? demoTrigger : a2a.open ? a2aTrigger : button;
    if (demo.open) demo.close();
    if (a2a.open) a2a.close();
    activeSource = {category, service, source};
    form.reset(); clearDraft();
    $('#demand-source').textContent = `来源：${source}`;
    demand.showModal();
    track('intent_open', service, category, button.dataset.surface);
    if (category === 'a2a' && product) track('a2a_interest', service, category, button.dataset.surface);
  }));
  form.addEventListener('input', () => {
    $('#problem').setCustomValidity('');
    clearDraft();
  });
  form.addEventListener('submit', event => {
    event.preventDefault();
    const problem = $('#problem');
    problem.setCustomValidity(problem.value.trim() ? '' : '请简要描述业务问题。');
    if (!form.reportValidity()) return;
    try {
      draft = mailDraft({source: activeSource.source, problem: problem.value, result: $('#result').value, constraints: $('#constraints').value});
      $('#draft-text').textContent = draft.text;
      $('#draft-mailto').href = draft.uri;
      $('#draft-mailto').textContent = draft.tooLong ? '打开邮件后粘贴草稿' : '打开邮件客户端确认';
      $('#draft-mailto').classList.toggle('primary', !draft.tooLong);
      $('#copy-draft').classList.toggle('button', draft.tooLong);
      $('#copy-draft').classList.toggle('primary', draft.tooLong);
      $('#draft').hidden = false;
      $('#copy-status').textContent = draft.tooLong ? '草稿较长，邮件链接可能被客户端截断。请优先复制完整草稿，再打开邮件粘贴；邮件链接不携带正文。' : '也可复制草稿，粘贴到你使用的邮箱。';
      track('mail_draft_ready', activeSource.service, activeSource.category, 'demand');
    } catch { problem.setCustomValidity('请检查文本长度并重新准备草稿。'); form.reportValidity(); }
  });
  $('#draft-mailto').addEventListener('click', () => track('mailto_click', activeSource.service, activeSource.category, 'demand'));
  async function copy(text, status, fallback) {
    try { await navigator.clipboard.writeText(text); status.textContent = '已复制。'; }
    catch { status.textContent = fallback; }
  }
  $('#copy-draft').addEventListener('click', () => { if (draft) copy(draft.text, $('#copy-status'), '无法自动复制，请选中上方草稿手动复制。'); });
  $('#copy-email').addEventListener('click', () => copy(EMAIL, $('#email-status'), `无法自动复制，请手动复制：${EMAIL}`));

  const stages = [
    ['发现服务', product => `样例服务目录：${product.name}。当前仅提供概念展示，未发现或连接运行中的 Agent。`],
    ['描述需求', product => product.problem],
    ['确认范围与授权', () => '样例检查项：输入范围、数据权限、人工复核与验收结构。此处不请求授权，也不创建任务。'],
    ['查看进度', () => '样例进度结构：待确认 → 待核验 → 待复核。仅解释可能的状态，不代表有工作正在执行。'],
    ['接收交付样例', () => '演示样例，非真实客户交付。以下 JSON 仅展示交付结构，所有内容均为虚构或待确认。']
  ];
  let stage = 0;
  function renderStage() {
    const service = $('#a2a-product').value;
    const product = PRODUCTS[service];
    $('#a2a-stage-label').textContent = `SAMPLE ${stage + 1} / 5 · ${product.name}`;
    $('#a2a-stage-title').textContent = stages[stage][0];
    $('#a2a-stage-copy').textContent = stages[stage][1](product);
    $$('.stages li').forEach((item, index) => { if (index === stage) item.setAttribute('aria-current', 'step'); else item.removeAttribute('aria-current'); });
    $('#a2a-artifact').hidden = stage !== 4;
    $('#a2a-artifact').textContent = stage === 4 ? JSON.stringify({kind: 'sample-deliverable', sample: true, label: '演示样例，非真实客户交付', service_id: service, service_name: product.name, scenario: product.problem, deliverable_structure: product.output, findings: null, requires_human_review: true, task_executed: false}, null, 2) : '';
    $('#a2a-next').hidden = stage === 4;
    $('#a2a-intent').hidden = stage !== 4;
  }
  $('#a2a-next').addEventListener('click', () => {
    if (stage < 4) stage++;
    renderStage();
    track('a2a_step', $('#a2a-product').value, 'a2a', 'a2a', {step: stage + 1});
    if (stage === 4) $('#a2a-intent').focus();
  });
  const reset = () => { stage = 0; renderStage(); track('a2a_step', $('#a2a-product').value, 'a2a', 'a2a', {step: 1}); };
  $('#a2a-reset').addEventListener('click', reset);
  $('#a2a-product').addEventListener('change', reset);
  renderStage();
  // Only count actual card visibility after consent; no historical interaction replay.
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) track('product_view', entry.target.id, 'product', 'cards');
    }), {threshold: .5});
    $$('.product').forEach(card => observer.observe(card));
  }
}

if (typeof document !== 'undefined') {
  document.documentElement.classList.add('js');
  $$('[data-js]').forEach(element => { element.hidden = false; });
  if ($('#demand-form')) initHome();
  initAnalytics();
}
