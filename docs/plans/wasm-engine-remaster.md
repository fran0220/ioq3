# PC 浏览器 ioq3 → WASM 完整重制：引擎工作包计划

状态：可实施规划，未开始重制、发布或付费生成。仅 PC，不含移动端、触控或移动端性能适配。

集成说明：以[主计划](../remaster-plan.md)的范围、阶段、统一性能预算和授权记录为准。本文 WebRTC 优先、144 FPS 等为工作包候选；主计划要求先比较传输实验，高刷暂定120 FPS，不将候选直接视为已决定或已达标。

检查日期：2026-09-09。仓库：fran0220/ioq3；基线：[bf98709](https://github.com/fran0220/ioq3/commit/bf98709c9391c907e0c83d0b522ceeda379c40e0)。本 orb 的默认分支 checkout 不代表源线程未推送的本地 main；实施前由主线程核对差异。本工作包仅拥有本文档，其余路径是未来实施的所有权建议，不表示本次已修改。

## 1. 结论与产品边界

**不用 Three.js 可行，推荐保留并升级 `renderergl2`。** ioq3 主体为 C99；使用 Emscripten 编译为 WASM，保留原引擎的游戏循环、客户端预测、服务端权威模拟、碰撞与 Bot。WASM 是执行目标，不是渲染 API：最终绘图仍由 SDL/GLES 适配调用浏览器 WebGL2。没有必要为了使用 WASM 把 C 改写为 C++。

这是完整重制，不是将原游戏套一个网页：人物、武器、环境、材质、动画、特效、声音、HUD、浏览器操作体验全部重新制作；但战斗规则与游戏循环保持参考版本。第一张图、单武器和单 Bot 是架构验收切片，不是最终缩减范围。最终内容清单必须覆盖选定原版范围的全部模式、武器、道具、地图、角色、Bot 层级和单人进度流程。

“玩法完全复刻”与“手感重制”的边界：允许改输入采样延迟、鼠标设置、视效/音效反馈、枪模动作、镜头表现和 UI；不暗改加速度、摩擦、空中控制、跳跃、碰撞盒、射速、伤害、弹道、拾取/重生时间或服务端命中判定。任何改变这些参数的调试都属于玩法变更，必须单独批准，不能混在表现重制中。

暂按 baseq3 规则作为参考起点。P0 必须确认 Team Arena/missionpack 是否属于最终复刻范围，并冻结准确版本、模式与内容清单；不以技术默认值替用户永久删减扩展内容。地图原布局、角色形象、声音、名称和商标的复制仍有授权问题：若不能获得需要的权利，可用原创资产制作技术验证与同规则新内容，但不能声称它完成了原商业内容的完整复刻。

## 2. 当前能力核实：实现存在不等于浏览器已验收

以下为实际代码检查，非运行结果。`command -v emcc` 未找到编译器；常见 emsdk 路径不存在；`build-orb/CMakeCache.txt` 是 `/usr/bin/cc` 的 Debug 原生构建，GL1/GL2 均开启。本次没有安装 SDK、执行 Web 编译或运行商业素材。因此不能宣称现有浏览器版本可以玩、画质正确或达到性能目标。`git ls-files '*.pk3' '*.bsp' '*.aas'` 无输出，仓库没有受 Git 跟踪的这些游戏数据；Web 清单中的文件名不是资产或授权证明。

| 范围 | 已确认的代码事实 | 重制缺口 / 验证要求 |
| --- | --- | --- |
| 构建 | `.github/workflows/build.yml:137–157` 固定 Emscripten 3.1.58，执行配置、编译、上传 | CI 没有浏览器运行验收；固定 SDK，首次复现日志及产物后再谈升级 |
| Web 目标 | `cmake/platforms/emscripten.cmake`：JS/WASM、256 MB 内存、5 MB 栈、WebGL 1–2；关闭独立 server、GL1、动态 renderer、原生 game libraries、引擎 HTTP 下载 | 不是生产发布包；内存、资源加载和错误恢复未按重制内容设计；建议发布目标明确 WebGL2-only，不为 PC 产品维护 WebGL1 画质分支 |
| 启动 | `code/web/client.html.in:25–84` 使用相对资源路径、fetch→MEMFS、URL 参数、`net_enabled 0`、`sv_pure 0` | 缺点击开始/音频授权、可靠失败状态、进度、持久化、平台生命周期；发布不能沿用任意 URL 命令透传及 pure 关闭的 demo 默认值 |
| 循环与 QVM | `code/sys/sys_main.c:892` 用 `emscripten_set_main_loop(Com_Frame, 0, 1)`；`cmake/basegame.cmake` 编译 game/cgame/ui QVM；`vm.c:656–674` 无对应 JIT 时用解释器，`q_platform.h` 的 WASM 分支未定义 `HAVE_VM_COMPILED` | 引擎 WASM 不代表 game/cgame 已直接编译成 WASM；QVM 解释开销、Bot 帧开销须剖析；不能复用 x86 JIT |
| WebGL2 | `code/sdl/sdl_glimp.c:535–590` 明确请求 GLES3 上下文；`tr_glsl.c:246–320` 有 GLSL ES 300 转换；`cl_main.c` 默认 opengl2；Web 静态链接 renderer | 有入口，不是现代 WebGL2 后端已完整 |
| 后处理的实际阻断 | `code/renderergl2/tr_extensions.c:74–165` 的 GLES 分支提前 `goto done`；FBO、浮点纹理标志赋值仅在后面的桌面分支；`tr_fbo.c:258` 在 FBO 未开启时返回，`tr_backend.c:1549` 跳过后处理 | 当前 GLES 路径不能因 `r_hdr=1` 就获得桌面 HDR/FBO 链。要补 WebGL2 核心函数加载、能力探测、格式、深度采样、resolve、shader 兼容及降级；不能只把标志设 true |
| 材质 | `tr_shader.c`、`glsl/lightall_fp.glsl:390–455` 有 normal/specular、PBR、环境反射；`tr_init.c:1317` 的 PBR 默认关闭 | PBR 为实验路径；红通道 gloss、绿通道 metallic，粗糙度解释取决于宏，不等同 glTF ORM；现有颜色平方近似也不是完整标准色彩管理 |
| 文档与渲染限制 | `docs/opengl2-readme.md` 明确提醒 GLES HDR/太阳阴影限制、PBR 实验性质、SSAO 性能/瑕疵及动态光阴影问题 | 不照抄桌面 feature list 当作 Web 承诺；每个 pass 需浏览器能力及画面证据 |
| 模型 | `tr_model.c:184–201` 注册 IQM/MDR/MD3；`tr_surface.c:778–845` MD3 顶点插值；`tr_animation.c` MDR 骨骼蒙皮；`tr_model_iqm.c` IQM CPU/VAO 骨骼路径，IQM v2 上限 128 joints | 不必自建骨骼格式；上限还受实际 uniform/GPU 能力约束；glTF 直接导入、重定向、层混合、IK、资源生产规范不是现成能力 |
| 玩家动画 | `code/cgame/cg_players.c` 读取 animation.cfg、帧号与分段 tag 连接；`cg_weapons.c` 枪模与开火表现 | renderer 会读 IQM 不意味着玩家已换成整身骨骼、上下身混合或第一人称手臂；必须改客户端表现适配 |
| 特效 | `cg_effects.c`、`cg_localents.c`、`cg_particles.c`、`cg_marks.c` 已有烟、轨迹、爆炸、碎片、贴花等 | 需重做素材、时间曲线、材质、批处理、透明排序/overdraw；没有证据表明存在完整现代 GPU 粒子作者系统 |
| 本地游戏/Bot | `cmake/client.cmake:69–79` 客户端仍链接 server 与 botlib；`game/ai_*` 是游戏侧策略，`server/sv_bot.c` 桥接 `botlib`；`be_aas_main.c:220–240` 加载 maps/*.aas | Web 禁建独立 server 不等于无本地比赛/Bot。仍需合法 BSP、AAS、botfiles、角色/武器配置；仓库没有地图编译器成品流水线可直接宣称具备 |
| 声音 | `code/client/snd_*` 有混音、空间化、WAV/Vorbis/Opus，`code/sdl/sdl_snd.c` SDL audio，`cmake/libraries/openal.cmake` 保留静态 OpenAL 路线 | Web 并非明确只用 SDL：首阶段同时核实 OpenAL 实际链接和可用性，选择/记录默认与回退；须解决用户手势、后台暂停、设备变化与声音素材重制 |
| 设置/进度 | `common.c:2922–2965` 写 binds/archived cvars；`files.c` 将配置、数据、状态分区；`q3_ui/ui_gameinfo.c` 有 g_spScores/g_spAwards/g_spVideos | Web shell 未挂载 IDBFS 或同步 IndexedDB。写 MEMFS 不是刷新后持久化；原单人进度不等于任意战斗状态快照存档 |
| PC 输入 | `sdl_input.c` 相对鼠标、键盘/文本、按钮/滚轮；`cl_input.c` 生成 usercmd | 需 Pointer Lock、焦点恢复、全屏、DPI、键位重绑和高刷新率验证；嵌入权限不能由 SDL 自动保证 |
| 联机 | `qcommon/net_ip.c` 为 UDP socket/sendto；`cl_net_chan.c`、`server/sv_net_chan.c` 等维持 Quake 协议 | 没有发现项目级 WebSocket/WebRTC 适配。浏览器不能直接连接原 UDP 服务；AI Gateway 不是多人实时传输 |

## 3. 保留 renderer 的完整技术路线

```text
浏览器 shell：加载/授权/持久化/平台生命周期/连接协商
        │ 窄边界，非每实体每帧场景镜像
        ▼
WASM ioq3：Com_Frame → client / server / botlib / QVM
        │                   └─共享 bg_* 与权威规则
        ▼
cgame：预测、HUD、视听事件、动画表现
        │ ref API（必要时版本化扩展）
        ▼
renderergl2：BSP/PVS、材质、骨骼、特效提交、光照、后处理
        ▼
SDL / Emscripten GLES 3 → WebGL2 → GPU
```

保留此路线可复用 BSP/PVS、lightmap/lightgrid、曲面、shader 脚本、模型注册、场景提交和调试命令。Three.js 同样不会代替权威逻辑、预测、碰撞或 UDP 传输；使用它还要把 BSP、材质脚本、实体/骨骼数据及资源生命周期映射到第二套场景，增加 JS/WASM 边界和同步工作。它可以用于独立美术预览工具，但不是本游戏运行时依赖。

代价是真实存在的：要维护 GLES/WebGL2 后端和老 renderer 的全局状态；WebGL2 无 compute/现代显式资源管理，不能承诺所有桌面特性照搬。采取以下完整升级顺序：

1. 明确 WebGL2 核心能力表：FBO、VAO、MRT/输出数量、深度纹理、32-bit index、纹理格式、MSAA resolve、shader 精度与骨骼 uniform 预算；对浮点颜色附件单独探测并实建 FBO 测试。区分“纹理可采样”和“可渲染到纹理”。
2. 建立线性光照、sRGB 输入/显示输出、normal/ORM 非颜色纹理、曝光、透明混合和 HDR→LDR 路径的一致规范。维护旧材质兼容层，不用自动生成法线冒充重制材质。
3. 保留 .mtr/.shader 与 IQM 运行格式；DCC 使用团队标准源格式（建议 Blender/glTF 中间交换），离线转换 IQM/贴图/材质，记录单位、坐标、切线、关节、附件和版本。此阶段不引入一个新的 glTF 运行时场景引擎。
4. 环境维持原碰撞、实体布局、PVS 和导航语义，制作高精视觉网格、LOD、lightmap/反射资源。高精装饰默认不参与碰撞；若修改结构则碰撞与 AAS 必须一起重新验证。
5. 新建客户端表现动画控制：速度/姿态驱动 locomotion，独立上身瞄准/开火，过渡、附加层、武器 socket、第一人称手臂、死亡与重生；IK 仅校正表现。root motion 不写回玩家位置，动画帧不决定开火/命中时刻。
6. 特效按原事件时刻生成，统一预算和材质，完善贴花、弹道、枪口、冲击、传送、能量与环境特效。远处 LOD 不得隐藏有战术意义的轨迹/警告。WebGL2 首选批处理/实例化可行路径，是否用 transform feedback 由性能实验决定。
7. 建立低/中/高画质配置：缺浮点颜色附件可走验证过的 LDR，基础 WebGL2 不支持则清晰报错；同样的玩家轮廓、命中和可辨识度是每档硬约束。

P2 的退出标准是用合法代表资产在目标浏览器画出可接受结果并满足预算。若功能正确但性能不足，先量化 QVM、draw call、蒙皮、纹理和透明开销，优化责任模块。若某关键画质需求确实超出 WebGL2，提交需求与数据后评估同一 ref API 下的独立 WebGPU 后端；不能在无证据时自动转 Three.js 或把本计划偷偷缩成原画面移植。

## 4. 原版逻辑保留与差分验证契约

保护区为 `code/game/bg_pmove.c`、`bg_slidemove.c`、`bg_misc.c`、`g_active.c`、`g_weapon.c`、`g_missile.c`、`g_combat.c`、`g_items.c`、`g_team.c`、`g_main.c`，以及 `code/qcommon/cm_*`、server 快照/命令/时间推进与 `cg_predict.c` 的语义。不是禁止修 bug，而是所有语义变化必须带独立规则评审与差分证据。

建立独立 native 参考构建，与 Web 使用同一参考代码、QVM、碰撞图、cvars、seed、usercmd 时序。不能要求任意 native 浮点与 WASM 自动逐 bit 等同：离散事件（命中对象、伤害、弹药、比分、道具、死亡、回合结束）必须一致；位置/速度先给出严格误差预算并记录首个分歧帧，不用大容差掩盖边缘碰撞差异。渲染随机数不得影响权威 RNG。

回归输入覆盖：30/60/144/240 Hz 呈现时的同一 usercmd 时间流；台阶临界高度、斜坡/墙角、跳台、连续跳、空中转向、火箭跳、水中移动、蹲起；每种武器的射程/弹药/冷却边界；同时拾取/死亡/得分；传送、重生、观战、CTF 等参考范围模式。另用真实鼠标在每档刷新率采样，检测 usercmd 分包方式改变的行为，不能只测理想注入输入。

不引入跟 rAF 绑定的“每帧固定移动量”，也不在重制中随意改 pmove_fixed、服务器 tick 或追帧策略。隐藏标签页时本地单机可显式暂停，远程比赛由服务器继续，恢复时重新同步；不依赖浏览器后台定时器维持权威服务端。

## 5. 运行配套不是可选尾项

### PC 输入与手感

点击开始一次用户手势触发可用的音频/Pointer Lock 流程；清楚区分请求失败、Esc 解锁、窗口失焦、菜单和重新进入。全屏走浏览器及平台允许的 API，不对抗 Esc。提供横纵灵敏度/反转/加速开关/键位冲突提示/FOV/枪模与镜头晃动强度；视觉瞄准方向必须与射击方向对应。物理按键、布局与文本输入分离，聊天不发移动命令；失焦释放全部按键。测试 Windows/macOS/Linux 的 Chrome/Edge/Firefox，macOS Safari 单独实机验收，不能以 Linux Chromium 代替。

### Bot

保留 `game/ai_*`、`botlib`、AAS 的经典策略/导航，不用 LLM 替代即时 Bot。为每张重制图产出合法匹配的 AAS 与 botfiles，锁定 q3map2/bspc 等外部工具版本和许可证，实施时另行核实其权威来源。几何换皮不应改变路线、可达性与命中；测试所有难度、武器选择、跳台、传送、拾取、组队、夺旗、死亡复活与换图。对相同 seed 做 native/Web 对比并统计 1/4/8 Bot CPU 时间、卡死与不可达节点；不以降低思考频率偷偷改变原版难度。

### 声音

保留事件触发及空间位置，重录/重制全部需要的武器、脚步、受击、环境、播报、音乐资产及权利清单。验证 SDL 混音与静态 OpenAL 的实际 Web 支持后确定一个生产默认，另一个仅在明确可验证时作回退；避免双路同时播放。定义声部优先级、响度、距离衰减、循环交叉、混音 headroom；检查左右/前后移动、遮挡策略（新增遮挡不能削掉战术信息）、32+ 并发音源、采样率变化、首次授权、暂停恢复、耳机切换和音画同步。语音聊天若纳入范围须单列浏览器麦克风许可、加密传输、静音/举报，不从存在 Opus 就推断可用。

### 设置、进度与资源

将可写 home config/state 路径显式挂载 IDBFS；启动先完成持久化恢复，再读取引擎配置。配置修改/局末里程碑后节流并串行同步，有成功/错误状态；不能依赖 beforeunload 才保存。版本化设置和进度、迁移、导入/导出、清除、配额失败、隐私模式与多标签写竞争均测试。readonly PK3 下载缓存与可写存档分开；缓存按 manifest 内容哈希，避免旧 JS/新 WASM/错 QVM 混用。

“存档”包含原版设置、键位、单人关卡成绩/奖章/解锁；不擅自增加原游戏没有的任意战斗快照或云账号系统。如最终需跨设备进度，则是额外平台数据契约，客户端上报的成绩不作为可信排行榜依据。

### 联机

最终部署独立 native dedicated server 作为权威服务端；浏览器本地 server 只负责单人/本地 Bot。保留 Quake netchan、sequence/ack、delta snapshot、reliable command、challenge、版本/pure 规则；只换传输边界。

推荐生产主路径：浏览器 WebRTC DataChannel 到专用传输网关，再以有会话隔离的 UDP 对接 native server；游戏数据使用无序、有限/零重传的数据报语义，由既有 netchan 处理其可靠消息。必须实现信令、ICE/STUN/TURN、会话生命周期、背压、MTU/分片限制、连接重建和网关定额。此网关是新工程，不假定 Origin Game 已提供。优先做容量/延迟实验再锁定实现语言与库，避免现在凭空添加依赖。

WSS→UDP 可作企业网络兼容回退/早期连通性验证，但 TCP 队头阻塞会放大丢包尾延迟，不能仅凭局域网顺畅就宣布竞技体验等价；界面显示回退与网络质量。不得把浏览器发往任意 UDP 地址的开放代理上线：目标只允许本游戏服务器，校验登录/会话票据、长度/速率、源映射与过期。网关/房间服务不能把平台密钥放进客户端。对恶意 usercmd、资源/协议版本不匹配、重放包和畸形包在服务端拒绝。

验收覆盖两台真实 PC、跨网络、直接/经 TURN/强制 WSS，RTT 20/80/150 ms、jitter 0/20 ms、丢包 0/1/3%，观测命令→权威结果→画面反馈、修正距离、P95/P99 延迟、掉线和重连；不保证把公网延迟降成零。大厅、匹配、版本管理、运营日志、反滥用、服务端容量和停服/回滚演练都在最终上线范围，具体平台接口由平台工作包负责。

## 6. 文件所有权：按模块单写，接口串行集成

下表是未来工程责任，不授权现在改动这些文件。多个工作包可并行，但任何文件同一时段只允许一个 owner。新增目录须等接口及仓库约定确定后创建。

| Owner / 工作包 | 独占修改路径 | 消费契约、不可自行修改 |
| --- | --- | --- |
| E-BUILD Web 工具链 | `cmake/platforms/emscripten.cmake`、`cmake/client.cmake`、`cmake/basegame.cmake`、`cmake/utils/qvm_tools.cmake`、相关 `cmake/libraries/*`、`.github/workflows/build.yml`、未来 `.agents/setup` 更新 | `.agents/setup` 修改前读 orb-setup；主 CMake 和共享配置经集成 owner 排队 |
| E-WEB 浏览器宿主 | `code/web/*`，未来生产 root index 生成/打包入口 | 仅调用版本化 C/JS 桥；不直接改引擎命令解析或复制游戏状态 |
| E-RENDER 渲染 | `code/renderergl2/*`、`code/sdl/sdl_glimp.c`、`sdl_gamma.c` | 不改权威碰撞/命中；`renderercommon` 公共接口走集成 owner |
| E-PRESENT 表现 | `code/cgame/cg_players.c`、`cg_weapons.c`、`cg_effects.c`、`cg_localents.c`、`cg_particles.c`、`cg_marks.c`、`cg_view.c`、`cg_event.c`、`cg_ents.c` | `cg_predict.c` 与 game 规则不归此 owner；视觉事件不能改变 shot time |
| E-UI 游戏 UI | `code/cgame/cg_draw*.c`、`cg_scoreboard.c`、`cg_info.c`，`code/q3_ui/*`，若确定扩展范围则 `code/ui/*` | 浏览器权限/加载属于 E-WEB；UI 输出配置需求给 E-STATE，避免两套设置源 |
| E-INPUT PC 输入 | `code/sdl/sdl_input.c`、`code/client/cl_input.c`、`cl_keys.c` | 不改 bg_pmove；桥/焦点协议由 E-WEB 消费 |
| E-AUDIO 音频 | `code/client/snd_*`、`qal.*`、`code/sdl/sdl_snd.c` | 构建选项由 E-BUILD，声音事件由 E-PRESENT；不各自改同一文件 |
| E-RULES 规则/回归 | `code/game/*`（不含 ai_* 与 g_bot.c）、`code/cgame/cg_predict.c`、`cg_snapshot.c`、`cg_playerstate.c`、`code/qcommon/cm_*` | 保护原语义；测试输入/参考输出的权威 owner |
| E-BOT | `code/game/ai_*`、`g_bot.c`、`code/botlib/*`、`code/server/sv_bot.c` | Bot 内容和 AAS 由内容 owner 提供；不独立改变公共规则 |
| E-NET 多人网络 | `code/qcommon/net_*`、`code/client/cl_net_chan.c`、`cl_parse.c`、`code/server/*`（除 sv_bot.c）；未来网关独立目录/仓库 | `sv_game.c` 的 syscall ABI 调整仍需集成 owner；宿主信令 JS 由 E-WEB 接单 |
| E-STATE 文件/存档 | `code/qcommon/files.c`、`code/sys/sys_unix.c` 的 home 路径相关部分 | IDBFS JS 由 E-WEB；不改 UI 进度规则；common.c 保存通知经集成 owner |
| E-INTEGRATE 跨层接口 | `code/renderercommon/*`、`code/qcommon/q_shared.h`、`qcommon.h`、`common.c`、`vm*`、`code/sys/sys_main.c`、`code/client/cl_main.c`、`cl_cgame.c`、`cl_ui.c`、game/cgame/ui 公共头及 syscall 表、主 `CMakeLists.txt` | 接口需求先写编号/数据布局/生命周期/版本兼容，再串行合入；公共头改动须重建全部 QVM/native/server |
| CONTENT 内容管线 | 未来授权资产目录、源 DCC、转换/地图编译脚本、资源 manifest、许可证清单 | 不将商业 PK3 默认加入仓库；材质/骨骼契约由 E-RENDER 与 E-PRESENT 一起冻结 |
| E-QA | 未来行为录制/差分、浏览器测试、网络压测与性能场景目录 | 验收脚本独立于实现计算期望，失败由所属 owner 修复；不代改产品文件 |

路径表中尚未列出的文件由集成 owner 先分配，不能以“相关代码”为由扩大并行写范围。所有目录通配符均排除 E-INTEGRATE 已列出的公共头和 syscall 表；这类文件始终只有集成 owner 写入。E-UI 与 E-PRESENT 对 cgame 公共头、E-RULES 与 E-NET 对 VM 系统调用的需求统一走 E-INTEGRATE。

## 7. 分阶段依赖、产物与可执行验收

所有阶段结束均提交可追溯构建标识、命令/退出码、机器/浏览器版本、场景/资产哈希、测试日志；画面相关阶段必须有实际渲染截图并人工检查。下列数字为立项预算建议，不是当前测试成绩；P0 按确定的 PC 基线冻结，未达成须解释瓶颈，不默默下调目标。

### P0 — 参考规格、合法资源与测试基线

依赖：无；owner：E-RULES + CONTENT + E-QA。

产物：参考版本和模式/武器/道具/地图/角色全量 checklist；授权/原创/待授权清单；原生参考、参考 cvars、动作轨迹和事件 golden 数据；PC 实机矩阵。建议基线为 Windows 的 Intel Iris Xe 级集显、GTX 1660 级独显及一台 Apple Silicon Mac，准确型号/驱动必须实录，不声称所有 PC 达标。

验收：`cmake -S . -B build-reference -DCMAKE_BUILD_TYPE=Release`、`cmake --build build-reference --parallel 2` 成功；使用合法测试包跑移动、战斗、结束/再开局的参考录制。每项最终内容都有权利状态与负责人；测试包含真实可加载的 BSP、实体、最小 HUD/字体/模型/声音以及对应 AAS/botfiles，不以空白 canvas 为通过。商业素材不足阻止商业内容验收，不阻止原创测试场继续开发。

### P1 — 可复现 Web 基线与生命周期

依赖：P0 测试包/参考；owner：E-BUILD + E-WEB + E-INTEGRATE。

产物：固定 Emscripten 3.1.58 的干净构建、完整 js/wasm/QVM 资源 manifest、root index 生产打包、加载/错误/重试 UI，浏览器权限与初步日志。

验收命令（SDK 安装激活后）：`emcc --version` 确认 3.1.58；`emcmake cmake -S . -B build-web -G Ninja -DCMAKE_BUILD_TYPE=Release`；`cmake --build build-web --parallel 2`。先复现现有选项，再为独立合法游戏建立命名/BUILD_STANDALONE 配置，不能与参考构建混淆。

HTTP 服务下 Chrome/Firefox 实际进入测试地图、移动/射击/重新开局；日志确认 WebGL2 和 QVM 模式；故意 404、损坏 PK3、错误 WASM、无 WebGL2 均得到明确可恢复状态。尚未授权的 Origin Game 发布不执行。资产 fetch、MEMFS 与 wasm heap 峰值分别计量，不能把 256 MB heap 当作浏览器总内存。

### P2 — WebGL2 后端与代表画质验证

依赖：P1；owner：E-RENDER，CONTENT 提供受控测试材质/网格。

产物：能力探测、FBO/深度/MSAA/浮点格式、GLSL ES shader 变体、色彩管线、低中高配置、context loss 重建/恢复策略。

验收：固定相机拍摄非金属/金属、粗糙/光滑、法线、透明、发光、阴影、HDR 过曝、LDR 降级、骨骼角色；检查实建 FBO 完整性和 GL/shader 错误，不只读取 extension 字符串。启用/禁用浮点能力分别通过；模拟 context loss 后恢复场景或给出明确重载流程。目标设备 1080p 中档 60 fps（5 分钟场景 P95 帧时间 ≤16.7 ms，P99 ≤33.3 ms）为初始门槛；计量时排除下载阶段但单列首次 shader 编译卡顿。达不到则阻止高精资产批量量产，先定位后端瓶颈。

### P3 — 资产契约、角色/武器动画与完整表现切片

依赖：P0/P2；owner：CONTENT + E-PRESENT + E-RENDER，公共 ABI 经 E-INTEGRATE。

产物：DCC→IQM/材质/贴图/地图流水线；一个完整角色、第一人称武器手臂、不同性质武器（hitscan 与 projectile）、新环境材质/装饰、完整开火→命中→死亡→重生表现；可重建的 source assets 和许可记录。

验收：全动画清单逐项触发，步行/跑/蹲/跳/瞄准/换枪/开火/死亡的交叉过渡无裂缝与附件漂移，低/高帧率无事件双触发。用不对称骨骼/材质样本发现坐标轴、权重、normal Y、金属/粗糙通道错置。对照 P0：任一新枪模/动画不得改变 shot time、命中、弹药与权威位置。工具拒绝超预算骨骼、缺贴图、非法路径和不匹配版本，而非运行时随机崩溃。

### P4 — 原玩法全量回归、Bot 与本地完整游戏循环

依赖：P1 的运行与 P0 数据；可与 P2/P3 并行规则测试，最终需合入 P3 表现；owner：E-RULES + E-BOT + E-QA。

产物：全部选定模式/武器/道具/场景规则矩阵与差分工具、本地 Bot 和单人/多人规则流；菜单→选图/角色/难度→比赛→结算→下一局。

验收：第 4 节边界轨迹/事件全部对比；所有 Bot 难度至少每种参考模式跑一个完整局，8 Bot 场景持续 60 分钟，检查卡死、不可达、换图/重生、内存与帧耗时；不要把一局能开枪当作玩法复刻。若 QVM 占用超预算，单列同源码静态编译 game/cgame 或 WASM 模块的架构实验，版本化 syscall 与验证语义一致；不能直接删解释器或解除模块隔离来换 benchmark 分数。

### P5 — PC 手感、声音、设置与存档生产化

依赖：P1；手感/声音最终验收依赖 P3/P4；owner：E-INPUT + E-AUDIO + E-STATE + E-UI + E-WEB。

产物：完整 PC 操作、声音混音、新 UI/HUD、IDBFS 设置/进度、版本迁移与导出；同一份设置源。

验收：60/144/240 Hz 的按键、鼠标持续转动、点击开火、滚轮、聊天/菜单、Alt-Tab、Esc、全屏反复 20 次无粘键/意外射击。记录输入事件→usercmd→绘制提交；真实 click-to-photon 与端到端声音延迟用实机高速录制/设备测量，不拿 JS 时间戳冒充。三种异步情形（授权拒绝、音频 suspended、恢复焦点）均可重试。改键位/音量/画质、完成关卡后刷新/关闭重开仍保留；迁移旧版本、配额拒绝、私密模式、多标签竞争不破坏原记录，明确提示未持久化。

### P6 — 浏览器联机与权威服务端

依赖：P1/P4 的协议和版本基线；连通性实验可提前并行，但上线验收依赖 P5；owner：E-NET + E-WEB + 平台/运维工作包。

产物：native dedicated build、WebRTC 网关/信令、WSS 兼容回退、房间/版本/pure/资源校验、连接质量 UI、断线与重连语义。

验收：按第 5 节网络矩阵跑双人对战、多人/Bot 混合、观战、换图、加退房和掉线；对比 server authoritative 日志。8 名玩家单局先达成稳定性，再以最终容量目标压测网关和 server，记录 CPU/内存/出口/带宽/每房成本；100 次加退房无遗留会话/UDP 映射。测试目标白名单、过期票据、畸形包、超速输入、错资源版本、TURN 及 WSS 尾延迟；没有真实跨网络结果不得宣布联机完成。部署共享基础设施另需授权，本阶段可先本地/受控测试。

### P7 — 全量内容整合、性能与兼容性收敛

依赖：P2–P6、完整合法内容交付；owner：所有模块各自负责，E-QA 统筹。

产物：全内容 checklist 关闭、每图 AAS/碰撞一致性、所有角色/武器/模式回归、画质档位、错误收集、资源分包缓存、QA 构建。

验收：每张图、每把武器、每类 Bot/模式都有实际跑过的记录；目标 PC 浏览器矩阵通过完整局。建议 1080p 中档 60 fps 及独显竞技档 144 fps（P95 ≤6.94 ms）分别测试，后者是增强目标，P0 冻结承诺等级。首个可玩包建议 ≤50 MiB 压缩传输、20 Mbps/80 ms 条件下冷启动 ≤30 s，超额须通过分包/素材预算解决；下载完成后首局不因缺资产停顿。暖缓存重复进入、20 次换图、2 小时对局无持续内存增长或音频泄漏；记录 wasm heap、JS ArrayBuffer、纹理/FBO 估算和进程峰值，最后根据实测设置 heap 与内容上限，不盲目扩大 TOTAL_MEMORY。

### P8 — 发布候选与明确授权后的上线

依赖：P0–P7 全部通过，资产及品牌权利完结；owner：主线程/平台发布工作包。

产物：root index、相对 URL、可缓存版本化产物、源代码/许可证/第三方通知及构建对应关系、隐私/日志规范、恢复/回滚手册。GPL 引擎及衍生代码按适用条款提供对应源码/构建信息；资产许可证单独列明，不能将代码 GPL 误当商业资产许可证，也不能默认套平台 protected 模式。

实施平台集成前，必须读取 fran0220/origingame 当前 `skill/origingame-deploy/SKILL.md`、deploy.sh、`docs/origin-gateway.md`，核对 loading/readiness/fullscreen 的实际接口。本文不编造其函数名或保证嵌入权限；单独页面和平台 iframe 分别验证启动、resize、Pointer Lock、全屏、音频、存档分区、网络及错误 UI。只有资源和可玩状态确实就绪才发 ready。

最终验收：无商业未授权素材/密钥、无绝对本机路径、无缺文件、许可证/源码可下载、两种运行环境完整比赛通过。用户明确授权后才能按根 `.origingame-deploy.json` 的固定 creator 发布，不重新随机身份；首次发布返回 ID/URL 需要保存。发布后执行真实地址冷/暖启动、加退房、设置、全屏、音频、完整局和回滚验证。当前阶段不执行上述发布或任何付费生成。

依赖汇总：P0 → P1 → P2 → P3；P0/P1 → P4；P1 → P5，P3/P4 → P5 最终验收；P1/P4 → P6；P2/P3/P4/P5/P6 + 全量合法内容 → P7 → P8。内容生产在 P3 契约稳定后扩大，联机风险实验不应拖到全部美术做完才开始。

## 8. 高风险、停线条件与实施排序

| 风险 | 早期信号 | 处理与停线条件 |
| --- | --- | --- |
| 商业内容权利未成立 | 只能使用来源不明 PK3/原版贴图/声音 | 原创测试场继续引擎工作；商业内容发行停线，授权或重新确认原创产品范围 |
| GLES 功能被误当桌面全功能 | HDR cvar 开启但无 FBO，阴影 pass 未执行 | P2 用实际 GPU 资源与图像验证；失败不量产高端素材 |
| QVM/Bot 占满主线程 | draw cost 低但 8 Bot 帧时超预算 | 先 profile，独立优化/静态编译实验；保护语义和 ABI，不把降 AI 频率藏作优化 |
| 重制变成玩法改版 | 动画改 shot time、root motion 推位置、改碰撞 | 规则 golden 测试强制阻断；提出独立产品变更 |
| 材质/骨骼管线反复返工 | artist 输出与运行时通道/轴/关节不符 | P3 用不对称测试资产锁定转换/版本与校验，稳定后批量制作 |
| 浏览器主线程/内存 | 加载 PK3 多副本、shader 卡顿、换图增长 | 分包、缓存、预热、释放和预算；Worker/pthreads 仅在测量必要且宿主 COOP/COEP 可行后独立验证，不作为无条件前提 |
| 网络竞技体验不达标 | WSS 丢包时尾延迟恶化，TURN 带宽过高 | 提前测 WebRTC/回退；容量/成本无法承担则阻止联机上线，不伪装成原生 UDP 等价 |
| 嵌入权限/存储隔离 | 独立窗口可玩而 iframe 无输入或不能保存 | P1 尽早跑真实宿主权限原型，P8 再全量验证；平台接口/许可不满足时需平台工作包解决 |
| 多 owner 冲突 | 公共头/syscalls/CMake 被多人同时改 | E-INTEGRATE 串行收口；工作包按表只写所属文件，重建全链后进入下一阶段 |

实施第一批顺序是 P0 基线与原创合法测试包 → 固定 SDK 复现 P1 → P2 FBO/WebGL2 关键缺口 → P3 代表重制切片；同时尽早做传输网关风险实验。它们证明长期路线可行，但只有 P7/P8 的全内容、全玩法、完整 PC 浏览器与线上环境验收才代表重制完成。
