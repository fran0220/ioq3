// Test-server route only. Never copy to production. Actual compiled engine, no mocks.
import factory from '../ioquake3.js';
export default async options => {
    // Bounded actual engine output for package/binding integration checks.
    // This test-only wrapper never changes game state or ships in a release.
    const output = [];
    const capture = channel => text => {
        output.push(String(text));
        if (output.length > 4096) output.shift();
        options[channel]?.(text);
    };
    const module = await factory({ ...options, print: capture('print'), printErr: capture('printErr') });
    if (module._OG_WebUIState() !== 0 || !Number.isNaN(module._OG_WebSetting(0))
        || module._OG_WebSetSetting(0, 0.5) !== 0 || module._OG_WebMenu(1) !== 0
        || module._OG_WebTextureFilter(0) !== -2 || module._OG_WebBind(0, -1, 105, 0) !== 0
        || module._OG_WebName(0, 0) !== -1) {
        throw new Error('UI bridge accepted pre-initialization access');
    }
    window.testEngine = module;
    window.testEngineOutput = output;
    return module;
};
