// Presentation contract fixture only; never claims an actual transport failure.
import { createMenu } from '../menu.mjs';

export function testNetworkNotice() {
    const menu = createMenu(document.querySelector('#canvas'));
    const notice = document.querySelector('#connection-notice');
    const check = (ok, message) => { if (!ok) throw Error(message); };
    menu.report({ network: 'reconnecting' });
    check(!notice.hidden && notice.textContent.includes('existing session'), 'reconnect absent');
    menu.report({ network: 'server secret' });
    check(!notice.hidden && !notice.textContent.includes('secret'), 'raw backend code leaked');
    menu.report({ network: 'connected' });
    check(notice.hidden, 'transport recovery retained trouble notice');
    menu.report({ network: 'closed' });
    check(!notice.hidden && notice.textContent.includes('local match'), 'closed recovery absent');
    menu.report({ state: 'failed' });
    check(notice.hidden && document.querySelector('#canvas').inert, 'terminal fault retained competing notice/input');
    menu.report({ network: 'reconnecting' });
    check(notice.hidden, 'late transport event overrode terminal failure');
    return 'PASS: reconnect/unknown/recovered/closed/terminal precedence; presentation fixture, not network acceptance';
}
