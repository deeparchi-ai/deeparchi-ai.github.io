import {normalizeConfig, validateEndpoint} from './deepblm-data.mjs';

// Separate from drafts and recovery. This is optional plaintext storage, not a vault.
export const REMEMBERED_KEY = 'deepblm-remembered-key-v1';
export function canonicalConfig(input) {
  const config = normalizeConfig(input);
  return {...config, endpoint: config.endpoint ? validateEndpoint(config.endpoint) : ''};
}
export function validKey(key) {
  return typeof key === 'string' && /^[\x21-\x7e]{1,4096}$/.test(key);
}
export function matchesDestination(credential, config) {
  return !!credential && credential.provider === config.provider && credential.endpoint === config.endpoint;
}
export function rememberedRecord(key, config) {
  const checked = canonicalConfig(config);
  if (!validKey(key) || !checked.endpoint || !checked.model) throw new Error('Invalid credential');
  return {version: 1, remembered: true, provider: checked.provider, endpoint: checked.endpoint, key};
}
export function restoreRemembered(raw, config) {
  // Bound before parsing; never pass secret data to draft parsers or recovery.
  if (typeof raw !== 'string' || raw.length > 32768) throw new Error('Invalid credential record');
  const value = JSON.parse(raw);
  if (!value || Object.getPrototypeOf(value) !== Object.prototype ||
      Object.keys(value).length !== 5 || !['version', 'remembered', 'provider', 'endpoint', 'key'].every(k => Object.hasOwn(value, k)) ||
      value.version !== 1 || value.remembered !== true) throw new Error('Invalid credential record');
  const checked = rememberedRecord(value.key, {...config, provider: value.provider, endpoint: value.endpoint});
  if (checked.endpoint !== value.endpoint || !matchesDestination(checked, canonicalConfig(config))) throw new Error('Credential destination mismatch');
  return checked;
}
