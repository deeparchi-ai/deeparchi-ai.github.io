export const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
const allowed = ['p', 'br', 'strong', 'em', 'b', 'i', 'del', 's', 'ul', 'ol', 'li', 'blockquote', 'pre', 'code', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'a'];
// Only this function creates rich HTML. Trusted UI controls are built with DOM APIs.
export function sanitizeRichHTML(html) {
  const fragment = window.DOMPurify.sanitize(html, {
    ALLOWED_TAGS: allowed, ALLOWED_ATTR: ['href', 'title'], ALLOW_DATA_ATTR: false, ALLOW_ARIA_ATTR: false,
    FORBID_TAGS: ['script', 'style', 'svg', 'math', 'iframe', 'object', 'embed', 'form', 'input', 'textarea', 'button', 'img', 'video', 'audio', 'source', 'link', 'meta'],
    RETURN_DOM_FRAGMENT: true,
  });
  for (const a of fragment.querySelectorAll('a')) {
    const href = a.getAttribute('href') || '';
    // No relative URLs, blobs, data URLs, protocol-relative URLs or control-character obfuscation.
    if (!/^(https?:\/\/|mailto:)/i.test(href) || /[\u0000-\u0020\u007f]/.test(href)) a.removeAttribute('href');
    else { a.setAttribute('rel', 'noopener noreferrer'); a.setAttribute('target', '_blank'); }
  }
  const container = document.createElement('div');
  container.append(fragment);
  return container.innerHTML;
}
export function renderMarkdown(text) {
  const html = window.EasyMDE.prototype.markdown.call({options: {renderingConfig: {singleLineBreaks: true, codeSyntaxHighlighting: false, sanitizerFunction: sanitizeRichHTML}}}, String(text));
  return sanitizeRichHTML(html);
}
