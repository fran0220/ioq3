// SPDX-License-Identifier: GPL-2.0-or-later
// Admission is a reservation, not an engine connection. Session capabilities
// are deliberately never requested or stored by this view.
export function createLobby(og) {
    const status = document.querySelector('#lobby-status');
    const controls = document.querySelector('#lobby-controls');
    const rooms = document.querySelector('#lobby-rooms');
    const api = og?.native;
    const supported = ['list', 'create', 'join', 'leave', 'close'].every(name => typeof api?.[name] === 'function');
    let current = null, busy = false, visible = false, stopped = false, timer;
    const describe = () => current ? `Reserved room ${current.code} · ${current.players}/${current.capacity} members. Engine entry unavailable until trusted session lifecycle is connected.` : 'Choose a room or create one. Membership is a reservation, not an active match.';
    function enable() {
        for (const button of controls.querySelectorAll('button')) button.disabled = busy || button.dataset.full === 'true' || (rooms.contains(button) && !!current);
        document.querySelector('#lobby-create').disabled = busy || !!current;
        document.querySelector('#lobby-leave').disabled = busy || !current;
        document.querySelector('#lobby-join button').disabled = busy || !!current;
    }
    function schedule() {
        clearTimeout(timer);
        if (!stopped && (visible || current)) timer = setTimeout(refresh, 20000);
    }
    async function run(operation) {
        if (busy || stopped || !supported) return;
        busy = true; enable();
        try { await operation(); return true; }
        catch {
            // SDK errors are plain strings, not a stable typed error contract.
            // Do not render unknown backend payloads, tokens or claimed success.
            status.textContent = 'Native admission failed or is unavailable for this release. No connection is claimed. Refresh to reconcile a timed-out request before retrying.';
        } finally { busy = false; enable(); schedule(); }
    }
    async function refresh() {
        await run(async () => {
            const result = await api.list();
            rooms.replaceChildren();
            if (current) {
                const updated = result.rooms.find(room => room.roomId === current.roomId);
                if (updated) current = updated;
                else { current = null; status.textContent = 'Reservation expired or room closed. Choose a room again.'; }
            }
            for (const room of result.rooms) {
                const row = document.createElement('div');
                const label = document.createElement('span');
                label.textContent = `${room.code} · ${room.players}/${room.capacity} members${room.listed ? '' : ' · Unlisted'}`;
                const join = document.createElement('button'); join.textContent = 'Reserve seat';
                join.dataset.full = String(room.players >= room.capacity);
                join.addEventListener('click', () => reserve(() => api.join(room.code)));
                row.append(label, join); rooms.append(row);
            }
            if (!result.rooms.length) rooms.textContent = 'No visible rooms.';
            status.textContent = `${describe()} ${result.availableSlots} room slots available.`;
        });
    }
    async function reserve(operation) {
        const ok = await run(async () => { current = await operation(); status.textContent = describe(); });
        // Reconcile server ownership/listing; list also extends the reservation.
        if (ok) await refresh();
    }
    document.querySelector('#lobby-refresh').addEventListener('click', refresh);
    document.querySelector('#lobby-create').addEventListener('click', () => reserve(() => api.create({ listed: document.querySelector('#lobby-listed').checked })));
    document.querySelector('#lobby-join').addEventListener('submit', event => {
        event.preventDefault();
        const code = document.querySelector('#lobby-code').value;
        if (!/^[A-F0-9]{8}$/.test(code) || current) return;
        void reserve(() => api.join(code));
    });
    document.querySelector('#lobby-leave').addEventListener('click', () => run(async () => {
        if (!current) return;
        const result = await api.leave(current.roomId);
        if (result.left !== true) throw new Error('No leave confirmation');
        current = null; status.textContent = 'Reservation released. This does not assert transport teardown.';
    }));
    controls.hidden = !supported;
    enable();
    return {
        show(value) { visible = value; if (visible && supported) void refresh(); else schedule(); },
        stop() { stopped = true; clearTimeout(timer); },
    };
}
