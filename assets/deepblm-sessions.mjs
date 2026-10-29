// Page-memory-only working suggestions. Never serialized into a planning draft or export.
export const SESSION_LIMITS = Object.freeze({targets: 24, characters: 600000, question: 8000, draft: 100000});
// A stored result is usable only while it still matches the live revision, target and action.
export function resultEligible(result, revision, target, action) {
  return !!result && result.state === 'success' && result.target === target && result.action === action
    && result.planning === revision.planning && result.connection === revision.connection;
}
export function writingSessions({maxTargets = SESSION_LIMITS.targets, maxCharacters = SESSION_LIMITS.characters} = {}) {
  const entries = new Map();
  let planning = 0, connection = 0;
  const revision = () => ({planning, connection});
  const weight = entry => entry.question.length + (entry.result ? entry.result.draft.length + entry.result.original.length : 0);
  const copy = entry => {
    const out = {question: entry.question, action: entry.action};
    if (entry.result) out.result = {...entry.result};
    return out;
  };
  function get(id) {
    const entry = entries.get(id);
    if (!entry) return undefined;
    entries.delete(id); entries.set(id, entry); // Least-recently used goes first when trimming.
    return copy(entry);
  }
  function set(id, entry) {
    const stored = {question: String(entry.question ?? '').slice(0, SESSION_LIMITS.question), action: entry.action};
    // Only a still-valid result is kept; a pending, failed or outdated one is dropped instead.
    if (resultEligible(entry.result, revision(), id, entry.action)) {
      stored.result = {...entry.result, draft: String(entry.result.draft).slice(0, SESSION_LIMITS.draft), original: String(entry.result.original ?? '').slice(0, SESSION_LIMITS.draft)};
    }
    entries.delete(id); entries.set(id, stored);
    let characters = [...entries.values()].reduce((total, value) => total + weight(value), 0);
    while (entries.size > maxTargets || characters > maxCharacters) {
      const oldest = entries.keys().next().value, value = entries.get(oldest);
      characters -= weight(value);
      entries.delete(oldest);
    }
  }
  // Planning edits and connection/consent changes invalidate every stored result but keep user text.
  function invalidate(kind = 'planning') {
    if (kind === 'connection') connection++; else planning++;
    for (const entry of entries.values()) delete entry.result;
  }
  function clear(step) {
    for (const id of entries.keys()) if (!step || id.startsWith(`${step}-`) || id === `discussion:${step}`) entries.delete(id);
  }
  return {get, set, revision, invalidate, clear, size: () => entries.size};
}
