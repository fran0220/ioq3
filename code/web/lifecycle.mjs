// SPDX-License-Identifier: GPL-2.0-or-later
// A room reservation outlives an engine document. Capabilities never do.
import { displayArguments, displayPresets } from './display.mjs';
export function createLifecycle({ native, mount, report = () => {}, sleep = ms => new Promise(r => setTimeout(r, ms)) }) {
    let current = null, generation = 0, transition = Promise.resolve(), acquisition = Promise.resolve();
    let busy = false;
    const alive = entry => current === entry && !entry.dead;
    const emit = (entry, update) => { if (alive(entry)) report(update); };
    async function dispose() {
        const old = current;
        if (!old) return;
        old.dead = true;
        current = null;
        // remove() must destroy the document even if its graceful cleanup fails.
        await old.frame.remove();
    }
    function replace(roomId = null, displayPreview = null) {
        displayArguments(displayPreview);
        if (busy) return Promise.reject(new Error('An engine transition is already running.'));
        busy = true;
        const work = transition.then(async () => {
            await dispose();
            const entry = { generation: ++generation, roomId, dead: false, requested: false, frame: null };
            current = entry;
            const boot = Object.freeze({
                displayPreview,
                report(update) {
                    // Only finite, public lifecycle states cross this boundary.
                    if (['loading', 'starting', 'ready', 'failed'].includes(update?.state)) {
                        emit(entry, { state: update.state, online: !!roomId });
                    }
                    if (['connecting', 'reconnecting', 'ready', 'failed'].includes(update?.network)) {
                        emit(entry, { network: update.network === 'ready' ? 'connected' : update.network });
                    }
                    const d = update?.display;
                    if (d && (d.preset === null || Object.hasOwn(displayPresets, d.preset))) {
                        const display = { preset: d.preset, preview: !!d.preview };
                        for (const key of ['width', 'height', 'picmip']) if (Number.isFinite(d[key])) display[key] = d[key];
                        emit(entry, { display });
                    }
                },
                async getSession() {
                    if (!alive(entry)) throw new Error('Engine was replaced.');
                    if (!roomId) return null;
                    if (entry.requested) throw new Error('Session already requested by this engine.');
                    entry.requested = true;
                    // A removed child's pending request cannot race the next child.
                    const task = acquisition.then(async () => {
                        for (let attempt = 0; attempt < 4; attempt++) {
                            if (!alive(entry)) throw new Error('Engine was replaced.');
                            emit(entry, { network: 'admitting' });
                            let session;
                            try { session = await native.getSession(roomId); }
                            catch (error) {
                                // Retry only the documented server-detach race. A timeout
                                // or any other unknown result must never repeat admission.
                                if (attempt === 3 || !String(error).includes('close active transport before replacing session')) {
                                    throw new Error('Session unavailable. Refresh the room or reload this release.');
                                }
                                await sleep(250 * (attempt + 1));
                                continue;
                            }
                            if (!alive(entry)) throw new Error('Engine was replaced.');
                            return session;
                        }
                    });
                    acquisition = task.catch(() => {});
                    return task;
                },
            });
            try {
                entry.frame = await mount(boot);
                emit(entry, { state: 'loading', online: !!roomId });
            } catch {
                entry.dead = true;
                current = null;
                report({ state: 'failed', online: !!roomId });
                throw new Error('Engine document could not be started.');
            }
        });
        transition = work.catch(() => {});
        return work.finally(() => { busy = false; });
    }
    return {
        replace,
        async stop() {
            if (busy) throw new Error('An engine transition is already running.');
            busy = true;
            try { await transition; await dispose(); report({ state: 'closed', network: 'closed' }); }
            finally { busy = false; }
        },
        isCurrent(boot) { return !!current && !current.dead && current.frame?.boot === boot; },
    };
}
