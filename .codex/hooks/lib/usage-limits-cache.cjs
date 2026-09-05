#!/usr/bin/env node
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');

const DEFAULT_CACHE_TTL_MS = 60_000;
const DEFAULT_FETCH_TIMEOUT_MS = 5_000;
const DEFAULT_USER_AGENT = 'vc-codex-hooks/1.0';
const DEFAULT_ELIGIBILITY_CACHE_TTL_MS = 60_000;

function getUsageCachePath() {
  return process.env.VC_USAGE_CACHE_PATH || path.join(os.tmpdir(), 'vc-usage-limits-cache.json');
}

function getQuotaEligibilityCachePath() {
  return process.env.CK_USAGE_ELIGIBILITY_CACHE_PATH || `${getUsageCachePath()}.eligibility`;
}

function readUsageCache(cachePath = getUsageCachePath()) {
  try {
    if (!fs.existsSync(cachePath)) return null;
    const parsed = JSON.parse(fs.readFileSync(cachePath, 'utf8'));
    return parsed && typeof parsed === 'object' ? parsed : null;
  } catch {
    return null;
  }
}

function getCacheAgeMs(cache, now = Date.now()) {
  if (!cache || typeof cache.timestamp !== 'number') return Number.POSITIVE_INFINITY;
  return Math.max(0, now - cache.timestamp);
}

function isUsageCacheFresh(cache, maxAgeMs, now = Date.now()) {
  return getCacheAgeMs(cache, now) <= maxAgeMs;
}

function normalizeUtilization(utilization) {
  if (typeof utilization !== 'number' || !Number.isFinite(utilization)) return null;
  if (utilization > 0 && utilization < 1) return Math.round(utilization * 100);
  return Math.max(0, Math.round(utilization));
}

function buildUsageSnapshot(data = null, now = Date.now()) {
  if (!data || typeof data !== 'object') return null;

  return {
    sourceVersion: 1,
    fetchedAt: new Date(now).toISOString(),
    fiveHourPercent: normalizeUtilization(data.five_hour?.utilization),
    weekPercent: normalizeUtilization(data.seven_day?.utilization)
  };
}

function writeUsageCache(status, data = null, { cachePath = getUsageCachePath(), now = Date.now() } = {}) {
  const tmpFile = `${cachePath}.${process.pid}.${now}.${Math.random().toString(16).slice(2)}.tmp`;
  const snapshot = status === 'available' ? buildUsageSnapshot(data, now) : null;

  try {
    fs.writeFileSync(
      tmpFile,
      JSON.stringify({
        timestamp: now,
        status,
        data,
        snapshot
      })
    );
    fs.renameSync(tmpFile, cachePath);
  } catch {
    try { fs.unlinkSync(tmpFile); } catch {}
  }
}

function readQuotaEligibilityCache(cachePath = getQuotaEligibilityCachePath()) {
  try {
    if (!fs.existsSync(cachePath)) return null;
    const parsed = JSON.parse(fs.readFileSync(cachePath, 'utf8'));
    if (parsed && typeof parsed === 'object' && typeof parsed.eligible === 'boolean') {
      return parsed;
    }
  } catch {}
  return null;
}

function writeQuotaEligibilityCache(result, { cachePath = getQuotaEligibilityCachePath(), now = Date.now() } = {}) {
  if (!result || typeof result.eligible !== 'boolean') return;

  const tmpFile = `${cachePath}.${process.pid}.${now}.${Math.random().toString(16).slice(2)}.tmp`;
  try {
    fs.writeFileSync(
      tmpFile,
      JSON.stringify({
        timestamp: now,
        eligible: result.eligible,
        note: result.note || null
      })
    );
    fs.renameSync(tmpFile, cachePath);
  } catch {
    try { fs.unlinkSync(tmpFile); } catch {}
  }
}

function hasProviderRuntimeOverride(envObj = process.env) {
  return ['OPENAI_API_KEY', 'CODEX_ACCESS_TOKEN', 'OPENAI_BASE_URL']
    .some((key) => typeof envObj?.[key] === 'string' && envObj[key].trim() !== '');
}

function readCodexCredentials({
  homedir = os.homedir(),
  envObj = process.env
} = {}) {
  try {
    const codexHome = envObj.CODEX_HOME || path.join(homedir, '.codex');
    const credentialsPath = path.join(codexHome, 'auth.json');
    const parsed = JSON.parse(fs.readFileSync(credentialsPath, 'utf8'));
    return parsed && typeof parsed === 'object' ? parsed : null;
  } catch {
    return null;
  }
}

function getCodexAccessTokenFromCredentials(credentials) {
  return credentials?.tokens?.access_token
    || credentials?.accessToken
    || credentials?.access_token
    || null;
}

function hasSupportedCodexSubscription(credentials) {
  return Boolean(getCodexAccessTokenFromCredentials(credentials));
}

function resolveQuotaDisplayEligibility(options = {}) {
  if (hasProviderRuntimeOverride(options.env)) {
    return { eligible: false, note: 'provider-override', accessToken: null };
  }

  const explicitAccessToken = typeof options.accessToken === 'string' && options.accessToken.trim() !== '';
  const explicitCredentials = Object.prototype.hasOwnProperty.call(options, 'credentials');

  if (options.useCache && !explicitAccessToken && !explicitCredentials) {
    const cached = readQuotaEligibilityCache(options.eligibilityCachePath);
    if (isUsageCacheFresh(cached, options.eligibilityCacheTtlMs || DEFAULT_ELIGIBILITY_CACHE_TTL_MS, options.now)) {
      return { eligible: cached.eligible, note: cached.note || 'cached', accessToken: null };
    }
  }

  const credentials = explicitCredentials ? options.credentials : readCodexCredentials(options);

  let result;
  if (explicitAccessToken) {
    result = { eligible: false, note: 'codex-usage-api-unavailable', accessToken: null };
  } else {
    const accessToken = getCodexAccessTokenFromCredentials(credentials);
    if (!accessToken) {
      result = { eligible: false, note: 'missing-credentials', accessToken: null };
    } else if (!hasSupportedCodexSubscription(credentials)) {
      result = { eligible: false, note: 'non-subscription-auth', accessToken: null };
    } else {
      result = { eligible: false, note: 'codex-usage-api-unavailable', accessToken: null };
    }
  }

  if (options.useCache && !explicitAccessToken && !explicitCredentials) {
    writeQuotaEligibilityCache(result, {
      cachePath: options.eligibilityCachePath,
      now: options.now
    });
  }

  return result;
}

function getCodexAccessToken(options = {}) {
  return resolveQuotaDisplayEligibility(options).accessToken;
}

async function fetchUsageLimits(options = {}) {
  return {
    ok: false,
    cacheStatus: 'unavailable',
    note: 'codex-usage-api-unavailable',
    data: null
  };
}

async function refreshUsageCache(options = {}) {
  const result = await fetchUsageLimits(options);
  writeUsageCache(result.cacheStatus, result.data, options);

  return {
    ...result,
    cache: readUsageCache(options.cachePath)
  };
}

module.exports = {
  DEFAULT_CACHE_TTL_MS,
  DEFAULT_FETCH_TIMEOUT_MS,
  DEFAULT_ELIGIBILITY_CACHE_TTL_MS,
  getUsageCachePath,
  getQuotaEligibilityCachePath,
  readUsageCache,
  readQuotaEligibilityCache,
  getCacheAgeMs,
  isUsageCacheFresh,
  buildUsageSnapshot,
  writeUsageCache,
  writeQuotaEligibilityCache,
  hasProviderRuntimeOverride,
  readCodexCredentials,
  hasSupportedCodexSubscription,
  resolveQuotaDisplayEligibility,
  getCodexAccessToken,
  fetchUsageLimits,
  refreshUsageCache,
  normalizeUtilization
};
