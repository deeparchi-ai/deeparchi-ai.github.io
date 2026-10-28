export const VERSION = '1';
export const EMAIL = 'contact@deeparchi.com.cn';
export const SERVICES = Object.freeze(['ip-guard', 'deep-blm', 'architecture', 'tech-ma']);
export const CATEGORIES = Object.freeze(['product', 'a2a', 'consulting', 'integration', 'general', 'partnership']);
export const SURFACES = Object.freeze(['cards', 'demo', 'a2a', 'support', 'contact', 'demand']);
export const EVENTS = Object.freeze(['product_view', 'demo_open', 'demo_complete', 'intent_open', 'mail_draft_ready', 'mailto_click', 'a2a_step', 'a2a_interest']);
const exactKeys = (value, keys) => value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).every(key => keys.includes(key));
const token = value => typeof value === 'string' && /^[a-zA-Z0-9-]{8,64}$/.test(value);

export function validateConfig(config) {
  if (!exactKeys(config, ['version', 'enabled', 'endpoint', 'site_id', 'consent_required']) || config.version !== VERSION || typeof config.enabled !== 'boolean' || config.consent_required !== true) return null;
  if (config.site_id !== undefined && (typeof config.site_id !== 'string' || !/^[a-zA-Z0-9_-]{1,40}$/.test(config.site_id))) return null;
  if (!config.enabled) return config.endpoint === null ? Object.freeze({...config}) : null;
  try {
    const url = new URL(config.endpoint);
    // Only an explicitly configured public HTTPS receiver; no credentials or URL metadata.
    if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash || url.port || !/^[a-z0-9.-]+\.[a-z]{2,}$/i.test(url.hostname) || /(?:^|\.)(?:localhost|local|internal|test|invalid)$/.test(url.hostname)) return null;
    return Object.freeze({...config, endpoint: url.href});
  } catch { return null; }
}

export function validatePayload(payload) {
  return Boolean(exactKeys(payload, ['version', 'event', 'service', 'category', 'surface', 'audience', 'is_test', 'session_id', 'event_id', 'step']) &&
    payload.version === VERSION && EVENTS.includes(payload.event) && (payload.service === null || SERVICES.includes(payload.service)) &&
    CATEGORIES.includes(payload.category) && SURFACES.includes(payload.surface) && payload.audience === 'browser_interaction' && typeof payload.is_test === 'boolean' && token(payload.session_id) && token(payload.event_id) &&
    (payload.event === 'a2a_step' ? Number.isInteger(payload.step) && payload.step >= 1 && payload.step <= 5 : payload.step === undefined) &&
    (!['product_view', 'demo_open', 'demo_complete', 'a2a_step', 'a2a_interest'].includes(payload.event) || SERVICES.includes(payload.service)));
}

export function privacyBlocked(navigatorLike = {}) {
  return navigatorLike.globalPrivacyControl === true || ['1', 'yes'].includes(String(navigatorLike.doNotTrack).toLowerCase());
}

export function createSignals(rawConfig, {navigatorLike = {}, isTest = false, local = false, transport, idFactory = () => globalThis.crypto.randomUUID()} = {}) {
  const config = validateConfig(rawConfig);
  let consent = false;
  const blocked = () => privacyBlocked(navigatorLike);
  const available = () => Boolean(config?.enabled && !blocked());
  let session;
  const sent = new Set(); // In-memory session dedupe only; never a unique-person count.
  return {
    available,
    status: () => !config?.enabled ? '匿名统计未连接，未收集事件。' : blocked() ? '已尊重 DNT/GPC，匿名统计关闭。' : consent ? '已允许匿名统计，可随时关闭。' : '匿名统计未获同意，未收集事件。',
    setConsent(value) { consent = available() && value === true; if (!consent) { session = undefined; sent.clear(); } },
    async track(fields) {
      if (!available() || !consent || !exactKeys(fields, ['event', 'service', 'category', 'surface', 'step'])) return false;
      // Automated/local runs never use the real transport, even with an enabled fixture config.
      if ((isTest || local) && !transport) return false;
      try {
        session ??= idFactory();
        const payload = {...fields, version: VERSION, audience: 'browser_interaction', is_test: Boolean(isTest || local), session_id: session, event_id: idFactory()};
        if (!validatePayload(payload)) return false;
        const key = JSON.stringify([fields.event, fields.service, fields.category, fields.surface, fields.step]);
        if (sent.has(key)) return false;
        sent.add(key);
        const send = transport ?? ((endpoint, body) => fetch(endpoint, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body), credentials: 'omit', referrerPolicy: 'no-referrer', mode: 'cors', cache: 'no-store', redirect: 'error'}));
        const response = await send(config.endpoint, payload);
        return response?.ok === true;
      } catch { return false; }
    }
  };
}

export function mailDraft({source, problem, result = '', constraints = ''}) {
  if (typeof source !== 'string' || !source.trim() || /[\r\n]/.test(source)) throw new TypeError('Invalid source');
  if (typeof problem !== 'string' || !problem.trim() || problem.length > 500 || typeof result !== 'string' || result.length > 500 || typeof constraints !== 'string' || constraints.length > 300) throw new TypeError('Invalid draft');
  const subject = `DeepArchi｜${source} 需求意向`;
  const body = `来源：${source}\r\n业务问题：${problem.trim()}\r\n期望结果：${result.trim() || '未填写'}\r\n约束：${constraints.trim() || '未填写'}`;
  const encode = value => encodeURIComponent(value).replace(/[!'()*]/g, char => `%${char.charCodeAt(0).toString(16).toUpperCase()}`);
  return {text: `收件人：${EMAIL}\n主题：${subject}\n\n${body}`, uri: `mailto:${EMAIL}?subject=${encode(subject)}&body=${encode(body)}`};
}
