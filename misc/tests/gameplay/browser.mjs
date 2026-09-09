// SPDX-License-Identifier: GPL-2.0-or-later
// Real Chromium CDP input, never dispatchEvent or writes to game state.
import { appendFileSync, writeFileSync } from 'node:fs';

export const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

export async function connect(url, journal) {
    const socket = new WebSocket(url);
    await new Promise((resolve, reject) => {
        socket.onopen = resolve;
        socket.onerror = reject;
    });
    let sequence = 0;
    let sessionId;
    const pending = new Map();
    const messages = [];
    const record = (kind, data) => {
        const entry = { at: new Date().toISOString(), kind, ...data };
        if (journal) appendFileSync(journal, JSON.stringify(entry) + '\n');
        return entry;
    };
    socket.onmessage = event => {
        const message = JSON.parse(event.data);
        if (message.id) {
            const request = pending.get(message.id);
            if (!request) return;
            pending.delete(message.id);
            clearTimeout(request.timer);
            if (message.error) request.reject(new Error(JSON.stringify(message.error)));
            else request.resolve(message.result);
        } else if (message.method === 'Runtime.consoleAPICalled') {
            const text = message.params.args.map(arg => arg.value ?? arg.description).join(' ');
            messages.push(text);
            record('console', { text });
        } else if (message.method === 'Runtime.exceptionThrown') {
            record('exception', message.params);
        }
    };
    const send = (method, params = {}, root = false) => new Promise((resolve, reject) => {
        const id = ++sequence;
        const timer = setTimeout(() => {
            pending.delete(id);
            reject(new Error(`CDP timeout: ${method}`));
        }, 30000);
        pending.set(id, { resolve, reject, timer });
        socket.send(JSON.stringify({ id, method, params, ...(!root && sessionId ? { sessionId } : {}) }));
    });
    const { targetInfos } = await send('Target.getTargets');
    const target = targetInfos.find(target => target.type === 'page' && /^https?:/.test(target.url));
    if (!target) throw new Error('Open the test page in agent-browser first');
    ({ sessionId } = await send('Target.attachToTarget', { targetId: target.targetId, flatten: true }, true));
    await send('Runtime.enable');
    await send('Page.enable');
    const evaluate = async expression => {
        const response = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
        if (response.exceptionDetails) throw new Error(JSON.stringify(response.exceptionDetails));
        return response.result.value;
    };
    const keyInfo = key => {
        const special = {
            Backquote: ['`', 192], Enter: ['Enter', 13], Escape: ['Escape', 27],
            Space: [' ', 32], ArrowUp: ['ArrowUp', 38], ArrowDown: ['ArrowDown', 40],
            ArrowLeft: ['ArrowLeft', 37], ArrowRight: ['ArrowRight', 39],
            PageDown: ['PageDown', 34], Delete: ['Delete', 46],
        };
        if (special[key]) return { key: special[key][0], code: key, windowsVirtualKeyCode: special[key][1] };
        if (/^[a-z]$/.test(key)) return { key, code: `Key${key.toUpperCase()}`, windowsVirtualKeyCode: key.toUpperCase().charCodeAt(0) };
        throw new Error(`Unsupported key ${key}`);
    };
    const key = async (name, down) => {
        record('input', { key: name, down });
        await send('Input.dispatchKeyEvent', { type: down ? 'keyDown' : 'keyUp', ...keyInfo(name) });
    };
    const press = async name => { await key(name, true); await sleep(60); await key(name, false); };
    const type = async text => {
        record('input', { text });
        for (const char of text) {
            // SDL TEXTINPUT is produced by Chromium's char event, not a DOM edit.
            await send('Input.dispatchKeyEvent', { type: 'char', text: char });
        }
    };
    const command = async text => {
        record('command', { text });
        const catcher = await evaluate('window.readEngine?.().keyCatcher ?? null');
        if (catcher === null || !(catcher & 1)) await press('Backquote');
        if (catcher !== null) await waitFor(() => evaluate('readEngine().keyCatcher'), value => !!(value & 1));
        else await sleep(150);
        // Quake's active-game console otherwise treats unprefixed text as chat.
        const firstMessage = messages.length;
        await type('/' + text);
        await press('Enter');
        await waitFor(async () => messages.slice(firstMessage), lines => lines.some(line => line.includes(']/' + text)));
        const after = await evaluate('window.readEngine?.().keyCatcher ?? null');
        if (after === null || (after & 1)) await press('Backquote');
        if (after !== null) await waitFor(() => evaluate('readEngine().keyCatcher'), value => !(value & 1));
        else await sleep(150);
    };
    const waitFor = async (read, predicate, timeout = 15000) => {
        const end = Date.now() + timeout;
        let value;
        do {
            value = await read();
            if (predicate(value)) return value;
            await sleep(100);
        } while (Date.now() < end);
        throw new Error(`Condition timed out; last value: ${JSON.stringify(value)}`);
    };
    return {
        send, evaluate, key, press, type, command, waitFor, messages, record,
        async click(selector) {
            const { x, y } = await evaluate(`(() => {
                const r = document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect();
                return {x:r.x+r.width/2,y:r.y+r.height/2};
            })()`);
            record('input', { click: selector, x, y });
            await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
            await send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
            await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
        },
        async screenshot(path) {
            const { data } = await send('Page.captureScreenshot', { format: 'jpeg', quality: 80 });
            writeFileSync(path, Buffer.from(data, 'base64'));
            record('screenshot', { path });
        },
        async close() {
            await send('Target.detachFromTarget', { sessionId }, true);
            socket.close();
        },
    };
}
