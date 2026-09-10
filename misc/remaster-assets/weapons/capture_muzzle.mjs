// Slow-time visual inspection only; normal-time gameplay checks are separate.
import { writeFileSync } from 'node:fs';
import { connect, sleep } from '../../tests/gameplay/browser.mjs';
const [url, output] = process.argv.slice(2);
const browser = await connect(url);
try {
    await browser.command('bind f +attack');
    await browser.command('timescale 0.1');
    await browser.key('f', true);
    for (let frame = 0; frame < 12; frame++) {
        await sleep(70);
        const shot = await browser.send('Page.captureScreenshot', { format: 'jpeg', quality: 85 });
        writeFileSync(output + '.' + String(frame).padStart(2, '0') + '.jpg', Buffer.from(shot.data, 'base64'));
    }
    console.log('Captured real slow-time muzzle sequence: ' + output);
} finally {
    await browser.key('f', false);
    await browser.command('timescale 1');
    await browser.close();
}
