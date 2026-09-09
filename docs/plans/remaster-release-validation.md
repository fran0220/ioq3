# PC 浏览器重制：发布与长期质量工作包

状态：2026-09-09 只读调查与规划；不是发布批准或兼容性证明。本文件是该工作包唯一写入范围；不依赖主线程尚未推送的本地修改。

集成说明：以[主计划](../remaster-plan.md)的统一预算、阶段和授权记录为准。本文硬件/网络数值与 WSS 优先是实验候选，不是另一套合同。用户已提出最终上线目标；不得在满足已约定条件后重复索取相同发布授权，但权利、付费额度和外部基础设施仍需明确，未满足前不发布。

## 1. 范围、事实标记与停止条件

- **已选路线**：沿用 C/C++ → WASM，PC 键鼠优先，不考虑移动端；复刻玩法循环，视觉、音效、动画全重制，资产走原型图 → 生成 3D → Blender 清理/绑定/烘焙/导出流程。
- **完整交付范围**：全部批准清单中的地图、模式、角色、武器、Bot、多人，以及下载、运行、发布、回滚、GPL 对应源码与资产证据链。先做单图/Bot 验证是阶段门禁，不是缩减最终范围。
- **当前停止条件**：地图/角色等原作权利未确认、资产预算未确认、没有现成可用游戏数据。不得下载商业 PK3 充当可发布数据，不得付费生成，不得创建或更新线上游戏，不得部署外部服务器。可规划、写代码、用自制无争议测试几何验证，但后续行动仍受主任务授权约束。
- 下文 **F** = 当前源码/仓库文档事实；**V** = 需要浏览器或线上验证；**D** = 用户或权利/预算负责人必须决定；**P** = 本计划建议，尚非已实现能力。

## 2. 调查依据与可信度

平台调查通过 Librarian 完整读取当前 `skill/origingame-deploy/SKILL.md`、`skill/origingame-deploy/scripts/deploy.sh`、`docs/origin-gateway.md`，并追踪部署、静态服务、SDK、iframe、房间与 release cleanup 实现。固定平台版本：[7eb275d](https://github.com/fran0220/origingame/commit/7eb275d91abdae9331c7e8c457257644f432f388)。这是源码调查，不是生产探测。以下平台链接固定到该版本；正式实施和每次发行前必须重读当时版本，不能把这份快照当永久平台契约。

本地直接读取：`cmake/platforms/emscripten.cmake`、`code/web/client.html.in`、`code/web/client-config.json`、`README.md`、`COPYING.txt`、`code/qcommon/q_shared.h`、根 identity。

### 2.1 构建、托管与下载

| 项目 | F：核实结果 | P/V：落实与验证 |
|---|---|---|
| 构建 | 当前 Web 链接固定 TOTAL_MEMORY=256MB、STACK_SIZE=5MB，WebGL 1–2；禁用 native server、动态游戏库、HTTP 选项；未配置 pthreads。项目指导要求保留 Emscripten 3.1.58。 | Release 浏览器产物单独构建；不得把 native Debug 成功当浏览器可发布。确认 QVM 构建和合法 botfiles；线程版必须独立批准并验证。 |
| 数据加载 | 模板设置 `net_enabled 0`、`sv_pure 0`；各目录一次发起全部文件 fetch，再写入 MEMFS；缺失文件会 continue，没有字节哈希检查。配置引用商业包但不提供这些包。 | 制作重制资产清单，限制并发（暂定 4，可测后调整）、必需文件失败即阻断启动、大小/哈希校验、可取消重试、清理旧缓冲；联网发行恢复明确的纯净资源校验策略。 |
| MIME | `.wasm` 是 `application/wasm`；`.pk3` 未专列，fallback 为 `application/octet-stream`。 | GET 检查 MIME、实际字节、404 不得变成 HTML 200；验证 WASM 流式编译。PK3 二进制 MIME 本身不是阻碍。 |
| 缓存 | 当前本地 play 静态路径是 `no-cache` + 弱 ETag/304，SDK max-age=300；S3 release immutable 实现仍存在，但运维文档记载生产已回退本地。 | 冷缓存、热缓存、条件请求、更新期间混合版本、SDK 更新均实测；不可承诺 CDN 或长期 immutable。 |
| 压缩 | 服务能选择已存在的 `.br/.gz`，但当前部署流水线不自动产生它们，运维清理规则还会删旁文件。 | 测 Content-Encoding/Vary、Brotli/gzip/identity 解码后 SHA 一致；WASM/JS 值得压缩，已压缩 PK3 收益单测。不要用上传 ZIP 压缩率代表客户端下载。 |
| 发布体积 | CLI 整目录 ZIP multipart；默认 MAX_UPLOAD_MB=200 MiB；仓库 Nginx 请求体 210m。MCP base64 最多 36,000,000 字符（约 27 MB 原始上界），checkpoint 不绕过 Portal 上限。 | 真实生产限制待核实；包增长需要重新预算或平台变更批准，不能假设分批上传、增量 patch 存在。 |
| 解压/下载 | 解包有路径/符号链接防护，未见累计解压/文件数上限；本地服务未见 Range/206 分支，无部署断点上传契约。 | 未见限制不等于无限。完整重发/逐文件重试为基线，不依赖 Range；按 manifest 记录文件数、总解压大小、磁盘与运行内存。 |
| 离线 | Skill 的 PWA 宣传与实现不一致：流水线删典型 SW/webmanifest，SDK 阻止注册并清理旧 SW。 | 不把平台自动离线/PWA列入承诺；浏览器缓存仅为优化，必须能在线重新获取。 |

证据：[静态服务](https://github.com/fran0220/origingame/blob/7eb275d91abdae9331c7e8c457257644f432f388/server/src/play/serve.ts#L10-L95)、[部署构建](https://github.com/fran0220/origingame/blob/7eb275d91abdae9331c7e8c457257644f432f388/server/src/routes/deploy.ts#L69-L181)、[处理与 SDK 注入](https://github.com/fran0220/origingame/blob/7eb275d91abdae9331c7e8c457257644f432f388/server/src/pipeline/process.ts#L25-L130)、[存储现状](https://github.com/fran0220/origingame/blob/7eb275d91abdae9331c7e8c457257644f432f388/docs/object-storage.md#L28-L50)、[配置](https://github.com/fran0220/origingame/blob/7eb275d91abdae9331c7e8c457257644f432f388/server/src/config.ts#L76-L92)。

### 2.2 加载、全屏、锁鼠、音频与 iframe

- **F**：`OG.loading.begin/stage/progress` 切为手动加载；无手动调用会在 window load 后自动 ready，早于异步 WASM/数据完成。SDK 20 秒未 ready 会记 load_failed，Portal 25 秒 slow 提示但不销毁 iframe。**P**：尽早 begin，分下载/校验/挂载/初始化/首帧；只有真正可操作的主菜单完成才 ready，不用空白壳骗取时限。选图加载另有真实进度；联网 ready 不等于已进房。**V**：重试、失败、慢速、离线恢复和重复 ready 幂等。
- **F**：`OG.fullscreen()` 嵌入时请求父级 shell 全屏，直开才对 document 全屏，返回 boolean。**P/V**：显式点击调用，处理 false/拒绝、Esc、外层控制条、缩放与高 DPI；不要直接只放大全屏 canvas 绕过平台 shell。
- **F**：iframe allow 含 autoplay/fullscreen/gamepad/pointer-lock；sandbox 含 scripts/same-origin/pointer-lock/downloads/orientation-lock/modals。**V**：权限属性不保证实际锁鼠成功；游戏自己处理 pointerlockchange/error、用户手势、Esc、Alt-Tab、失焦后重新点击；禁止失焦后自动抢回锁鼠。
- **F**：`OG.userGesture()` 是首次手势通知，不会调用引擎 AudioContext.resume；PC iframe 默认自动加载。**P/V**：明确“点击开始/恢复声音”入口，实际恢复音频上下文；后台/休眠/全屏退出/设备变化都重测，保证不会双重播放、失焦连发或保持移动键。
- **F**：play 设置 COOP same-origin、COEP require-corp、CORP cross-origin、nosniff、frame-ancestors；所读 Portal 顶层没有配套隔离头，iframe allow 未声明 cross-origin-isolated。**P**：单线程 WASM不因自身执行必需 SAB/跨源隔离，但必须兼容平台现有 COEP；外部资源需正确 CORS/CORP。若引入 pthreads，共享内存需要安全上下文和完整顶层/iframe/worker隔离链。**V**：直开和平台内嵌分别检查 crossOriginIsolated、SAB、实际 worker/共享内存，不得靠关闭 COEP 过关。平台 header 改动属于共享基础设施批准事项。

证据：[SDK loading/fullscreen](https://github.com/fran0220/origingame/blob/7eb275d91abdae9331c7e8c457257644f432f388/sdk/src/og-sdk.ts#L750-L824)、[SDK 超时](https://github.com/fran0220/origingame/blob/7eb275d91abdae9331c7e8c457257644f432f388/sdk/src/og-sdk.ts#L863-L909)、[手势](https://github.com/fran0220/origingame/blob/7eb275d91abdae9331c7e8c457257644f432f388/sdk/src/og-sdk.ts#L309-L335)、[iframe](https://github.com/fran0220/origingame/blob/7eb275d91abdae9331c7e8c457257644f432f388/web/src/pages/Play.tsx#L381-L406)。

### 2.3 浏览器联网与批准边界

**F**：浏览器不能直接复用 Quake 原生 UDP socket；平台 CSP 不设 connect-src 不等于提供 UDP。OG rooms 是自己的 WebSocket 房间协议，relay 10 KiB frame、8 KiB data、30 messages/s/client、重连宽限 15 秒。未找到 WebTransport 实现、通用 Quake UDP 代理或原生 dedicated server 发布接口。平台房间 actor 的 512 MiB 地址空间和 Node heap 64 MiB 是服务端限制，不是浏览器 WASM 内存配额；`--jitless` runner 也不能直接假设适合 ioq3 服务端。AI Gateway 是模型转发和计费，不是多人传输。

**P：推荐完整联网路线**：保留原生 dedicated server/游戏协议语义，做浏览器 transport 抽象 + WSS→UDP 会话网关，先测协议封包、可靠/非可靠语义和 TCP 队头阻塞。网关必须绑定会话与获准目标，不提供任意 UDP 转发；加入鉴权、origin校验、限流、包长上限、超时、DDoS策略和日志脱敏。游戏状态以服务端为权威；输入序号、重放/重复包、预测/纠正和掉线重连都要验证。

**备选及决策实验**：若 WSS 在 100 ms RTT/1%丢包下达不到多人门禁，评估 WebTransport datagram 或 WebRTC DataChannel。前者涉及浏览器覆盖、HTTP/3/证书/边缘支持，后者涉及 ICE/STUN/TURN 和运维成本；不得预先宣布平台支持。OG rooms 可评估作大厅发现/邀请，但不能未经负载和协议测试直接承担 Quake 快照流。批准的正式传输必须覆盖完整支持浏览器集合或明示用户可接受的兼容性范围。

**D：独立授权事项**：外部服务器地域/规格/持续费用，WSS域名/TLS/DNS，开放端口、网关部署、数据库写入、监控留存/隐私政策、TURN或HTTP/3、容量与运维责任。浏览器代码和本地模拟验证不等于这些授权；unlisted 平台上传也属于发布。无授权时可完成本地协议实验与离线 Bot，不能宣布多人上线完成。

证据：[relay 限额](https://github.com/fran0220/origingame/blob/7eb275d91abdae9331c7e8c457257644f432f388/server/src/rooms/relay.ts#L20-L25)、[Gateway 边界](https://github.com/fran0220/origingame/blob/7eb275d91abdae9331c7e8c457257644f432f388/docs/origin-gateway.md#L9-L41)。

## 3. 暂定 PC 性能合同（P，设备未定，不能当已达标）

**候选最低档**：Windows 11、4核8线程、8 GB RAM、Intel Iris Xe 级集显、SSD、1280×720 low；**候选基准档**：6核12线程、16 GB RAM、GTX 1650 4 GB级、SSD、1920×1080 medium。这些只是便于启动测量的预算，D：由用户确认具体 CPU/GPU/驱动、显示器和最低档价格范围。macOS 桌面 Safari 是否正式支持也须确认；暂列兼容性调查，不默默删除。Linux Chrome/Firefox列次级回归。全程不包含移动端。

| 指标 | 暂定门槛与测量条件 |
|---|---|
| 帧时间 | 基准档 1080p medium，最重地图8 Bot/多人等效负载，10分钟采样 p95≤16.7ms、p99≤33.3ms；最低档720p low p95≤33.3ms。144Hz竞技档是后续目标，不替代基础合同。 |
| 停顿 | 稳态不得反复出现>100ms停顿；首次 shader 编译单列，尽量前置暖机。地图加载不混入稳态帧时间。 |
| 启动 | 25 Mbps、50ms RTT、无丢包、冷缓存：可操作菜单 p95≤15s，首次进入比赛 p95≤30s；100 Mbps/20ms 热缓存菜单≤5s；慢网5 Mbps必须展示准确进度/取消重试，不能假 ready。 |
| 下载与发行 | 首菜单必需传输≤20 MiB，第一张图额外≤40 MiB；当前单次完整发行ZIP暂预算≤160 MiB，距默认200 MiB留余量。完整内容若超限必须在量产前解决，不以删地图过关。 |
| 内存 | 先保持256 MiB固定 WASM heap验证；是否调至512 MiB/增长模式由测量决定。暂定 renderer进程峰值≤1 GiB、估算GPU资源≤512 MiB；区分 JS缓冲/MEMFS/WASM/GPU，浏览器不可测项明确标注。 |
| 生命周期 | 30次地图轮换、2小时 soak 后稳定态内存相对暖机后增幅≤10%，无OOM/崩溃/重复音轨；正式候选8小时 soak。测前后GC稳定窗口，不能把瞬时峰值误判泄漏。 |
| 输入 | 实机摄像/硬件测量目标基准档输入至显示 p95≤50ms；自动浏览器只能测事件处理等代理指标，不能声称测得端到端延迟。 |
| 多人 | 保留所选参考版本的权威模拟频率与时间推进规则；server tick p99不得超出该频率的单tick预算，不因显示器刷新率改成60Hz。目标8人稳定，16人压力；50/100/200ms RTT、0/1/3%丢包分档记录，100ms/1%为可玩门禁。 |

每次测量记录硬件、OS、驱动、浏览器完整版本、渲染器/分辨率/画质、build与asset哈希、地图/模式/Bot数、网络、冷/热状态、样本数。启动测试至少20次，稳态3轮10分钟；相同基准比较 p50/p95/p99。超过预算或对基线退化>10%必须归因并批准，不通过更换较快设备掩盖回归。无真实 GPU 的 orb 只能做功能/构建检查，不能签性能通过。

## 4. 长期回归矩阵与资产验收

建立版本化“内容清单 × 测试用例 × 支持环境 × 证据”矩阵。全部地图有唯一ID、模式适配、资源哈希、权利状态、测试状态；“地图数待定”不能变成遗漏项。D：确认原作 baseq3 全部地图是否含 Team Arena、隐藏/演示/扩展地图；未决条目标 BLOCKED，不虚构完成。原作布局、名称和角色外观也可能受权利约束；全重制美术并不自动解决复刻地图授权。

| 维度 | 完整长期覆盖 |
|---|---|
| 地图 | 每张：出生点、碰撞/跳跃台/传送、掉落死亡、物品计时、遮挡/光照、音场、导航/AAS、可达性/卡点、最重视角、加载/退出/重开/轮换、缺失资产阻断。 |
| 模式 | FFA、Tournament/duel、Team DM、CTF、单人/Bot进度与结算；若批准 Team Arena，增加 One Flag/Overload/Harvester及其资产。只测试地图声明支持的组合，其余标N/A并有理由。 |
| 武器/玩法 | 所有武器×主场景：命中/散布/距离/溅射/自伤/护甲/伤害、弹药拾取/切换/死亡掉落；移动加速/跳跃/空中控制、道具、击杀归属、计分、平局/加时/胜负/重赛。预期来自独立规则说明，不从当前实现反推。 |
| 角色/动画/音频 | 每角色全状态：idle/run/strafe/jump/land/attack/pain/death，第一/第三人称同步、武器挂点、LOD切换、穿模；空间音、并发枪声、循环音停止、音量/静音持久化。 |
| Bot | 每张图每支持模式至少1/4/8 Bot、全部难度分层；导航脱困、拾取、战斗、CTF目标/队伍切换；固定种子重复场景，记录完成率和长时间卡住。不能以只生成AAS即合格。 |
| 多人 | 2/8人正常、16人压力；加入/离开/晚入/观战/换队/重连、满房、重复登录、版本不符、服务端轮换/崩溃恢复、恶意/超长输入、混合浏览器；纯净资源、权威伤害与反作弊基础校验。 |
| 网络 | RTT/丢包/抖动/限速矩阵、断网/重连/超时、TCP队头阻塞、半连接、网关重启；客户端预测误差、tick耗时、带宽、恢复耗时和异常率。 |
| 浏览器生命周期 | Chrome/Edge/Firefox稳定版及前一主版本；直开/真实平台iframe；窗口/全屏、高DPI/缩放/resize、Esc/Alt-Tab、后台/休眠、锁鼠拒绝、音频未解锁、WebGL context lost/restored或明确可恢复报错、持久化/存储受限。 |
| 下载/发布 | 冷/热/损坏缓存、404/截断/错hash、重试/取消、并行加载、版本切换中途加载新地图、许可/source链接、无密钥/私有路径泄漏、同gameID、回退包重发。 |

**执行层级**：每次提交构建/静态/规则单测；每夜全部地图加载+核心模式+固定Bot种子与浏览器代表组合；每周完整地图模式与网络压力/长时测试；每个release candidate跑所有支持环境核心路径、全部内容覆盖、8小时soak和授权后的平台实测。pairwise仅用于非核心环境组合，不替代每张图每支持模式的行为验收。新 bug 必须附可重复输入、独立期望值与防回归用例。

**资产工作包交接门**：每张原型图有权利/提示词/模型版本/生成批次/费用记录；生成3D不是最终游戏模型，Blender需完成拓扑、比例、朝向、UV、PBR/引擎材质映射、碰撞、LOD、骨架、动画、烘焙和导出检查。贴图尺寸/三角面/骨骼/声音时长按性能预算倒推并在代表场景签收；不凭“视觉更精细”放行。保存可编辑.blend、原始音轨和来源文件；交付包与编辑源分离，源码/素材源许可证分别标明。

## 5. GPL 与素材证据链

- **F**：仓库 COPYING 为 GPLv2；所读引擎头注明 GPLv2 or later。**P**：逐项核实依赖和新增代码后确定引擎最终标识（候选 GPL-2.0-or-later），不可把整包默认标为 MIT。引擎GPL不授予 Quake 3 商业数据、商标或角色再分发权；玩法复刻与地图/外观/音效表达授权分开审查。
- 每个资产记录：稳定ID、作者/权利人、来源URL/采购凭据、许可文本及版本、商用/再分发/修改范围、衍生链、文件SHA-256、导出工具、审核人；生成资产附工具条款、输入图授权、模型/提示词、生成日期及费用。无证据标阻断，不能仅靠“AI生成”放行。
- 每次WASM发行提供与二进制匹配的完整对应源码、改动、构建/安装脚本、固定工具链及依赖获取方法、许可证/版权声明；长期公开可获取的release源码快照，做干净环境重建。minified JS/链接WASM或一个浮动main链接不代替对应源码。可编辑美术源是否公开取决于其许可，不能把代码GPL误扩大为全部美术必须GPL。
- **F**：helper 默认 protected；open 缺省 license_name 会被平台默认 MIT。每次未来发布必须显式 open + 审核后的正确license_name + 对应source_url。平台assets_used最多100组关联，manifest仅归属元数据不是授权证明；维护独立完整资产台账。
- 法律边界与原作复刻授权由有权负责人/专业法律审核确认，本文件不是法律意见。可发布的数据缺失是首发硬阻断，不可用本地合法购买替代再分发许可。

## 6. 分阶段门禁与证据包

| 阶段 | 工作与完成证据 | 不通过时 |
|---|---|---|
| G0 范围/合规/预算 | 地图模式角色完整清单、版权路线、生成及infra预算、PC基准、浏览器合同、责任人确认；当前仅规划完成。 | 只用自制测试几何继续技术验证，不生成收费资产/发布。 |
| G1 可复现Web底座 | 固定Emscripten版本，干净构建WASM/QVM，root index/相对资源，loading/错误/锁鼠/音频/生命周期自动与人工记录。 | 修底座，不铺量资产；native Debug不是替代证据。 |
| G2 代表性垂直切片 | 一张覆盖最重渲染/导航的原创或获授权地图、全部关键武器机制、代表角色动画和Bot；原型→3D→Blender流程质量与成本实测。 | 调画质/技术预算，避免完成全量后才发现下载超限。 |
| G3 全内容与联网 | 全地图模式清单逐条完成，全部资产溯源和导航，多人transport比较实验、外部infra获批准后部署测试、容量与安全验收。 | 保持内部里程碑，不把单机切片称为长期任务完成。 |
| G4 候选包 | 全矩阵、性能合同、8小时soak、源码重建、哈希/SBOM/资产台账、发布包≤核实上限、无P0/P1。 | 阻断发行；P2仅可有负责人/期限/公开限制的接受记录。 |
| G5 授权平台预发 | 明确授权后同identity按约定visibility上传；真实iframe/headers/压缩/缓存/网络验证；回退演练与新旧会话兼容。 | 修复或授权回退；unlisted也不可在授权前执行。 |
| G6 公开发行与维护 | 用户明确批准公开发行、封面海报与许可/source审阅；发布后验收、监测值班/费用/隐私责任、回滚权限明确。 | 不自动扩大发布或运维授权。 |

每个门禁保存：源码与资产版本、构建日志、测试原始数据、浏览器控制台/网络证据（脱敏）、代表截图/动画视频、缺陷列表、批准记录。P0=数据/凭证/法律风险或普遍不可运行；P1=核心玩法/地图/多人严重损坏、崩溃、OOM、无法输入/恢复；不以均值帧率好看抵消关键失败。

## 7. 同 gameID 发行、回退与长期运维

**F**：根 identity 当前只有 creator `og-atlas`，尚无gameId。helper依identity的gameId默认PUT更新，`--new`才另建；首发成功会保存ID/slug/URLs。必须始终使用根 `.origingame-deploy.json`和该creator命名密钥，不能假设裸OG_API_KEY属于它，不因新orb/临时dist重新选作者。

**F**：构建失败通常不切旧release；成功更新会retire旧版本，约60秒后可清理旧字节。未找到发布者历史rollback API。数据库记录留存不代表包还在。当前本地路径每个请求查询当前release，跨版本懒加载可能混包；内容哈希能防止静默错配，但旧哈希文件被删仍会404。

**P：发行记录**：每版保存原始发布ZIP、SHA-256、完整artifact清单、源码快照、工具链/依赖版本、资产证据、cover/poster、所有发布参数、gameId/version/releaseId、实际响应headers和验收结果到获批准的持久存储。只保存orb工作区不够。发布必显式license/source，检查HTTP状态和JSON，不依赖helper注释。

**P：会话一致性**：manifest绑定buildId，资源文件内容寻址且校验；当前存储实现下优先在进局前完成该局必需文件加载。更新前确认活跃会话策略：兼容窗口内新包保留必要旧哈希资源（也计入ZIP预算），或客户端发现资源版本不可用后提示安全重载而非混用。完整地图懒加载所需的版本固定资源URL/旧版保留能力若依赖平台改造，必须先批准并验收，不能仅改文件名就宣布解决。

**P：回退手册**：确认影响→停止继续发行→定位最后已验收原始包→验证包/源码/依赖及服务端协议兼容→获得当次或预先界定的事故回退授权→用同根identity向同gameID重新PUT旧包形成新version→直开和iframe验证、检查活跃玩家/缓存/资源/服务端→记录恢复时间与根因。不得创建第二gameID冒充回退，不依赖平台60秒旧包。目标RTO暂定30分钟，必须通过演练后才承诺；若有持久玩家数据，备份/RPO/不可逆schema迁移另行设计和批准。

**P：监测**：区分平台20秒加载遥测与真实不可玩率，采集buildId、加载阶段失败、崩溃/OOM、p95帧时间、下载失败、多人断线/tick/容量；不采API key/聊天或个人内容。公开后观测窗口与自动告警/回滚条件待批准；监测授权本身不授权发布、扩容、回滚或基础设施写入。本阶段不创建定时任务。

证据：[identity及部署参数](https://github.com/fran0220/origingame/blob/7eb275d91abdae9331c7e8c457257644f432f388/skill/origingame-deploy/scripts/deploy.sh#L69-L105)、[release更新](https://github.com/fran0220/origingame/blob/7eb275d91abdae9331c7e8c457257644f432f388/server/src/routes/deploy.ts#L664-L710)、[旧包清理](https://github.com/fran0220/origingame/blob/7eb275d91abdae9331c7e8c457257644f432f388/server/src/releases/cleanup.ts#L15-L41)。

## 8. 必须由用户决定、必须实测与当前结论

**D：优先决策**：①原作地图/角色/商标与资产再分发授权路线，若不能授权是否接受保留玩法而原创表达；②全部地图/模式是否含Team Arena及扩展内容；③生成/人工修模/音频/托管与网络月费预算；④最低/基准PC、Safari/macOS支持合同；⑤多人目标人数/地域/匹配账号需求与运维责任；⑥平台预发/公开发行/事故回退的具体批准边界。

**V：不能提前声称通过**：实际浏览器构建与合法数据启动、所有地图与性能、当前生产体积限制/压缩/Range/缓存、iframe音频/锁鼠/全屏与SAB、多玩家服务与网络退化、同gameID资源一致性与回退。此文没有执行这些测试。

**当前完成项**：平台与项目源码调查、完整PC发布/质量工作包、门禁/回归矩阵/暂定预算/恢复方案；仅新增本文件，没有修改引擎、生成资产或发布。后续实施线程可以依门禁并行分工，但本工作包不创建任何新线程。
