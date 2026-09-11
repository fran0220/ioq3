import test from 'node:test';
import assert from 'node:assert/strict';
import { networkNotice } from './menu.mjs';

test('transport notices never promote admission or transport readiness to a match', () => {
    assert.match(networkNotice('admitting'), /No transport connection/);
    assert.match(networkNotice('connecting'), /handshake is still required/);
    assert.equal(networkNotice('ready'), '');
    assert.equal(networkNotice('connected'), '');
    assert.match(networkNotice('reconnecting'), /existing session/);
    assert.match(networkNotice('failed'), /fresh engine/);
    assert.match(networkNotice('closed'), /local match/);
});

test('unknown network codes and backend text cannot become UI notices', () => {
    for (const state of [undefined, 'constructor', '__proto__', 'secret session token', '<img onerror=1>']) {
        assert.equal(networkNotice(state), undefined);
    }
});
