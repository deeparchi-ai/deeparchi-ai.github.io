import {steps, LIMITS, DRAFT_KEY, STEP_KEY, CONFIG_KEY, TOOL_KEYS, PROVIDERS, normalizeImport, structuredExport, normalizeReport, parseBoundedJSON, validateEndpoint} from './deepblm-data.mjs';
import {REMEMBERED_KEY, canonicalConfig, validKey, matchesDestination, rememberedRecord, restoreRemembered} from './deepblm-credentials.mjs';
import {groups, groupFor, hasContent, missingFields, simpleField, purposes, wireMenu, writingActions, defaultWritingAction, defaultAITarget, canApplyWriting, writingPlaceholder, writingMessages} from './deepblm-ui.mjs';
import {escapeHTML, renderMarkdown, sanitizeRichHTML} from './deepblm-security.mjs';
const $ = selector => document.querySelector(selector);
const clone = value => JSON.parse(JSON.stringify(value));
function el(tag, attrs = {}, text) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  if (text !== undefined) node.textContent = text;
  return node;
}
function button(text, action, attrs = {}) {
  const node = el('button', {type: 'button', ...attrs}, text);
  node.addEventListener('click', action);
  return node;
}
function asset(path, kind) {
  return new Promise((resolve, reject) => {
    const node = el(kind === 'script' ? 'script' : 'link', kind === 'script' ? {src: new URL(path, import.meta.url).href} : {rel: 'stylesheet', href: new URL(path, import.meta.url).href});
    node.onload = resolve; node.onerror = reject; document.head.append(node);
  });
}
let started = false;
export async function startWorkspace() {
  if (started || !matchMedia('(min-width: 1024px)').matches) return;
  started = true;
  await Promise.all([
    asset('./vendor/easymde/easymde.min.js', 'script'),
    asset('./vendor/dompurify/purify.min.js', 'script'),
    asset('./vendor/easymde/easymde.min.css', 'style'),
  ]);
  if (!matchMedia('(min-width: 1024px)').matches) return;
  buildWorkspace();
}
function buildWorkspace() {
  let formData = {}, metadata = {}, currentStep = 0, editors = [];
  let storageBlocked = false, configBlocked = false, undo = [], redo = [], lastEdit = {}, pending = false, aiEpoch = 0;
  let config = {provider: 'deepseek', ...PROVIDERS.deepseek};
  let credential = null, remembered = false, configDirty = false;
  const recovery = new Map();
  const host = $('#workspace');
  host.className = 'workbench';
  const topbar = el('header', {class: 'workspace-topbar'});
  const brand = el('a', {class: 'workspace-brand', href: '../index.html', 'aria-label': 'DeepArchi 首页'});
  const brandIcon = el('span', {class: 'workspace-brand-icon', 'aria-hidden': 'true'});
  brandIcon.append(el('img', {src: '../assets/deeparchi-logo.png', width: '64', height: '66', alt: ''}));
  brand.append(brandIcon, el('strong', {}, 'DeepArchi'));
  const product = el('div', {class: 'workspace-product'});
  product.append(el('strong', {}, 'Deep BLM'), el('span', {}, '规划工具 · 试用'));
  const status = el('p', {id: 'save-status', class: 'status', role: 'status', 'aria-live': 'polite'});
  const message = el('p', {id: 'tool-message', class: 'status', role: 'status', 'aria-live': 'polite'});
  topbar.append(brand, product, status); host.append(topbar);
  function menu(title, id) {
    const node = el('details', {class: 'disclosure-menu', id});
    node.append(el('summary', {}, title), el('div', {class: 'menu-items'})); wireMenu(node); return node;
  }
  const recoveryBox = el('div', {id: 'storage-recovery', class: 'notice warning', hidden: ''});
  recoveryBox.append(el('p', {}, '本工具发现无法读取的本地数据，已保留原件并暂停自动保存。可导出恢复副本，检查文件后重新导入，或确认清除本工具数据。'));
  recoveryBox.append(button('导出恢复副本', () => {
    if (!recovery.size) { say('浏览器存储不可用；可用下方 JSON 导出保留当前内存草稿。'); return; }
    download('deepblm-recovery.json', JSON.stringify(Object.fromEntries(recovery), null, 2), 'application/json');
  }, {id: 'export-recovery'}));
  const undoBtn = button('撤销', () => historyMove(undo, redo), {id: 'undo'});
  const redoBtn = button('重做', () => historyMove(redo, undo), {id: 'redo'});
  const importInput = el('input', {type: 'file', accept: '.json,application/json', hidden: '', id: 'import-file', 'aria-label': '导入规划 JSON'});
  const importMenu = menu('导入', 'import-menu');
  importMenu.lastElementChild.append(button('导入 JSON', () => importInput.click(), {id: 'import-json'}), importInput);
  const exportMenu = menu('导出', 'export-menu');
  exportMenu.lastElementChild.append(button('导出 JSON', () => exportFile('json'), {id: 'export-json'}), button('导出 Markdown', () => exportFile('md'), {id: 'export-markdown'}), button('Word 兼容 .doc', () => exportFile('doc'), {id: 'export-word'}));
  const settingsMenu = menu('设置', 'settings-menu');
  settingsMenu.lastElementChild.append(button('保存到本机', () => save(), {id: 'save-draft'}), button('清除本工具本地数据', clearLocal, {id: 'clear-local'}));
  const help = el('details', {id: 'tool-help'});
  help.append(el('summary', {}, '使用与数据说明'), el('p', {}, '手工编辑始终可用。草稿只保存在当前浏览器，没有账号或云端同步。请定期导出 JSON 备份。JSON 兼容旧版扁平和分步结构；字段支持文本/Markdown 文件导入。Word 兼容 .doc 是 HTML，不是 .docx。不支持 .docx 导入。公共链接导入、代理抓取与自动搜索已关闭。'));
  settingsMenu.lastElementChild.append(button('使用与数据说明', () => { help.open = !help.open; if (help.open) help.querySelector('summary').focus(); }));
  help.addEventListener('keydown', event => { if (event.key === 'Escape') { help.open = false; settingsMenu.querySelector('summary').focus(); } });
  const globalAIButton = button('AI 设置 · 未配置', openGlobalAI, {id: 'open-ai-settings', 'aria-haspopup': 'dialog'});
  topbar.append(globalAIButton, importMenu, exportMenu, settingsMenu);
  host.append(message, recoveryBox, help);
  const grid = el('div', {class: 'workspace-grid'}), sidebar = el('aside', {class: 'step-sidebar', 'aria-label': '规划进度'});
  const projectName = el('strong', {id: 'planning-name'}, '未命名规划');
  const planning = el('div', {class: 'current-planning'});
  planning.append(el('span', {}, '当前规划'), projectName);
  const progressLabel = el('p', {id: 'progress-label', class: 'small'}), progress = el('progress', {id: 'planning-progress', max: '15', value: '0', 'aria-label': '有内容的步骤数'});
  const nav = el('nav', {'aria-label': '15 步规划导航', id: 'step-nav'}), stepButtons = [];
  for (const group of groups) {
    const section = el('section', {class: group.note ? 'nav-group nav-foundation' : 'nav-group'}); section.append(el('h2', {}, group.name));
    if (group.note) section.append(el('p', {class: 'nav-group-note'}, group.note));
    steps.slice(group.start, group.end).forEach((step, offset) => {
      const i = group.start + offset;
      const b = button(`${i + 1}. ${step.title}`, () => goToStep(i), {'data-step': step.id});
      section.append(b); stepButtons.push(b);
    }); nav.append(section);
  }
  sidebar.append(planning, nav, progressLabel, progress, el('p', {class: 'local-note'}, '仅存于此浏览器'));
  const body = el('section', {class: 'step-body', id: 'step-content', 'aria-label': '当前规划步骤'});
  const center = el('div', {class: 'workspace-center'}), pager = el('footer', {class: 'step-pager'});
  const hints = el('aside', {class: 'context-sidebar', 'aria-label': '填写帮助'});
  center.append(body, pager); grid.append(sidebar, center, hints); host.append(grid);
  let returnPoint = null, reportEntries = [];
  const aiDetails = el('dialog', {id: 'ai-panel', 'aria-modal': 'true', 'aria-labelledby': 'ai-heading'});
  const aiHeader = el('header', {class: 'ai-header'});
  const aiHeading = el('div');
  aiHeading.append(el('p', {class: 'ai-eyebrow'}, '写作助手'), el('h2', {id: 'ai-heading', tabindex: '-1'}, '把想法写进规划'));
  aiHeader.append(aiHeading, button('关闭', closeAI, {id: 'close-ai', 'aria-label': '关闭 AI 辅助'}));
  aiDetails.append(aiHeader);
  const aiScroll = el('div', {class: 'ai-scroll'});
  const aiSetup = el('div', {class: 'ai-setup'});
  const aiDisclosure = el('p', {id: 'ai-disclosure'}, '主动发送后，当前规划全文、已有校验报告和你的问题（包含全部 15 步）会交给所选服务方处理，费用由你的账户承担。请确认发送范围，不要发送敏感资料；建议需自行核验。取消只停止本页等待，已发送内容无法撤回，服务方可能继续处理或计费。此处统一确认后，全部步骤共用；重新打开页面或修改连接设置后需重新确认。');
  const sharedStatus = el('p', {id: 'ai-config-status', class: 'small'});
  const destination = el('p', {id: 'ai-destination', class: 'small'});
  const configureAIButton = button('去全局设置', openGlobalAI, {id: 'ai-open-settings', 'aria-haspopup': 'dialog'});
  aiSetup.append(sharedStatus, configureAIButton);
  const aiSettings = el('dialog', {id: 'ai-settings', 'aria-modal': 'true', 'aria-labelledby': 'ai-settings-heading', 'aria-describedby': 'ai-disclosure ai-storage-disclosure'});
  aiSettings.append(button('关闭全局设置', closeGlobalAI, {id: 'close-ai-settings'}), el('h2', {id: 'ai-settings-heading', tabindex: '-1'}, '全局 AI 设置'));
  aiSettings.append(el('p', {}, 'DeepBLM 工作台全部 15 步共用一份设置；导入或重置规划不影响它。仅支持 OpenAI 兼容 Chat Completions，请核对模型 ID、费用、权限与浏览器 CORS。保存设置不测试连接。'));
  const aiGrid = el('div', {class: 'ai-grid'});
  function aiField(name, node) { const l = el('label'); l.append(el('span', {}, name), node); aiGrid.append(l); return node; }
  const provider = aiField('提供方', el('select', {id: 'ai-provider'}));
  for (const [id, name] of [['deepseek', 'DeepSeek（需自行核对）'], ['openai', 'OpenAI（填写可用模型 ID）'], ['custom', '自定义 OpenAI 兼容接口']]) provider.append(el('option', {value: id}, name));
  const endpoint = aiField('完整 HTTPS Chat Completions 地址', el('input', {type: 'url', id: 'ai-endpoint', maxlength: '500', autocomplete: 'off', spellcheck: 'false'}));
  const model = aiField('模型 ID', el('input', {id: 'ai-model', maxlength: '100', autocomplete: 'off'}));
  const key = aiField('API Key', el('input', {type: 'password', id: 'ai-key', autocomplete: 'off', spellcheck: 'false', maxlength: '4096'}));
  const remember = el('input', {type: 'checkbox', id: 'ai-remember-key'});
  const rememberLabel = el('label', {class: 'ai-checkbox'});
  rememberLabel.append(remember, document.createTextNode('在此浏览器记住 Key（仅个人设备）'));
  const rememberedStatus = el('p', {id: 'ai-remember-status', role: 'status'});
  aiSettings.append(aiGrid, rememberLabel, el('p', {id: 'ai-storage-disclosure'}, '默认仅保存在当前页面内存。勾选并保存后，Key 以明文写入此浏览器同源 localStorage，同源脚本、XSS 或本机用户可读取；这不是安全密钥库，不要在共享设备使用。仅限同一浏览器与来源，无账号、云端或跨设备同步。刷新或重新打开仍须重新同意外部处理；只有主动发送才直接交给选定提供方，不上传到本站服务器，不进入草稿或导出。'), rememberedStatus);
  const consentLabel = el('label');
  const consent = el('input', {type: 'checkbox', id: 'ai-consent'});
  consentLabel.append(consent, document.createTextNode('我同意向所选服务方发送规划上下文并承担费用。'));
  aiSettings.append(aiDisclosure, destination, consentLabel);
  const aiBar = el('div', {class: 'toolbar'});
  const settingsBar = el('div', {class: 'toolbar'});
  settingsBar.append(button('保存全局设置', saveAISettings, {id: 'save-ai-preferences', class: 'primary'}), button('忘记 Key', forgetKey, {id: 'forget-key'}));
  const legacyNotice = el('div', {id: 'legacy-settings', class: 'notice', hidden: ''});
  legacyNotice.append(el('p', {}, '检测到旧版 blm-ai-config 设置。新版不会读取其中的 Key，也不会自动使用或迁移。你可以显式删除旧设置。'), button('清除旧版 AI 设置', () => {
    if (!confirm('确认只删除 blm-ai-config 旧版 AI 设置？')) return;
    try { localStorage.removeItem('blm-ai-config'); legacyNotice.hidden = true; say('旧版 AI 设置已删除。'); } catch { say('浏览器不允许删除本地设置。'); }
  }, {id: 'clear-legacy-settings'}));
  const targetBlock = el('section', {class: 'ai-target-block', 'aria-label': '写作目标'});
  const targetLabel = el('p', {id: 'ai-target'});
  const targetSelectLabel = el('label', {for: 'ai-target-select'}, '当前步骤 · 写作目标');
  const targetSelect = el('select', {id: 'ai-target-select'});
  const aiSnapshot = el('details', {id: 'ai-snapshot'});
  const snapshotTitle = el('summary');
  const snapshotContent = el('div', {id: 'ai-snapshot-content', class: 'ai-snapshot-content', tabindex: '0', role: 'region', 'aria-label': '已有内容，只读'});
  aiSnapshot.append(snapshotTitle, snapshotContent);
  aiBar.append(button('规划讨论', () => chooseAITarget(null), {id: 'ai-discussion', 'aria-pressed': 'false'}));
  targetBlock.append(targetSelectLabel, targetSelect, aiBar, targetLabel, aiSnapshot);
  targetSelect.addEventListener('change', () => {
    const step = steps[currentStep], field = step.fields.find(f => `${step.id}-${f.name}` === targetSelect.value);
    chooseAITarget(field ? {step, field, id: targetSelect.value} : null);
  });
  const composer = el('section', {class: 'ai-composer', 'aria-label': '写作要求'});
  const actionBar = el('div', {class: 'ai-shortcuts', role: 'group', 'aria-label': '写作动作'});
  const actionButtons = writingActions.map(action => button(action.label, () => {
    if (aiAction === action.id) return;
    resetAIResult(); aiAction = action.id; rememberComposer(); updateComposer();
  }, {'data-ai-action': action.id, 'aria-pressed': 'false'}));
  actionBar.append(...actionButtons);
  const questionLabel = el('label', {for: 'ai-question'}, '补充要求（可选）');
  const question = el('textarea', {id: 'ai-question', maxlength: '8000', rows: '3'});
  question.addEventListener('input', rememberComposer);
  let composing = false;
  question.addEventListener('compositionstart', () => { composing = true; });
  question.addEventListener('compositionend', () => { composing = false; });
  question.addEventListener('keydown', event => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey) && !event.isComposing && !composing && event.keyCode !== 229) {
      event.preventDefault(); runAI();
    }
  });
  const aiSend = button('生成建议', () => runAI(), {id: 'ai-send', class: 'primary'});
  const aiCancel = button('取消生成', () => {
    resetAIResult('已停止等待；已发送内容无法撤回，草稿未更改。');
  }, {id: 'ai-cancel', disabled: '', hidden: ''});
  const aiResult = el('div', {id: 'ai-result', class: 'rich-content ai-result', 'aria-live': 'polite'});
  const aiMessage = el('p', {id: 'ai-message', role: 'status', 'aria-live': 'polite'});
  const aiApply = button('采用到目标字段', () => applyAI(), {id: 'ai-apply', hidden: ''});
  const resultCard = el('section', {class: 'ai-result-card', 'aria-labelledby': 'ai-result-heading', 'data-state': 'empty'});
  resultCard.append(el('h3', {id: 'ai-result-heading'}, '建议预览'), aiResult, aiApply);
  const sendBar = el('div', {class: 'ai-sendbar'});
  sendBar.append(el('span', {class: 'ai-keyboard-hint'}, 'Ctrl / ⌘ + Enter 生成 · Enter 换行'), aiSend, aiCancel);
  composer.append(actionBar, questionLabel, question, sendBar, aiMessage);
  const settingsMessage = el('p', {id: 'ai-settings-message', role: 'status', 'aria-live': 'polite'});
  aiSettings.append(settingsBar, legacyNotice, settingsMessage);
  aiScroll.append(aiSetup, targetBlock, composer, resultCard); aiDetails.append(aiScroll);
  host.append(aiDetails, aiSettings);
  let controller = null, aiAnswer = '', aiTarget = null, aiAction = 'draft', aiMemoryKey = null;
  const composerMemory = new Map();
  let aiOpener = null, settingsOpener = null, returnToAI = false;
  function openAI() {
    aiOpener = document.activeElement;
    aiMessage.textContent = '';
    if (!aiDetails.open) aiDetails.showModal();
    aiScroll.scrollTop = 0;
    (configureAIButton.hidden ? question : configureAIButton).focus();
  }
  function closeAI() { if (pending) aiCancel.click(); aiDetails.close(); }
  function openGlobalAI() {
    returnToAI = aiDetails.open;
    settingsOpener = document.activeElement;
    if (returnToAI) closeAI();
    aiSettings.showModal(); aiSettings.scrollTop = 0; $('#ai-settings-heading').focus();
  }
  function closeGlobalAI() {
    aiSettings.close();
    if (returnToAI && matchMedia('(min-width: 1024px)').matches) {
      aiDetails.showModal(); (configureAIButton.hidden ? question : configureAIButton).focus();
    } else if (matchMedia('(min-width: 1024px)').matches) {
      let focus = settingsOpener?.isConnected ? settingsOpener : globalAIButton;
      const disclosure = focus?.closest('.disclosure-menu');
      if (disclosure && !disclosure.open) focus = disclosure.querySelector('summary');
      focus?.focus({preventScroll: true});
    }
    returnToAI = false;
  }
  aiDetails.addEventListener('cancel', event => { event.preventDefault(); closeAI(); });
  aiSettings.addEventListener('cancel', event => { event.preventDefault(); closeGlobalAI(); });
  for (const dialog of [aiDetails, aiSettings]) dialog.addEventListener('keydown', event => {
    if (event.key !== 'Tab') return;
    const controls = [...dialog.querySelectorAll('button, a[href], input, select, textarea, summary, [tabindex]')]
      .filter(node => node.tabIndex >= 0 && !node.disabled && node.getClientRects().length);
    const first = controls[0], last = controls.at(-1);
    if (!first) { event.preventDefault(); return; }
    if (event.shiftKey && (document.activeElement === first || !controls.includes(document.activeElement))) {
      event.preventDefault(); last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault(); first.focus();
    }
  });
  aiDetails.addEventListener('close', () => {
    if (aiSettings.open || aiDetails.open) return;
    if (pending) aiCancel.click();
    let focus = aiOpener?.isConnected ? aiOpener : $('#step-heading');
    const disclosure = focus?.closest('.disclosure-menu');
    if (disclosure && !disclosure.open) focus = disclosure.querySelector('summary');
    if (matchMedia('(min-width: 1024px)').matches) focus?.focus({preventScroll: true});
  });
  matchMedia('(min-width: 1024px)').addEventListener('change', event => {
    if (!event.matches) { if (aiSettings.open) closeGlobalAI(); if (aiDetails.open) closeAI(); }
  });
  function say(text) { message.textContent = text; if (aiDetails.open) aiMessage.textContent = text; if (aiSettings.open) settingsMessage.textContent = text; }

  function rememberComposer() { if (aiMemoryKey) composerMemory.set(aiMemoryKey, {question: question.value, action: aiAction}); }
  function clearComposer(step = null) {
    if (step) {
      for (const id of composerMemory.keys()) if (id.startsWith(`${step.id}-`) || id === `discussion:${step.id}`) composerMemory.delete(id);
    } else composerMemory.clear();
    aiMemoryKey = null; aiTarget = null; aiAction = 'draft'; question.value = '';
    resetAIResult();
  }
  function updatePending() {
    aiSend.disabled = pending; aiSend.textContent = pending ? '生成中…' : aiTarget ? '生成建议' : '开始讨论';
    aiCancel.hidden = !pending; aiCancel.disabled = !pending;
    aiResult.setAttribute('aria-busy', String(pending));
  }
  function resetAIResult(text = '生成后在这里预览，核验后再决定是否采用。') {
    aiEpoch++; controller?.abort(); pending = false; aiAnswer = ''; aiApply.hidden = true;
    resultCard.dataset.state = 'empty'; aiResult.textContent = text; aiMessage.textContent = ''; updatePending();
  }
  function updateComposer() {
    actionBar.hidden = !aiTarget;
    actionButtons.forEach((node, i) => node.setAttribute('aria-pressed', String(writingActions[i].id === aiAction)));
    $('#ai-discussion').setAttribute('aria-pressed', String(!aiTarget));
    question.placeholder = writingPlaceholder(aiTarget); updatePending();
  }
  function renderAISnapshot() {
    snapshotContent.replaceChildren();
    targetLabel.textContent = aiTarget ? `${aiTarget.step.title} / ${aiTarget.field.name}` : '规划讨论 · 仅供参考，不写入字段';
    aiSnapshot.hidden = !aiTarget;
    if (!aiTarget) return;
    const value = formData[aiTarget.id];
    snapshotTitle.textContent = hasContent(value) ? '已有内容 · 只读' : '已有内容 · 尚未填写';
    if (aiTarget.field.type === 'table') {
      const table = el('table'), head = el('tr');
      aiTarget.field.columns.forEach(column => head.append(el('th', {scope: 'col'}, column)));
      const thead = el('thead'); thead.append(head); table.append(thead);
      const tbody = el('tbody');
      for (const row of value || []) { const tr = el('tr'); row.forEach(cell => tr.append(el('td', {}, cell))); tbody.append(tr); }
      table.append(tbody); snapshotContent.append(table);
      if (!hasContent(value)) snapshotContent.append(el('p', {}, '表格尚未填写。'));
    } else snapshotContent.append(el('pre', {}, value || '此字段尚未填写。'));
    aiSnapshot.open = JSON.stringify(value || '').length < 350;
  }
  function chooseAITarget(target) {
    // Keep only the user's supplemental text and chosen action, in page memory.
    rememberComposer();
    resetAIResult(); aiTarget = target;
    aiMemoryKey = target?.id || `discussion:${steps[currentStep].id}`;
    const step = steps[currentStep]; targetSelect.replaceChildren();
    step.fields.forEach(field => targetSelect.append(el('option', {value: `${step.id}-${field.name}`}, field.name)));
    targetSelect.append(el('option', {value: 'discussion'}, '规划讨论'));
    targetSelect.value = target?.id || 'discussion';
    const saved = composerMemory.get(aiMemoryKey);
    question.value = saved?.question ?? '';
    aiAction = saved?.action ?? defaultWritingAction(target ? formData[target.id] : '');
    renderAISnapshot(); updateComposer();
  }
  function snapshot() { return {formData: clone(formData), metadata: clone(metadata)}; }
  function pushHistory(editKey = '') {
    const now = Date.now();
    if (!editKey || lastEdit.key !== editKey || now - lastEdit.time > 700) { undo.push(snapshot()); if (undo.length > 30) undo.shift(); }
    lastEdit = {key: editKey, time: now}; redo = []; updateHistory();
  }
  function updateHistory() { undoBtn.disabled = !undo.length; redoBtn.disabled = !redo.length; }
  function historyMove(from, to) {
    if (!from.length) return;
    to.push(snapshot()); const state = from.pop();
    formData = state.formData; metadata = state.metadata; lastEdit = {};
    save(); renderStep(); updateHistory();
  }
  function commitField(id, value, editKey = id) {
    const f = steps.flatMap(s => s.fields.map(f => ({...f, id: `${s.id}-${f.name}`}))).find(f => f.id === id);
    const maxLength = f?.maxlength ?? LIMITS.text;
    if (typeof value === 'string' && value.length > maxLength) { say(`此字段最多 ${maxLength} 个字符，请缩短内容。`); return false; }
    if (f?.type === 'table' && value.length > LIMITS.rows) { say(`每张表最多 ${LIMITS.rows} 行。`); return false; }
    try { normalizeImport({[id]: value}); } catch { say('字段或表格超出支持范围，已保留原内容。'); return false; }
    pushHistory(editKey); formData[id] = value;
    if (id === 'strategy-validation-逻辑校验报告') { metadata.validationReport = {content: value, savedAt: Date.now()}; formData['strategy-validation-completed'] = value.trim() ? 'true' : 'false'; }
    if (id === 'revision-修改建议列表') formData['revision-completed'] = value.trim() ? 'true' : 'false';
    save(); updateProgress(); return true;
  }
  function save() {
    if (storageBlocked) { status.textContent = '自动保存已暂停；原存储保留。请导出草稿备份或使用恢复选项。'; return false; }
    try { localStorage.setItem(DRAFT_KEY, JSON.stringify(structuredExport(formData, metadata))); status.textContent = `已保存到本机 · ${new Date().toLocaleTimeString('zh-CN')}`; return true; }
    catch { status.textContent = '保存失败 · 请导出 JSON 备份'; say('保存失败：空间、格式限制或存储权限不足，当前内容仍在内存。'); return false; }
  }
  function load() {
    try {
      const saved = localStorage.getItem(DRAFT_KEY);
      if (saved !== null) {
        recovery.set(DRAFT_KEY, saved);
        ({formData, metadata} = normalizeImport(saved));
        const selectedStep = localStorage.getItem(STEP_KEY);
        if (/^(?:[0-9]|1[0-4])$/.test(selectedStep ?? '')) currentStep = Number(selectedStep);
      } else {
        const legacy = localStorage.getItem('blm-strategy-data');
        if (legacy !== null) { recovery.set('blm-strategy-data', legacy); ({formData, metadata} = normalizeImport(legacy)); }
        const report = localStorage.getItem('blm-validation-report');
        if (report !== null) {
          recovery.set('blm-validation-report', report);
          metadata.validationReport = normalizeReport(parseBoundedJSON(report));
          if (!formData['strategy-validation-逻辑校验报告']) formData['strategy-validation-逻辑校验报告'] = metadata.validationReport.content;
        }
        const step = localStorage.getItem('blm-strategy-step');
        if (/^(?:[0-9]|1[0-4])$/.test(step ?? '')) currentStep = Number(step);
      }
      status.textContent = saved !== null || Object.keys(formData).length ? '已恢复本机草稿；旧版原件保留。' : '尚未填写 · 编辑后自动本机保存';
    } catch { storageBlocked = true; recoveryBox.hidden = false; status.textContent = '本地数据异常或存储不可用；未覆盖原件。当前可在内存中编辑并导出。'; }
    try {
      // Deliberately detect only presence. Never parse or reuse persisted legacy secrets.
      legacyNotice.hidden = localStorage.getItem('blm-ai-config') === null;
      const raw = localStorage.getItem(CONFIG_KEY);
      if (raw !== null) config = canonicalConfig(raw);
    } catch { configBlocked = true; say('非秘密 AI 设置无法读取，已保留原件；AI 默认关闭。'); }
    writeConfig();
    try {
      const raw = localStorage.getItem(REMEMBERED_KEY);
      if (raw !== null) {
        if (configBlocked) throw new Error('Invalid config');
        credential = restoreRemembered(raw, config); key.value = credential.key;
        remembered = true; remember.checked = true;
      }
    } catch { say('记忆 Key 无法读取、格式异常或与配置不符，未使用；原记录未导出或覆盖。可重新输入，或用“忘记 Key”删除。'); }
    consent.checked = false; updateAIStatus();
  }
  function writeConfig() { provider.value = config.provider; endpoint.value = config.endpoint; model.value = config.model; }
  function readConfig() { return canonicalConfig({provider: provider.value, endpoint: endpoint.value.trim(), model: model.value.trim()}); }
  function updateAIStatus() {
    const configured = !configDirty && matchesDestination(credential, config) && !!config.model && consent.checked;
    globalAIButton.textContent = `AI 设置 · ${configured ? '已配置' : '未配置'}`;
    sharedStatus.textContent = configured ? '' : '请先完成全局设置。';
    sharedStatus.hidden = configured; configureAIButton.hidden = configured; aiSetup.hidden = configured;
    // Recipient and consent are shown only in global settings.
    try { destination.textContent = `内容接收方：${new URL(endpoint.value).hostname}`; }
    catch { destination.textContent = '请填写服务地址以确认内容接收方。'; }
    rememberedStatus.textContent = remembered ? '已在此浏览器记住 Key（明文）。' : '当前未启用已确认的浏览器记忆；本页可使用内存 Key。';
  }
  function invalidateAI() {
    consent.checked = false; resetAIResult();
  }
  function editAISettings(destinationChanged = false) {
    invalidateAI(); configDirty = true; credential = null; remembered = false;
    if (destinationChanged) { key.value = ''; remember.checked = false; }
    updateAIStatus();
  }
  function saveAISettings() {
    let next, nextCredential;
    try {
      next = readConfig();
      const entered = key.value.trim();
      if (entered) nextCredential = rememberedRecord(entered, next);
      else if (remember.checked) throw new Error('Missing key');
    } catch { say('设置无效：请检查公共 HTTPS 接口、模型 ID 和 Key；原存储未更改。'); return; }
    if (configBlocked && !confirm('原设置无法读取。确认用当前全局设置替换？')) return;
    const approved = consent.checked;
    invalidateAI(); consent.checked = approved;
    config = next; credential = nextCredential ?? null; configDirty = false; remembered = false; writeConfig();
    // Remove the old secret first. If any write fails, keep only the explicitly applied
    // in-memory credential and report the uncertain/failed persistence without echoing it.
    let removed = false;
    try {
      localStorage.removeItem(REMEMBERED_KEY); removed = true;
      localStorage.setItem(CONFIG_KEY, JSON.stringify(config)); configBlocked = false;
      if (remember.checked) { localStorage.setItem(REMEMBERED_KEY, JSON.stringify(credential)); remembered = true; }
      say(remembered ? '全局设置已保存；此浏览器已明文记住 Key。' : '全局设置已应用，非秘密配置已保存；浏览器记忆 Key 已移除，Key 仅在本页内存。');
    } catch {
      say(removed ? '本页已应用设置，但浏览器保存失败；未记住 Key。当前可用内存 Key，草稿仍可手工导出。' : '本页已应用设置，但浏览器拒绝删除旧记忆 Key；未确认已忘记，刷新可能恢复旧记录。请在浏览器设置中检查。');
    }
    if (!remembered) remember.checked = false;
    updateAIStatus();
  }
  function dropCredential() {
    key.value = ''; credential = null; remembered = false; remember.checked = false;
    invalidateAI(); updateAIStatus();
  }
  function forgetKey() {
    dropCredential();
    try { localStorage.removeItem(REMEMBERED_KEY); say('本页与此浏览器记忆 Key 已清除。'); }
    catch { say('本页 Key 已清空，但浏览器拒绝删除记忆 Key；未确认已忘记，刷新可能恢复旧记录。请在浏览器设置中检查。'); }
  }
  provider.addEventListener('change', () => {
    endpoint.value = PROVIDERS[provider.value].endpoint; model.value = PROVIDERS[provider.value].model; editAISettings(true);
  });
  endpoint.addEventListener('input', () => editAISettings(true));
  model.addEventListener('input', () => editAISettings()); key.addEventListener('input', () => editAISettings());
  remember.addEventListener('change', () => editAISettings());
  consent.addEventListener('change', () => { if (!consent.checked) invalidateAI(); updateAIStatus(); });
  window.addEventListener('storage', event => {
    if (event.key !== null && ![REMEMBERED_KEY, CONFIG_KEY].includes(event.key)) return;
    // Never import another tab's credentials or silently change their destination.
    dropCredential(); configDirty = true; updateAIStatus();
    say('另一标签页更改或清除了全局 AI 存储。本页 Key、同意与旧回复已失效；请重新输入并保存全局设置。');
  });
  window.addEventListener('pageshow', event => { if (event.persisted) invalidateAI(); });
  function updateProgress() {
    const count = steps.filter(s => s.fields.some(f => hasContent(formData[`${s.id}-${f.name}`]))).length;
    projectName.textContent = formData['company-info-企业名称']?.trim() || '未命名规划';
    progress.value = count; progressLabel.textContent = `${count} / 15 步已有内容`;
    stepButtons.forEach((b, i) => { if (i === currentStep) b.setAttribute('aria-current', 'step'); else b.removeAttribute('aria-current'); });
  }
  function goToStep(index) {
    currentStep = index;
    if (!storageBlocked) { try { localStorage.setItem(STEP_KEY, String(index)); } catch { say('步骤位置无法保存，规划内容仍可导出。'); } }
    renderStep();
    body.scrollTop = 0; $('#step-heading').focus({preventScroll: true});
  }
  function renderStep() {
    for (const e of editors) e.toTextArea(); editors = [];
    body.replaceChildren(); pager.replaceChildren();
    const step = steps[currentStep];
    body.classList.toggle('company-step', currentStep === 0);
    const title = el('h1', {id: 'step-heading', tabindex: '-1'}, step.title);
    body.append(el('p', {class: 'step-breadcrumb'}, `${groupFor(currentStep)} / 第 ${currentStep + 1} 步`), title, el('p', {class: 'step-description'}, purposes[currentStep]));
    if (returnPoint) body.append(button('返回检查结果', returnToReport, {id: 'return-report'}));
    renderHints(step);
    const stepTools = menu('撤销 / 重做 / 重置', 'step-tools');
    stepTools.lastElementChild.append(undoBtn, redoBtn);
    stepTools.lastElementChild.append(button('重置当前步骤', () => {
      if (!confirm(`确认重置“${step.title}”？可使用撤销恢复当前会话内容。`)) return;
      pushHistory(); for (const f of step.fields) delete formData[`${step.id}-${f.name}`];
      if (step.id === 'strategy-validation') { delete metadata.validationReport; delete formData['strategy-validation-completed']; }
      if (step.id === 'revision') delete formData['revision-completed'];
      reportEntries = []; returnPoint = null;
      clearComposer(step);
      save(); renderStep();
    }, {id: 'reset-step'}));
    const reportTools = el('div', {class: 'toolbar report-tools'});
    if (step.id === 'strategy-validation') reportTools.append(button('生成本地完整性报告', basicValidation, {id: 'basic-validation'}));
    if (step.id === 'revision') reportTools.append(button('复制校验报告到修订草稿', () => {
      if (formData['revision-修改建议列表'] && !confirm('确认替换现有修订草稿？')) return;
      commitField('revision-修改建议列表', formData['strategy-validation-逻辑校验报告'] || metadata.validationReport?.content || '请先完成战略逻辑校验，再记录修改项、责任人与处理结果。'); renderStep();
    }, {id: 'revision-from-report'}));
    hints.append(stepTools);
    if (reportTools.childElementCount) body.append(reportTools);
    if (['strategy-validation', 'revision'].includes(step.id)) {
      body.append(el('p', {class: 'validation-disclaimer'}, '本地检查只核对是否填写，不能证明战略逻辑正确。报告可手工编辑，也可按需使用 AI。'));
    }
    if (step.id === 'revision') {
      body.append(el('p', {}, '手工记录修改建议与处理结果。通过下列链接回到对应步骤修改；关键决策须由你确认，AI 不会自动改写其他字段。'));
      const links = el('div', {class: 'revision-links'});
      steps.slice(0, 13).forEach((s, i) => links.append(button(s.title, () => goToStep(i)))); body.append(links);
    }
    for (const field of step.fields) renderField(step, field);
    if (['strategy-validation', 'revision'].includes(step.id)) renderMissing();
    const count = el('span', {class: 'field-count'}, `${step.fields.length} 项信息 · 可随时继续补充`);
    const prev = button(`上一步：${steps[currentStep - 1]?.title || ''}`, () => goToStep(currentStep - 1), {id: 'previous-step'}); prev.hidden = currentStep === 0;
    const next = button(`下一步：${steps[currentStep + 1]?.title || ''}`, () => goToStep(currentStep + 1), {id: 'next-step', class: 'primary'}); next.hidden = currentStep === 14;
    if (returnPoint) pager.append(button('返回检查结果', returnToReport, {id: 'return-report-footer'}));
    pager.append(count, prev, button('稍后继续', () => { if (save()) say('已保存到当前浏览器，可随时继续填写。建议导出 JSON 备份。'); }, {id: 'save-later'}), next); updateProgress();
  }
  function renderHints(step) {
    hints.replaceChildren();
    const context = el('details', {class: 'context-help', open: ''}); context.append(el('summary', {}, '填写提示'));
    const tips = el('ol');
    for (const tip of ['明确本次规划的业务范围', '先写事实，判断可以逐步补充', '不确定的内容可暂时留空']) tips.append(el('li', {}, tip));
    const example = el('details', {id: 'writing-example'}); example.append(el('summary', {}, '查看填写示例'));
    example.append(el('p', {}, currentStep === 0 ? '示例（虚构，仅供参考）：某制造服务企业，为中小工厂提供设备监测服务。当前处于业务验证阶段，需要补充客户续费数据。' : `示例（虚构，仅供参考）：围绕“${step.title}”，记录已知事实、证据来源和仍需核实的问题。`));
    context.append(tips, example); hints.append(context);
    const aiIntro = el('section', {class: 'ai-entry'}); aiIntro.append(el('h2', {}, '一起写好这一步'), el('p', {}, '从待补充的字段开始，也可切换到规划讨论。'), button('AI 帮写当前步骤', () => { chooseAITarget(defaultAITarget(step, formData)); openAI(); }, {id: 'open-ai'})); hints.append(aiIntro);
  }
  function renderMissing() {
    const current = missingFields(steps, formData);
    if (!reportEntries.length) reportEntries = current;
    const box = el('section', {id: 'missing-fields', 'aria-label': '待补充字段'});
    box.append(el('h2', {}, `填写完整性 · ${current.length} 项待补充`));
    const list = el('ul');
    // Keep resolved entries visible during this review session; derive status from current values.
    const entries = [...reportEntries, ...current.filter(item => !reportEntries.some(old => old.id === item.id))];
    for (const item of entries) {
      const resolved = hasContent(formData[item.id]);
      const row = el('li', {'data-missing-field': item.id, 'data-resolved': String(resolved)});
      row.append(el('span', {}, `${item.step.title} / ${item.field.name} · ${resolved ? '已补充' : '待补充'}`), button(resolved ? '查看' : '去补充', () => {
        returnPoint = {step: currentStep, scroll: body.scrollTop, field: item.id};
        goToStep(item.index); focusField(item.id);
      })); list.append(row);
    }
    if (!entries.length) box.append(el('p', {}, '前 13 步均有内容，仍需人工核验。'));
    box.append(list); body.append(box);
  }
  function focusField(id) {
    const box = [...body.querySelectorAll('[data-field]')].find(node => node.dataset.field === id);
    if (!box) return;
    requestAnimationFrame(() => {
      const cm = box.querySelector('.CodeMirror')?.CodeMirror;
      if (cm) cm.focus(); else box.querySelector('input:not([type=file]), textarea')?.focus({preventScroll: true});
      box.scrollIntoView({block: 'center', behavior: 'instant'});
    });
  }
  function returnToReport() {
    const point = returnPoint; returnPoint = null; goToStep(point.step);
    body.scrollTop = point.scroll;
    const row = [...body.querySelectorAll('[data-missing-field]')].find(node => node.dataset.missingField === point.field);
    row?.querySelector('button')?.focus({preventScroll: true});
  }
  function renderField(step, field) {
    const id = `${step.id}-${field.name}`;
    const box = el('section', {class: 'field', 'data-field': id});
    const head = el('div', {class: 'field-heading'}), label = el('h3');
    label.append(el('label', {for: id}, field.name));
    if (field.type === 'table') label.firstChild.removeAttribute('for');
    const actions = el('div', {class: 'field-actions', id: `actions-${id}`});
    actions.append(button('AI 帮写', () => { chooseAITarget({id, field, step}); openAI(); }, {'data-ai-field': id, 'aria-haspopup': 'dialog'}));
    if (field.type !== 'table') {
      const file = el('input', {type: 'file', accept: '.txt,.md,text/plain,text/markdown', hidden: '', 'aria-label': `导入${field.name}文本`});
      file.addEventListener('change', async () => {
        try {
          const f = file.files[0]; if (!f) return;
          if (!/\.(txt|md)$/i.test(f.name) || f.size > LIMITS.text * 3) throw new Error();
          const text = await f.text();
          if ((formData[id] || '') && !confirm(`确认用文件文本替换“${field.name}”？`)) return;
          if (commitField(id, text, '')) renderStep();
        } catch { say('仅支持限长的 UTF-8 文本或 Markdown 文件；不支持 .docx。原字段未更改。'); }
        finally { file.value = ''; }
      });
      actions.append(button('导入文本', () => file.click()), file);
    }
    head.append(label, actions); box.append(head);
    if (field.type === 'table') {
      const wrap = el('div', {class: 'table-wrap'}), table = el('table', {class: 'table-input', 'aria-label': field.name});
      const tr = el('tr'); for (const c of [...field.columns, '操作']) tr.append(el('th', {scope: 'col'}, c));
      const thead = el('thead'); thead.append(tr); table.append(thead); const tbody = el('tbody');
      const rows = formData[id]?.length ? formData[id] : [field.columns.map(() => '')];
      rows.forEach((row, r) => {
        const line = el('tr'); row.forEach((cell, c) => {
          const td = el('td'), input = el('textarea', {'aria-label': `${field.name} 第${r + 1}行 ${field.columns[c]}`, maxlength: String(LIMITS.cell), 'data-row': r, 'data-column': c}); input.value = cell;
          input.addEventListener('input', () => { const data = clone(formData[id]?.length ? formData[id] : rows); data[r][c] = input.value; if (!commitField(id, data, `${id}-${r}-${c}`)) input.value = (formData[id]?.[r]?.[c] ?? rows[r][c]); }); td.append(input); line.append(td);
        });
        const operation = el('td'); operation.append(button('删除', () => { const data = clone(formData[id]?.length ? formData[id] : rows); data.splice(r, 1); commitField(id, data, ''); renderStep(); }, {'aria-label': `删除${field.name}第${r + 1}行`})); line.append(operation); tbody.append(line);
      });
      table.append(tbody); wrap.append(table); box.append(wrap, button('添加行', () => { const data = clone(formData[id]?.length ? formData[id] : rows); data.push(field.columns.map(() => '')); if (commitField(id, data, '')) renderStep(); }, {'data-add-row': id}));
    } else {
      const maxLength = field.maxlength ?? LIMITS.text;
      const input = el(field.type === 'input' ? 'input' : 'textarea', {id, 'aria-label': field.name, maxlength: String(maxLength), placeholder: field.placeholder || '支持 Markdown；可手工编辑并保存。'});
      input.value = formData[id] || '';
      if (simpleField(step, field)) {
        input.classList.add('simple-input');
        input.addEventListener('input', () => { if (!commitField(id, input.value)) input.value = formData[id] || ''; });
        box.append(input); body.append(box); return;
      }
      const columns = el('div', {class: 'editor-preview'}), editPane = el('div', {class: 'editor-pane'}), preview = el('div', {class: 'preview-pane', hidden: ''});
      const rich = el('div', {class: 'rich-content', id: `${id}-preview`}); preview.append(rich);
      const toggle = button('预览', () => {
        preview.hidden = !preview.hidden; toggle.setAttribute('aria-expanded', String(!preview.hidden)); toggle.textContent = preview.hidden ? '预览' : '收起预览';
      }, {class: 'preview-toggle', 'aria-expanded': 'false', 'aria-controls': `${id}-preview`});
      const format = el('div', {class: 'format-actions'}); format.append(el('span', {}, 'Markdown（可选）'), toggle);
      editPane.append(input); columns.append(editPane, format, preview); box.append(columns); body.append(box);
      const editor = new window.EasyMDE({element: input, autoDownloadFontAwesome: false, spellChecker: false, autosave: {enabled: false}, status: ['lines', 'words'], toolbar: false, minHeight: step.id === 'company-info' ? '100px' : '140px', previewRender: renderMarkdown, renderingConfig: {sanitizerFunction: sanitizeRichHTML}, inputStyle: 'textarea', lineWrapping: true, forceSync: true, shortcuts: {togglePreview: null, toggleSideBySide: null, toggleFullScreen: null, drawImage: null, drawLink: null, undo: null, redo: null}});
      editor.codemirror.getInputField().setAttribute('aria-label', `${field.name} Markdown 编辑`);
      editors.push(editor);
      const syncPreview = value => { rich.innerHTML = renderMarkdown(value); };
      syncPreview(input.value);
      editor.codemirror.setOption('extraKeys', {'Ctrl-Z': () => historyMove(undo, redo), 'Cmd-Z': () => historyMove(undo, redo), 'Ctrl-Y': () => historyMove(redo, undo), 'Cmd-Shift-Z': () => historyMove(redo, undo)});
      editor.codemirror.on('beforeChange', (_cm, change) => {
        const current = editor.value();
        const nextLength = current.length - (editor.codemirror.indexFromPos(change.to) - editor.codemirror.indexFromPos(change.from)) + change.text.join('\n').length;
        if (nextLength > maxLength) { change.cancel(); say(`此字段最多 ${maxLength} 个字符，已保留原内容。`); }
      });
      editor.codemirror.on('change', () => { const value = editor.value(); if (commitField(id, value)) syncPreview(value); });
      return;
    }
    body.append(box);
  }
  function basicValidation() {
    const missing = missingFields(steps, formData);
    const incomplete = missing.map(item => `- ${item.step.title} / ${item.field.name}：待补充`);
    const report = `## 本地完整性检查\n\n${incomplete.length ? incomplete.join('\n') : '前 13 步均有内容。'}\n\n此检查仅核对是否填写，不能证明战略逻辑正确。请人工核验目标、业务设计、关键任务与资源之间的承接关系。`;
    if (formData['strategy-validation-逻辑校验报告'] && !confirm('用本地完整性检查替换现有报告？')) return;
    reportEntries = missing;
    commitField('strategy-validation-逻辑校验报告', report, ''); renderStep(); say('已生成本地完整性报告，未调用 AI。');
  }
  importInput.addEventListener('change', async () => {
    try {
      const file = importInput.files[0]; if (!file) return;
      if (!/\.json$/i.test(file.name) || file.size > LIMITS.bytes) throw new Error();
      const next = normalizeImport(await file.text());
      const serialized = JSON.stringify(structuredExport(next.formData, next.metadata));
      if (storageBlocked) { say('请先导出恢复副本并显式清除异常本地数据，再导入；原草稿未更改。'); return; }
      if (!confirm('确认用所选 JSON 替换当前草稿？可在当前会话撤销。')) return;
      // Persist first. A rejected/oversized/quota-failed import never changes either draft or storage.
      localStorage.setItem(DRAFT_KEY, serialized);
      pushHistory(); ({formData, metadata} = next); reportEntries = []; returnPoint = null;
      clearComposer();
      renderStep(); status.textContent = 'JSON 已校验、导入并保存到本机。'; say('导入成功。');
    } catch { say('导入失败：仅支持有效、限长的规划 JSON（扁平或分步格式）。原草稿与存储未更改；不支持 .docx。'); }
    finally { importInput.value = ''; }
  });
  function download(filename, content, type) {
    const blob = new Blob([content], {type}); const url = URL.createObjectURL(blob); const a = el('a', {href: url, download: filename});
    document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function documentMarkdown() {
    let text = `# ${metadata.header?.title ?? 'BLM扩展框架战略规划'}\n\n`;
    for (const [i, s] of steps.entries()) {
      text += `## ${i + 1}. ${s.title}\n\n${s.description}\n\n`;
      for (const f of s.fields) {
        const value = formData[`${s.id}-${f.name}`]; text += `### ${f.name}\n\n`;
        if (f.type === 'table') {
          const cell = v => String(v).replace(/\|/g, '\\|').replace(/\r?\n/g, ' / ');
          text += `| ${f.columns.map(cell).join(' | ')} |\n| ${f.columns.map(() => '---').join(' | ')} |\n`;
          for (const row of value || []) text += `| ${row.map(cell).join(' | ')} |\n`;
          text += '\n';
        } else text += `${value || ''}\n\n`;
      }
    }
    if (metadata.validationReport) text += `## 已保存的校验记录\n\n${metadata.validationReport.content}\n`;
    return text;
  }
  function exportFile(format) {
    try {
      const name = `deepblm-${Date.now()}`;
      if (format === 'json') download(`${name}.json`, JSON.stringify(structuredExport(formData, metadata), null, 2), 'application/json');
      if (format === 'md') download(`${name}.md`, documentMarkdown(), 'text/markdown;charset=utf-8');
      if (format === 'doc') {
        let html = `<h1>${escapeHTML(metadata.header?.title ?? 'BLM扩展框架战略规划')}</h1>`;
        for (const [i, s] of steps.entries()) {
          html += `<h2>${i + 1}. ${escapeHTML(s.title)}</h2><p>${escapeHTML(s.description)}</p>`;
          for (const f of s.fields) {
            const v = formData[`${s.id}-${f.name}`]; html += `<h3>${escapeHTML(f.name)}</h3>`;
            if (f.type === 'table') html += `<table><thead><tr>${f.columns.map(c => `<th>${escapeHTML(c)}</th>`).join('')}</tr></thead><tbody>${(v || []).map(row => `<tr>${row.map(c => `<td>${escapeHTML(c)}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
            else html += renderMarkdown(v || '');
          }
        }
        if (metadata.validationReport) html += '<h2>已保存的校验记录</h2>' + renderMarkdown(metadata.validationReport.content);
        download(`${name}.doc`, `<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><title>BLM 战略规划</title></head><body>${sanitizeRichHTML(html)}</body></html>`, 'application/msword');
      }
      say('已准备下载；JSON 可用于恢复，Word 兼容 .doc 为 HTML 格式，实际排版请在 Word 中核验。');
    } catch { say('无法导出：草稿超出支持范围。请缩短字段，或导出恢复副本。'); }
  }
  function clearLocal() {
    if (!confirm('确认删除本工具在本机的草稿、记忆 Key、旧版项目、旧版 AI 设置与非秘密偏好？此操作不会清除其他应用数据。请先导出备份。')) return;
    dropCredential();
    let failed = false;
    for (const k of TOOL_KEYS) { try { localStorage.removeItem(k); } catch { failed = true; } }
    if (failed) { say('清除未完成：本页 Key 已清空，但本地记录（包括记忆 Key）未确认全部删除；请使用浏览器设置检查。'); return; }
    try {
      key.value = ''; consent.checked = false; resetAIResult(); composerMemory.clear(); aiMemoryKey = null; aiTarget = null; targetSelect.replaceChildren(); question.value = '';
      formData = {}; metadata = {}; currentStep = 0; undo = []; redo = []; returnPoint = null; reportEntries = []; recovery.clear(); storageBlocked = false; configBlocked = false; recoveryBox.hidden = true; legacyNotice.hidden = true;
      config = {provider: 'deepseek', ...PROVIDERS.deepseek}; configDirty = false; writeConfig(); updateAIStatus(); renderStep(); updateHistory(); status.textContent = '本工具本地数据已清除；下次编辑才会重新保存。'; say('已清除本工具数据（包括记忆 Key）。');
    } catch { say('清除未完成：浏览器拒绝存储操作，请使用浏览器设置检查；未清除其他应用数据。'); }
  }
  async function runAI() {
    if (pending) return;
    let settings;
    try {
      settings = config;
      if (configDirty || !settings.model || !matchesDestination(credential, settings) || !validKey(credential?.key)) { say('请先完成全局设置。'); return; }
      if (!consent.checked) { say('请先完成全局设置。'); return; }
      validateEndpoint(settings.endpoint);
      const requestKey = credential.key;
      // Limit the aggregate context and prompt before any network request.
      const context = JSON.stringify(structuredExport(formData, metadata));
      const messages = writingMessages({target: aiTarget, action: aiAction, context, question: question.value});
      if (messages.reduce((size, item) => size + item.content.length, 0) > 180000) { say('规划上下文过长，请缩短后发送。'); return; }
      const epoch = ++aiEpoch;
      controller = new AbortController(); const requestController = controller; const timer = setTimeout(() => requestController.abort(), 60000);
      pending = true; updatePending(); aiApply.hidden = true; aiAnswer = ''; aiMessage.textContent = ''; resultCard.dataset.state = 'loading'; aiResult.textContent = '正在整理建议…';
      try {
        const response = await fetch(settings.endpoint, {method: 'POST', mode: 'cors', credentials: 'omit', cache: 'no-store', redirect: 'error', referrerPolicy: 'no-referrer', headers: {'Content-Type': 'application/json', Authorization: `Bearer ${requestKey}`}, body: JSON.stringify({model: settings.model, stream: false, messages}), signal: requestController.signal});
        if (epoch !== aiEpoch) return;
        if (!response.ok) { resultCard.dataset.state = 'error'; aiResult.textContent = `生成失败（HTTP ${response.status}）。请稍后重试或去全局设置。`; return; }
        // Bound streamed response bytes before parsing to avoid unbounded provider output.
        const reader = response.body.getReader(), decoder = new TextDecoder(); let raw = '', bytes = 0;
        while (true) {
          const {done, value} = await reader.read(); if (done) break;
          bytes += value.byteLength; if (bytes > LIMITS.bytes) { await reader.cancel(); throw new Error('response-limit'); }
          raw += decoder.decode(value, {stream: true});
        }
        raw += decoder.decode(); const data = parseBoundedJSON(raw);
        const content = data?.choices?.[0]?.message?.content;
        if (typeof content !== 'string' || !content.trim() || content.length > LIMITS.text) throw new Error('response-format');
        if (epoch !== aiEpoch) return;
        aiAnswer = content.replaceAll(requestKey, '[Key 已隐藏]'); aiResult.innerHTML = renderMarkdown(aiAnswer); resultCard.dataset.state = 'success'; aiApply.hidden = !canApplyWriting(aiTarget, aiAction);
        say(canApplyWriting(aiTarget, aiAction) ? `建议已返回，核验后可采用到“${aiTarget.field.name}”。` : '以下建议供人工核验，不写入字段。');
      } catch {
        if (epoch === aiEpoch) { resultCard.dataset.state = 'error'; aiResult.textContent = '生成未完成：网络、CORS、超时或接口格式不兼容。请重试；草稿未更改。'; }
      } finally {
        clearTimeout(timer);
        if (epoch === aiEpoch) { pending = false; updatePending(); }
      }
    } catch { say('请先完成全局设置。'); }
  }
  function applyAI() {
    if (!canApplyWriting(aiTarget, aiAction) || !aiAnswer || pending) return;
    try {
      const {id, field} = aiTarget; let value = aiAnswer;
      if (field.type === 'table') value = parseBoundedJSON(value.replace(/^```(?:json)?\s*|\s*```$/g, ''));
      normalizeImport({...formData, [id]: value});
      if (!confirm(`确认将 AI 建议写入“${field.name}”？请先核验，原内容可撤销。`)) return;
      if (commitField(id, value, '')) {
        const scrollTop = body.scrollTop;
        renderStep(); body.scrollTop = scrollTop;
        aiOpener = body.querySelector(`[data-field="${CSS.escape(id)}"] [data-ai-field]`);
        renderAISnapshot(); aiApply.hidden = true; say('已采用建议，可关闭后撤销；请继续人工核验。');
      }
    } catch { say('AI 内容不符合字段或表格结构，未改写草稿。'); }
  }
  load(); host.hidden = false; document.body.classList.add('workspace-ready'); renderStep(); updateHistory();
  matchMedia('(min-width: 1024px)').addEventListener('change', event => {
    if (event.matches) requestAnimationFrame(() => editors.forEach(editor => editor.codemirror.refresh()));
  });
  document.addEventListener('keydown', event => {
    if (!(event.ctrlKey || event.metaKey) || !['z', 'y', 's'].includes(event.key.toLowerCase())) return;
    if (!matchMedia('(min-width: 1024px)').matches) return;
    const codeMirror = event.target.closest?.('.CodeMirror'); if (codeMirror && event.key.toLowerCase() !== 's') return;
    if (event.key.toLowerCase() === 's') { event.preventDefault(); save(); }
    // Native text inputs retain native undo; explicit toolbar provides whole-draft undo/redo.
  });
}
