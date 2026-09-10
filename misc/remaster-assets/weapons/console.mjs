// Real browser console input using the existing gameplay CDP harness.
// This never writes player state. Commands require a local devmap for cheats.
import { connect, sleep } from '../../tests/gameplay/browser.mjs';
const [url, ...commands] = process.argv.slice(2);
const browser = await connect(url);
try {
    for (const command of commands) await browser.command(command);
    await sleep(700);
    console.log(JSON.stringify(await browser.evaluate('readEngine()'), null, 2));
} finally {
    browser.close();
}
