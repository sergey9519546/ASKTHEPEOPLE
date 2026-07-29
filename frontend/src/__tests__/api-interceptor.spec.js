import { describe, it, expect } from 'vitest';
import service from '../api/index.js';

// Exercise the response success handler registered in api/index.js directly.
// Axios stores response interceptors on `service.interceptors.response.handlers`
// as { fulfilled, rejected, ... }. Invoking `fulfilled` with a synthetic response
// keeps the test isolated from network/HTTP concerns (mirroring how toast.spec.js
// imports and invokes the unit under test).
//
// Spec (`docs/superpowers/specs/2026-03-24-production-crash-remediation-design.md`,
// Layer 1): the success handler must normalize a null / non-object `response.data`
// to { success: false, error: 'empty_response' } before any view consumes it. In
// the merged interceptor that normalized object is then routed through the
// existing `if (!res.success) reject(...)` branch, so callers observe it as a
// rejected promise whose error message is 'empty_response'. Either way the
// *value* the spec requires — success:false + error:'empty_response' — is what
// the interceptor produces, which is what these tests pin down.
function getResponseFulfilled() {
  const handlers = service.interceptors.response.handlers || [];
  const handler = handlers.find(h => h && typeof h.fulfilled === 'function');
  if (!handler) {
    throw new Error('no response success interceptor registered on the axios instance');
  }
  return handler.fulfilled;
}

// When the safety-net guard is present, a null/undefined/non-object body is
// normalized to { success: false, error: 'empty_response' }. Because the merged
// interceptor then rejects on `!res.success`, callers see a rejection. This
// helper asserts the normalized payload is reachable as that error value,
// regardless of whether it surfaces as a resolve or a reject.
async function expectEmptyResponse(payload) {
  const fulfilled = getResponseFulfilled();
  try {
    const res = await fulfilled({ data: payload, status: 200, statusText: 'OK', headers: {}, config: {} });
    // If it resolves, the normalized object itself must carry the marker.
    expect(res).toBeDefined();
    expect(res.success).toBe(false);
    expect(res.error).toBe('empty_response');
    return;
  } catch (err) {
    // If it rejects, the rejection must carry the 'empty_response' marker so the
    // normalized value is observable downstream.
    expect(err).toBeInstanceOf(Error);
    expect(err.message).toBe('empty_response');
  }
}

describe('API response interceptor normalization (null / non-object safety net)', () => {
  it('normalizes response.data === null to { success: false, error: "empty_response" }', async () => {
    await expectEmptyResponse(null);
  });

  it('normalizes response.data === undefined to { success: false, error: "empty_response" }', async () => {
    await expectEmptyResponse(undefined);
  });

  it('normalizes a non-object primitive (plain string) to { success: false, error: "empty_response" }', async () => {
    // e.g. an HTML error page returned by a proxy, or a bare "ok" string.
    await expectEmptyResponse('ok');
  });

  it('does not reject a well-formed success payload', async () => {
    const fulfilled = getResponseFulfilled();

    const payload = { success: true, content: 'hello', data: { x: 1 } };
    const res = await fulfilled({ data: payload, status: 200, statusText: 'OK', headers: {}, config: {} });

    expect(res.success).toBe(true);
    expect(res.content).toBe('hello');
  });

  it('normalizes a null content field on an otherwise-valid payload to ""', async () => {
    // Some models (e.g. stepfun) return a null content field; the interceptor
    // must coerce it to an empty string so views can render it safely.
    const fulfilled = getResponseFulfilled();

    const res = await fulfilled({
      data: { success: true, content: null },
      status: 200,
      statusText: 'OK',
      headers: {},
      config: {},
    });

    expect(res.success).toBe(true);
    expect(res.content).toBe('');
  });
});
