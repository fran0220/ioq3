// SPDX-License-Identifier: GPL-2.0-or-later
// Local DOM contract fixture only. This is NOT a production admission test.
import { createLobby } from '../lobby.mjs';

export async function testLobby() {
    const check = (condition, message) => { if (!condition) throw Error(message); };
    const settle = () => new Promise(resolve => setTimeout(resolve, 0));
    const calls = [];
    const room = { roomId: 'fixture-room', code: 'AB12CD34', players: 1, capacity: 4, listed: false, owner: true };
    const full = { roomId: 'fixture-full', code: '1234ABCD', players: 4, capacity: 4, listed: true, owner: false };
    let rejected = false;
    const lobby = createLobby({ native: {
        list: async () => { calls.push(['list']); if (rejected) throw Error('secret must never render'); return { rooms: [room, full], availableSlots: 1 }; },
        create: async opts => { calls.push(['create', opts]); return room; },
        join: async code => { calls.push(['join', code]); return { ...room, owner: false }; },
        leave: async id => { calls.push(['leave', id]); return { left: true }; },
        close: async id => { calls.push(['close', id]); return { closed: true }; },
        getSession: async () => { throw Error('lobby must not mint session credentials'); },
    } });
    try {
        lobby.show(true); await settle();
        check(document.querySelectorAll('#lobby-rooms button')[1].disabled, 'full room button enabled');
        document.querySelector('#lobby-listed').checked = false;
        document.querySelector('#lobby-create').click(); await settle();
        check(calls.some(([name, opts]) => name === 'create' && opts.listed === false), 'visibility not sent');
        check(lobby.reservation() === 'fixture-room', 'reservation not retained in memory');
        check(document.querySelector('#lobby-enter').disabled, 'reservation falsely enabled engine entry');
        check(document.querySelector('#lobby-create').disabled, 'duplicate reservation enabled');
        check(!document.querySelector('#lobby-close').disabled, 'owner close disabled');
        document.querySelector('#lobby-close').click(); await settle();
        check(lobby.reservation() === null, 'closed reservation retained');
        const form = document.querySelector('#lobby-join');
        document.querySelector('#lobby-code').value = 'ab12cd34';
        form.dispatchEvent(new Event('submit', { cancelable: true })); await settle();
        check(!calls.some(([name]) => name === 'join'), 'lowercase code accepted');
        document.querySelector('#lobby-code').value = 'AB12CD34';
        form.dispatchEvent(new Event('submit', { cancelable: true })); await settle();
        check(calls.some(([name, code]) => name === 'join' && code === 'AB12CD34'), 'valid join absent');
        // The subsequent list is authoritative for owner status.
        document.querySelector('#lobby-leave').click(); await settle();
        check(calls.some(([name, id]) => name === 'leave' && id === 'fixture-room'), 'leave not scoped to reservation');
        rejected = true;
        document.querySelector('#lobby-refresh').click(); await settle();
        check(document.querySelector('#lobby-status').textContent.includes('No connection is claimed'), 'failure falsely successful');
        check(!document.body.textContent.includes('secret must never render'), 'raw error disclosed');
        return 'PASS: DOM admission fixture list/full/create visibility/join validation/owner close/leave/failure/no false connection';
    } finally { lobby.stop(); }
}
