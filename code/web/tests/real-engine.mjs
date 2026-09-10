// Test-server route only. Never copy to production. Actual compiled engine, no mocks.
import factory from '../ioquake3.js';
export default async options => {
    const module = await factory(options);
    if (module._OG_WebUIState() !== 0 || !Number.isNaN(module._OG_WebSetting(0))
        || module._OG_WebSetSetting(0, 0.5) !== 0 || module._OG_WebMenu(1) !== 0
        || module._OG_WebTextureFilter(0) !== -2 || module._OG_WebBind(0, -1, 105, 0) !== 0
        || module._OG_WebName(0, 0) !== -1) {
        throw new Error('UI bridge accepted pre-initialization access');
    }
    window.testEngine = module;
    return module;
};
