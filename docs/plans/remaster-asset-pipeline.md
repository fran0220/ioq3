# ioq3 PC 网页重制：完整资产生产与交付规划

核验日期：2026-09-09。状态：**仅规划；未生成、未发布、未完成商业资产权利确认**。

## 1. 已决定的范围与必须保留的关卡

- 目标为 PC 网页端，沿用 ioq3 → Emscripten/WASM/GL2，不引入 Three.js。玩法循环复刻，画面、角色动画、特效、声音与手感重新制作和调试；长期分批覆盖全量资产，不把样件当最终范围。
- 所有可见场景组件，包括地形表面、建筑、植被、道具、角色、武器及附件，必须经过**原型图批准 → 图生 3D → Blender 加工 → 引擎交付 → 网页验收 → 经授权上线**。纯逻辑碰撞、触发器、导航体可手工搭建，但不能以可见程序几何或现成素材绕过此链。
- HUD、字体、图标、菜单、纯音频不强造 3D：使用对应的二维/声音制作链；依附场景的发光面、喷口、碎片等可见实体仍走上述链。粒子贴图、天空、光束可以由经过该链的场景/模型在 Blender 烘焙成二维运行资产，来源不能丢失。
- 原作商业数据、截图作为生成参考的权利、角色/标识/地图视觉设计的权利尚未确认。不得把已有商业 pak、纹理、音频、模型混进公开样件。玩法实现的合法边界也须审核；“重新生成”不等于消除原作权利。
- 本文件不授权任何费用、上线、平台基础设施变更或代码实现。后续所有工具和预算是待实施合同，不声称已存在。只拥有本文件，不依赖源线程未推送的更改。

## 2. 运行时合同先于生成量产

| 合同 | 已核实事实 | 生产决策 |
|---|---|---|
| Web 渲染 | `cmake/platforms/emscripten.cmake` 关闭 GL1、动态 renderer、原生 game libraries、引擎 HTTP 下载；256 MB 内存、5 MB 栈、WebGL 1–2 链接范围；GL2 默认开启 | 浏览器实测为准，不能把编译选项当 WebGL1 完整兼容承诺；保留 GL1 材质作为传统回退/原生对照 |
| Web 资源/网络 | `code/web/client.html.in` 默认 `net_enabled 0`，预加载 `.data` 或 fetch 写入虚拟文件系统 | 首个闭环先做离线 bot 对战；联机为独立引擎/传输任务，AI Gateway 不是 Quake 网络替代品 |
| 模型 | 两套 `tr_model.c` 支持 IQM、MDR、MD3；显式扩展优先，之后才有替代查找 | GLB/FBX 是加工交换格式，不能直接交付 ioq3；经典 Q3 分段 MD3 为首个兼容基线。IQM 是后续可验证分支，不是默认全身骨骼无缝替换 |
| 玩家 | `code/cgame/cg_players.c` 注册 lower/upper/head MD3、skin、animation.cfg、icon | 骨骼动画须烘焙成分段顶点帧及 tags；引擎格式支持不代表 cgame 合同改变 |
| 地图 | `code/qcommon/qfiles.h` 定义 IBSP v46；`cm_load.c` 和 `tr_bsp.c` 分别读碰撞和可见数据 | 最终为完整 BSP/光照/可见性/实体数据；巨大单个生成网格不是可玩地图 |
| 材质 | GL2 默认 normal/specular 开、PBR 关；GL1 不安全忽略 GL2 stage 语法 | 母版保留 PBR，导出传统和 GL2 两套材质；先用传统 GL2 跑通，再独立验证 PBR |

项目指导要求保留 Emscripten 3.1.58；本次 `.github/workflows/build.yml` 未检出该 pin，视为**待补齐的构建依赖**，不声称现有 CI 已验证该版本。现有 `build-orb` 原生 Debug 不构成浏览器交付。

### 2.1 MD3 硬限制与转换风险

`code/qcommon/qfiles.h`：每 surface ≤4096 顶点、≤8192 三角形；每模型 ≤32 surfaces、≤1024 帧；每帧 ≤16 tags；最多 3 LOD。位置为 signed-short × 1/64，引擎坐标约束约为 [-512, 511.984375]，导出前逐帧检查局部坐标，不能靠截断通过。UV 共用于所有帧，拓扑、顶点顺序与 surface 数必须固定。

这些是格式上限，不是性能目标；读取器、索引拆分、UV seam 拆点还可能使导出顶点数上涨。必须检查**导出的文件**而不是只看 Blender 面板。顶点帧存储随顶点数×帧数增长，角色需要同时控制两者。

## 3. 全资产目录、覆盖率与交付包

先建立 inventory，逐一盘点代码引用、地图实体引用、shader 间接依赖、UI 配置和音频事件；法律允许盘点不等于允许复制。每个槽位有稳定 ID，不以文件名或供应商 task ID 当身份。定义“全量完成”为已批准范围内 required 槽位的验收率 100%，零临时替代和零未知来源，不是只统计已生成数量。

| 分类/ID 前缀 | 必须覆盖的槽位 | 特有交付 |
|---|---|---|
| `env.terrain` | 地面、墙、坡、岩、洞、远景、边界、天空 | 模块拼接、可行走边界、烘焙天空及碰撞对应表 |
| `env.arch` | 墙/地/顶板、门框/门、楼梯/坡道、平台、栏杆、桥、柱、窗、管线 | 网格尺寸、连接口、开关状态、结构/装饰分类 |
| `env.prop` | 箱体、设备、灯具、标牌、植被、布料、碎屑、破坏件 | pivot、交互/破坏状态、LOD、碰撞模板 |
| `map` | 每张竞技场、出生区、复活点、路线、垂直层、危险区、跳台、传送器、门/电梯、观战位 | `.map` 源、BSP v46、光照、VIS、实体表、bot 导航与回归路线 |
| `char` | 每个可玩外观/bot 外观、头/身/腿、队色、第一人称手臂、附件 | 母版骨架、权重、动作表、MD3/skin/icon、tags |
| `weapon` | 近战及每个远程武器的第一/第三人称模型、掉落/拾取展示、弹体、弹药、弹壳、附件 | 握持点/枪口、切换/射击事件、姿态、材质与声音链接 |
| `item` | 血量、护甲、强化、弹药、钥匙/目标物、队旗与底座 | 地面高度、旋转/闪光、拾取碰撞与图标 |
| `anim` | 移动、跳落、蹲伏、游泳、转身、待机、攻击、切枪、手势、死亡、旗帜 | 固定枚举映射、帧表、loop/root-motion 合同 |
| `vfx` | 枪口火、曳光、光束、轨迹、爆炸、烟、火花、命中材质、血/替代反馈、传送、强化、拾取、环境效果 | 模型来源、flipbook、shader、生命周期/层数/透明覆盖预算 |
| `audio` | 每武器射击/尾音/命中、脚步材质、跳落/受伤/死亡/语音、拾取、环境循环、UI、播报、音乐 | 无损母版、目标格式、循环点、响度/峰值、空间化与事件表 |
| `ui` | HUD、准星、计分板、菜单、设置、加载、按键提示、结算、头像、地图预览、字体/本地化 | 源文件、atlas、字号/安全区/可读性、版权与事件状态 |
| `release` | 封面、海报、截图、预告、商店文案、许可页、对应源码 | 独立授权与预算，不能借宣传素材授权覆盖游戏资产 |

命名：`<category>.<family>.<name>.<variant>`；版本独立记录。引擎路径使用小写 ASCII、正斜杠、无空格，按 `MAX_QPATH`（含终止符）校验；同一路径大小写冲突在打包前失败。

每资产交付包必须含：brief；参考及授权；原型图与批准记录；原始生成物和响应；`.blend` 母版及依赖纹理；导出配置/工具版本；runtime 文件；机器报告；人工截图/动作片段；provenance；依赖列表。大原始文件进入受控资产存储，版本库放索引/hash及可再生产配置；存储权限、备份、长期保留费用单独审批。生产凭证不入任一文件。

## 4. 风格、视图、比例与评审标准

**建议风格（待美术批准）**：原创工业科幻竞技场，强轮廓、清晰体块、有限材质族；战斗区优先可读性，不通过原作纹理、标识或特定角色造型复刻视觉。角色、武器、拾取物与环境在明度、运动和轮廓上分层；不只依赖红绿区分队伍，队色同时配形状/符号。

建立 style bible：批准色板、金属/橡胶/石材/发光材质球、边缘磨损密度、曲直比例、倒角尺度、轮廓噪声、图标线宽、字体、VFX 色族、禁止元素和反例。相同测试光照/曝光下评审，原型图不把戏剧性阴影烘焙进 base color。所有批次先对照“黄金样件”再比细节。

- 静态件原型：正/后/左/右正交，俯视、必要底视，独立 3/4 轮廓图和连接口尺寸图；背景中性、无遮挡、无透视混淆，视图标签放元数据，不让模型生成文字。
- 角色：同一身份的正/后/左右、3/4、头手特写；A 或 T pose 二选一并冻结；指缝、腋下、裆部、衣摆与附件边界清楚。武器补左右握持和枪口正视，禁止左右镜像误装。
- 多视图在一次生成任务前人工核对同一体积、服装、色块、朝向。单张拼图不能当作多图 API 已正确理解；最多 1–4 图的供应商路由仍须样件实测。
- Blender 母版按米，Z 向上，统一资产前向并记录 exporter 轴矩阵。暂以 **1 m = 40 Q3 units** 为标定起点，最终由玩家碰撞高度/步高/门宽样件确定并全局锁定；不得缩放碰撞或改变跳跃距离来“让模型看起来合适”。
- 静态 pivot 在底部中心或明确连接基准，门在铰链、电梯在平台基准；角色在足底中心，挂点局部坐标单独定义。应用 transform，避免负缩放，输出引擎前做非对称左右标记试件与法线测试。
- 模块建议使用 8/16/32 Q3 unit 网格；可见装饰可以偏离，连接口与逻辑壳不能偏离。初始 texel density 256 px/m、近景武器 512 px/m，实际随镜头距离/包体校准；母版与运行尺寸分开。

以上数值为工程起点，不是已达标事实。风格/尺度冻结前只做样件，不批量生成；修改 bible 版本时列出受影响资产，不能静默重做并计费。

## 5. 当前 Gateway 能力与不得承诺的事项

核验来源为 `fran0220/origingame` 当前 `main`，使用 librarian 读取，未向生产端探测或付费。正式执行前冻结源码版本、服务条款与当前账号报价；仓库代码存在不等于该账号必然可用。

| 能力 | 已见支持 | 不代表什么 |
|---|---|---|
| 图片 | `/v1/images/generations`、`/v1/images/edits`；MCP generate_image 默认 grok-imagine-image-2.0，可指定 gpt-image-2 | 不保证正交一致、真实比例、可商用或固定单图价格；transparent 是品红背景提示加 cutout，不是透明通道保证 |
| Meshy 3D | `/meshy/openapi/v1/image-to-3d`；原生 `/meshy/openapi/v1/multi-image-to-3d` 支持 image_urls；MCP image 仅单图 | 多图不是一致性验收；不能将未暴露字段塞进 MCP 并宣称支持 |
| Meshy 后处理 | MCP `remesh/rig/animate`；rig 接 task/model URL 和 height_meters；animate 接 rig_task_id/action_id；有 GLB/FBX 输出 | 不是通用角色拓扑、指骨/布料/非人形保证；预设 action_id 不是文本定制动作；没有 MD3 输出证据 |
| Hunyuan3D | `/v1/3d/tasks` 的 shape、shape+texture、texture-only；后者接 image、mesh GLB、mesh_sha256 | 单图路线，没有对外多视图/绑骨/动作输入；texture-only 不接受已有 skin/animation/morph，不能放在最终动作烘焙后 |
| 视频 | 异步视频任务输出 MP4 | 不等于可以提取可交付骨骼动作 |

Hunyuan texture-only：自包含 GLB ≤8 MiB，单 scene/node/mesh、identity transform、1–40000 实际三角形；输入不含纹理资源、层级、skin、animation、morph。image 为 PNG/JPEG/WebP data URL ≤8 MiB、边长16–4096、≤1600万像素。UV、索引、法线可能重建，因此 **修几何→贴图→最终拓扑/UV验收→绑骨→冻结→烘焙**。保留修模母版，不把几何不变误解为顶点序列不变。

参考 Blender 示例 `examples/teldrassil/tools/blender-humanoid-backup-rig.py`：能导入 GLB、按硬编码人体切片绑骨、制作 idle/walk/run/attack/hit/death、输出 NLA GLB 和 blend；其报告仍 `accepted:false`。`blender-hunyuan-review.py` 统计与拍视图，仍 `runtimeAccepted:false`。它们不含已验证 MD3 导出链，硬编码路径/比例不能直接复用；其中程序构造可见法杖也不能绕过本项目图生 3D 要求。

## 6. 生成 manifest、幂等与预算批准

以下 YAML 是未来 runner 的**设计规范示例，不是可直接执行的 API 请求**。runner 必须按 provider 白名单转换，禁止把内部预算、批注、引用路径传上游。

```yaml
schema_version: 1
asset_id: env.arch.gateway_panel.a
revision: 1
style_version: industrial-arena-v1
rights_review: pending
dependencies: []
brief: briefs/env.arch.gateway_panel.a.md
units: {source: meter, target: q3_unit, units_per_meter: 40}
views: {front: null, rear: null, left: null, right: null, hero: null}
reference_licenses: []
prototype_approval: {reviewer: null, at: null, image_sha256: null}
generation:
  provider: meshy
  route: /meshy/openapi/v1/image-to-3d
  api_parameters: {image_url: null, should_texture: true}
  operation_id: null
  request_sha256: null
  task_id: null
  state: blocked
  attempt: 0
budget:
  approval_id: null
  approved_by: null
  currency: USD
  quoted_unit_price: null
  max_paid_submissions: 0
  max_total_cost: 0
  expires_at: null
outputs: {raw: [], blend: null, runtime: [], sha256: {}}
export: {profile: md3-static-v1, tool_version: null, source_revision: null}
limits: {triangles_lod0: 2000, materials: 2, texture_edge: 1024}
quality: {machine_report: null, art_review: null, engine_review: null}
provenance: {provider_terms_snapshot: null, actual_cost: null}
```

状态机：`blocked → ready → submitting → queued → in_progress → downloaded → art_review → blender_ready → engine_ready → accepted`。另有 `submission_unknown / failed / rejected / quarantined / superseded`。前置图、权利、预算任一未批准则 blocked；供应商 completed 只允许进入下载阶段，不能直接 accepted。

提交前持久化 operation_id、规范化参数 hash、输入内容 hash、批准额度和预留费用；每个阶段独立 task，refine/remesh/rig/animate 均视为可能新增付费。服务端凭证只在可信 runner 使用 `OG_AI_GATEWAY`，不进浏览器、日志、manifest；带签名 URL 也要脱敏，不能归档为公开来源链接。

- **安全恢复**：已取得 task ID 只恢复 GET；轮询退避、遵守 Retry-After、单任务顺序查询。下载失败/URL过期/MCP 25 MiB 限制不触发重新生成，先恢复认证下载或原始任务输出，再验证文件 magic、长度、hash。
- **不明提交**：超时且无 task ID → submission_unknown，停止自动 POST，核对任务与账单。Meshy 幂等受用户、operation、token 摘要作用域影响；pending claim 10 分钟过期等窗口不能保证 exactly-once。换 token/key 不作为恢复手段。
- **质量重试**：拒绝原因分类为原型不一致、几何、纹理、rig、动画、格式；先判断 Blender 修复是否足够，再申请新付费 attempt。同参数重复提交不是修复策略，人工拒绝不等于供应商退款。
- **Hunyuan 恢复**：202 是受理，状态 queued/in_progress/completed/failed；同账号/token/key及相同请求可恢复原任务；默认 5–10 秒轮询，排队亦计入一小时期限；无新增取消 API，不承诺立即止损。
- **预算**：图片、模型、重网格、绑定、每个动作、贴图、宣传图分别报价。批准项包含币种、账号/组、模型版本、单价时效、数量、重试池、硬上限、审批人、有效期；额度用“已花费+在途预留+新任务最坏费用”计算，多 worker 原子扣预留，达到上限停止提交。不预先花掉预计退款。
- **重试默认**：自动新增付费次数为 0；只读轮询/下载可有限重试。批准可以一次授予限定 retry pool，而非每次都询问；改变模型、输入、单位价格、任务数量或超额必须重新批准。

仓库报价线索仅供申请预算：Hunyuan 默认组 shape $0.10、texture-only $0.40、一键 $0.50；Grok Image 默认配置 0.04，但实际账号价格须重新确认。Meshy 各操作价格/组倍率未核实，GPT token ratio 不能当固定每张报价。样件报价表未填满，不开始计费。“免费查询”也不意味无限并发；限流错误不得升级成新生成任务。

## 7. Blender：静态资产与角色分开的加工线

### 7.1 静态场景、武器与道具

1. 导入隔离区，保留原始字节；核对视图、尺度、开口、左右和来源。处理浮岛、内部面、非流形、反法线和丢贴图；不把自动 remesh 视为验收。
2. 重拓扑保大轮廓、连接口与轮廓转折；地形和建筑拆为可复用组件，不能靠每个地图整块生成获得可靠拼缝。门、电梯、转轴件分开，pivot 与逻辑实体对齐。
3. UV 展开/重排、统一密度、足够 mip padding；必要时高模到低模烘焙 base/normal/AO/roughness/metal/emissive，人工除去高光/阴影污染。镜像 UV 的法线和文字类纹理独立检查。
4. 创建人工控制的 LOD0/1/2，初始比例100/50/25%，连接边/枪口/tag不漂移；碰撞用独立 brush/clip 壳，不把碎片细节用于阻挡玩家。
5. 静态可见 MD3 用一帧；地图编译器可支持的模型输入格式必须先核实并做样件转换，不能假定 q3map2 可以读任意 GLB/MD3。固定建筑可烘入 BSP，互动/可动件保留适合引擎的模型/brush entity。
6. 导出并重新导入检查，运行时测试 LOD、法线、材质与贴地；长期保存 `.blend` 和可复现无 UI 导出流程。Blender 版本及 MD3 插件版本在样件阶段选定、验证、冻结；目前没有“已验证插件”的承诺。

### 7.2 角色与骨骼动作

1. 验收姿态和解剖后修拓扑：肩/肘/膝/髋变形环、面部与手指、衣服厚度及关节可动空间。自动绑骨仅作为初稿；人工做极限姿态测试、权重归一化、去无效骨、清穿插。
2. 母版统一骨命名、rest pose、骨长、关节朝向、root 与挂点；先复用同骨架制作可行性，再谈不同体型重定向。非双足/特殊装备走专用人工 rig，不强塞 Meshy 人形假设。
3. 动作来源可为获批预设、合法动作捕捉或人工关键帧；逐个登记许可、fps、帧区间、循环帧数、接地事件、武器事件。游戏移动驱动位置，默认 in-place，移除 root translation，不能用生成 root motion 改写物理。
4. 完整动作覆盖 `bg_public.h` 的 BOTH_DEATH/DEAD 三组、TORSO_GESTURE/ATTACK/ATTACK2/DROP/RAISE/STAND/STAND2、LEGS_WALKCR/WALK/RUN/BACK/SWIM/JUMP/LAND/JUMPB/LANDB/IDLE/IDLECR/TURN、队伍手势与旗帜/派生腿部动作。区分文件显式项和 cgame 派生项，按固定枚举而不是随意命名写 animation.cfg。
5. `animation.cfg` 每行 firstFrame/numFrames/loopFrames/fps；遵守腿部帧偏移、负帧数倒放和 parser 兼容规则。动作采样率不是游戏逻辑 tick；以引擎插值效果和帧数预算决定，先试24/30 fps，死亡和关键接触点单独核查。
6. 冻结拓扑后烘焙逐帧 evaluated mesh，拆 `lower.md3/upper.md3/head.md3`；在 lower 放 `tag_torso`、upper 放 `tag_head` 和需要的 `tag_weapon`。逐帧烘焙 tags 变换，保持腰/颈接缝在混合上半身攻击与下半身移动时成立。
7. 交付 skin、团队 skin、icon、完整帧表和附件。第一人称武器/手臂须先调查 `cg_weapons.c` 自身摆动和 frame 逻辑；不假定它直接消费玩家动作表，必要代码适配是另一明确工作项。
8. 测试站立/蹲跑/跳跃射击、切枪、倒退、死亡、复活、斜向移动、持不同武器及不同队色。检查脚滑、穿插、挂点抖动、首尾循环跳变和插值中间帧；只看关键帧不算验收。

MD3 导出样件失败时，先修导出器或重新评估 IQM 分支所需的 cgame/挂点/帧表改造；不得在批量生成后才发现无法交付。IQM 可以减少顶点帧体积，但必须单独验收浏览器加载、皮肤、动画混合与 tag，不能只换文件后缀。

## 8. 材质、VFX、声音与手感

PBR 母版保留独立 base color（色彩）、normal（线性数据及绿通道约定）、roughness、metallic、AO、emissive、opacity。交付 texture 格式须由引擎读取和 Web 样件验证；禁止直接用 KTX2/glTF sampler/ORM 假定引擎能读。法线用 Blender 烘焙与引擎切线方向样件确认。

- 传统包：diffuse + lightmap/vertex lighting，必要透明、发光、动画贴图用既有 shader 语法；GL1 的 `.shader` 不放 GL2 专用 stage。
- GL2 包：对应同 basename `.mtr` 与 `.shader` 一起交付。GL2 从 `.shader` 枚举并优先读对应 `.mtr`，所以仅有孤立 `.mtr` 不够。
- 非 PBR specular：RGB 为法向反射率，A 为 gloss；PBR specular：R 为 gloss、G 为 metallicness。roughness→gloss 转换须绑定 `r_glossType`/实际宏模式：可能是指数 gloss、smoothness、roughness 或 shininess，**不是一律 1−roughness**。转换配置与 renderer cvars 一起版本化，使用0/0.25/0.5/1粗糙度梯度和金属/非金属样板实测。
- `_n/_nh/_s` 自动发现仅适用于符合条件的受光 stage；不依赖其覆盖全部材质。AO 合并避免重复压暗；透明、双面、alpha test、mip 边缘与发光强度独立验收。
- VFX 以事件表绑定射击/命中/落地/拾取等，预算记录同时存活数、粒子数、透明屏幕覆盖、持续时间。强光和烟不能遮住准星/目标识别；闪烁可访问性、音画同步和低画质回退单列验收。
- 声音无损母版、运行格式样件、声道/采样率/循环缝、峰值和混音总线统一，枪声尾音不吞脚步/命中信息。未核实平台音效生成合同，不承诺已有可用音频 API；人工录制/合成/获授权采购是独立批准路线。
- 手感测试冻结移动/跳跃/射速/伤害/碰撞等玩法参数，单独调枪模摆动、反冲视觉、命中声、粒子、动画前后摇。对照事件时间轴，装饰动画不得增加输入延迟或改射击判定；如确需玩法偏离，单独批准并记录。

## 9. 地图逻辑和视觉分离

每地图保存 `logic_layout` 与 `visual_assembly` 的版本和变换对应关系。逻辑层包含尺寸、brush/clip、contents/surface flags、出生/物品/目标点、触发器、门电梯路径、危险区域、VIS分区和 bot 导航；视觉层引用经过批准的组件、灯光和装饰。使用相同坐标基准，源文件组织方式在地图工具样件阶段确定，不要求引擎支持额外运行层格式。

先用不公开的逻辑灰盒验证路线、跳跃距离、视线、资源节奏和 bot；灰盒是测试夹具，不是最终可见资产。视觉替换不可侵入玩家通行壳、阻挡弹道、制造假掩体；对可见和碰撞的差异设置尺寸容差并人工走测。发光装饰不能伪装成可拾取物，透明面不能意外阻挡射击。

构建链固定兼容 Q3 BSP 的编辑器/编译器、版本、参数、依赖许可；执行几何→VIS→光照→导航构建。q3map2/bspc 等为候选待验证依赖，不声称当前 orb 已有可用工具。大生成网格拆分和封闭壳保证叶节点/PVS效率，避免全图可见、漏光、穿墙、bot 卡死。每次换视觉都运行碰撞/实体表对比及固定路径回放。

## 10. 批量流水线、阶段与依赖

`权利清单 + 风格/尺寸 → 原型批准 → 预算批准 → 图生3D → 归档校验 → Blender静态/角色线 → 格式检查 → BSP/PK3构建 → WASM → 人工玩法/视觉 → 发布批准`。

调度器以资产依赖 DAG 运作；只有已批准原型能进入生成队列。按 provider 限流及本机内存设置并发，先单个任务确认报价/恢复，再逐步增加；Blender 分进程但不同资产目录隔离。每个 task 使用临时目录，校验通过后原子晋升；失败隔离，不覆盖上个已验收版本。按输入 hash+参数+工具版本缓存**本地加工**，缓存生成结果必须有相同来源/授权，不跨预算静默创建请求。

| 阶段 | 完整交付 | 放行依赖 |
|---|---|---|
| P0 盘点与法律 | 全槽位inventory、参考许可、style bible、浏览器/硬件基线、预算表 | 商业数据隔离；确定什么能用于原型/生成/公开 |
| P1 技术样件 | 一件模块建筑、一件近景武器、一名可动画角色，各自全链；一处透明/发光/法线样板 | 有效的单批费用批准；MD3导出器、地图编译、GL2材质、WASM内存实测 |
| P2 纵向闭环 | 一张完整可玩的地图、一套玩家、代表性武器/物品/音效/HUD；启动→对战→死亡复活→结算重开 | P1全部通过；独立页/嵌入页和性能通过，不代表删减后续范围 |
| P3 长期全量 | 按资产族/地图分批交付所有槽位、全部动画武器特效、声音、UI、本地化 | 每批预算和风格锁定；复用模块/骨架的变更传播；覆盖率持续更新 |
| P4 整体收敛 | 跨地图性能、画质档、可访问性、玩法回归、全部来源和对应源码 | 零未知来源、零占位；技术和法律双签 |
| P5 授权上线 | 平台预检、独立/嵌入测试、封面海报、一次经授权发布及发布后检查 | 用户明确授权费用和发布；身份、license、source URL及可回退包齐备 |

黄金样件锁定后，每批按组件族复用材质/骨架/连接口，避免每件独立风格。周/月生产量由实测“人工修复工时+通过率+账单”估算，不以 API 生成速度冒充全量制作工期。资产删除/替换要沿 DAG 查 UI icon、shader、声音、地图与动作依赖，不能留孤儿引用。

## 11. 可执行验收合同（工具尚待实现）

后续建议命令接口：`assetctl validate <manifest>`、`assetctl export --asset <id>`、`assetctl package --profile web`、`assetctl verify --profile web`。这些命令当前不存在；实现归属为后续工程工作，不应复制执行后把 command-not-found 当环境问题。每项产出 JSON 报告+工具版本+输入/输出 hash，人工报告给出审核人、版本和证据；任何红项阻止 accepted。

| 验收层 | 具体执行/输入 | 通过标准 |
|---|---|---|
| manifest/权利 | schema检查、依赖拓扑排序、每件图→生成→blend→runtime hash链核对 | 无缺字段/循环依赖/未知公开权利；批准仍有效；无密钥或私有签名URL |
| API恢复 | 假服务注入429、500、提交超时、重复响应、过期下载；不使用计费端点做故障注入 | 不超额、不重复付费POST；unknown停单；只读恢复不丢原任务 |
| 静态几何 | Blender headless导出后重读；非对称朝向模型、负缩放、UV seam试件 | 轴/尺寸/pivot一致；无意外法线、缺图、裂缝；LOD不丢连接口 |
| MD3 | 解析header/offset/count、逐帧bbox/tag/顶点/法线、skin路径 | 格式上限以内、无越界/NaN、所有帧一致拓扑，tag正交且连续，量化误差≤1/64 Q3 unit（按坐标分量） |
| 角色 | 所有动作和组合；循环首尾/中间插值帧；上下身独立播放 | 帧表索引有效、无缺动作、挂枪/腰颈接缝稳定；跑跳射击/死亡复活无错帧，人工确认无明显穿插/脚滑 |
| 材质 | 固定曝光灯光测试室；粗糙度/金属梯度、法线凹凸标记、透明边、GL2/传统对照 | 无defaultShader/缺图；通道方向正确；GL2关闭高级项仍可辨识，截图人工签收 |
| 地图 | BSP读取、实体/碰撞比较、漏点检查、固定路线与bot循环 | v46可加载、无leak/出界/卡门；视觉不改变走位/弹道；所有出生/目标/拾取均可达 |
| 包体 | PK3/虚拟FS大小写与路径检查，追踪shader/模型/声音引用，断网加载缓存包 | 无缺依赖、绝对路径、商业pak、秘钥、热链；版本和hash确定，干净环境可重建 |
| 网页 | Chrome/Edge/Firefox稳定版，Windows集显基线；补测macOS Safari，独立/平台iframe两种环境 | 首个可玩帧后ready；点击锁鼠/音频恢复/焦点丢失/全屏退出/缩放/设置重开正确；控制台无加载或GL错误 |
| 手感 | 固定移动/武器事件回放+高帧率录屏，验证首次输入、连射、切枪、受击、音画事件 | 玩法时序与批准基线一致；画面/音频不阻塞输入，无视觉假命中；时间差目标冻结后执行 |
| 全量 | inventory required槽位和被引用文件双向核查 | 全部验收，零占位，零遗失来源；不可达资产解释或去除，不为覆盖率而造空条目 |

性能初始目标（P1用实测硬件冻结）：1080p低/中档、8名角色压力场景、目标60fps，p95帧耗≤16.7ms、p99≤33.3ms；WASM峰值占用≤配置256 MiB的80%，把预加载FS、纹理解码、模型帧、音频计入，GPU内存单独估计/记录。初始运行预算：小道具LOD0≤2k三角/2材质/1k纹理，模块≤4k/2材质，玩家整体≤8k三角/4材质/1k为主，第一人称武器≤6k/3材质/2k以内；MD3仍按每surface实际拆点后计数。预算不能代替场景实测。

初始首场景压缩传输目标≤40 MiB，在受控20 Mbps/80ms冷缓存下首个可玩帧≤25秒，热缓存≤5秒；记录实际网络条件与TTI，不能只展示下载结束。若固定256 MB容不下，不静默增内存：先检查全量预加载、动画体积、纹理解码峰值和资源分批策略，再单独批准构建/加载改动。浏览器自动化没有真实GPU时只能验证功能，性能必须在约定PC补测。

截图和Blender报告只能证明所见状态；最终必须进入 ioq3 WASM 拍摄同一姿态/材质/场景，并人工玩代表性动作。P1之前不承诺这些目标已达成。

## 12. 授权、来源与发布前最后关卡

来源清单分别记录参考作者/URL/获取时间/许可证副本、是否允许生成输入/衍生/商用/再分发、供应商模型与条款版本、实际账号资格、raw hash、人工作者与修改、最终文件hash、批准人及撤回影响。公开许可页只暴露必要署名与许可，不包含密钥、账单私密信息或签名链接。AI输出的授权需审核，不能填默认CC0；Hunyuan还有地域/主体/协议和非关联声明要求。

GPL引擎与商业游戏数据分开；必须提供适当许可、修改说明、可获得的对应源码及构建材料。Origin deploy helper默认 `protected`，不能盲用；未来选择适合GPL的 `open/license_name/source_url` 等字段并确认真实合规，平台字段不是法律替代品。

上线前重新读最新 deploy/generate skill、deploy.sh 与 Gateway文档。浏览器包根 `index.html`、相对路径，加载时接 `OG.loading.*`，首个可玩帧调用 `OG.ready()`，全屏走 `OG.fullscreen()`，同时支持无OG独立运行；实现桥接属于后续工作。发布用项目根 `.origingame-deploy.json` 的既有 creator及命名密钥，构建目录变更不换身份、不在浏览器放 Gateway key。无gameId不伪造；经授权首次发布后才记录返回ID/URL。部署超时先核对状态，helper无自动幂等保证，不盲重发。

当前阻塞：商业权利、风格/尺度批准、账号报价和付费批准、已验证MD3导出链、地图工具链、Emscripten版本固定、真实PC浏览器性能、平台嵌入集成。均不能由“API支持生成”代替人工和工程验收。

## 13. 核验来源与证据边界

本地源码：`code/qcommon/qfiles.h:73–155,300–320`；两套 `tr_model.c:185–365`；`code/cgame/cg_players.c:84–290,517–615,2338–2358,2564–2584`；`cg_weapons.c:1240–1262`；`code/game/bg_public.h` 动画枚举；`code/qcommon/cm_load.c:569–665`；`code/renderergl2/tr_bsp.c:2740–2795`；`tr_init.c:1295–1328`；`tr_shader.c:3790–3837`；`glsl/lightall_fp.glsl:385–425`；`cmake/platforms/emscripten.cmake`；`code/web/client.html.in`。行号以本次快照为准。

Origin Game远程来源（main会变化，执行时需固定版本）：

- [Gateway文档](https://github.com/fran0220/origingame/blob/main/docs/origin-gateway.md)、[Hunyuan工作流](https://github.com/fran0220/origingame/blob/main/docs/hunyuan3d-workflow.md)。
- [部署skill](https://github.com/fran0220/origingame/blob/main/skill/origingame-deploy/SKILL.md)、[deploy.sh](https://github.com/fran0220/origingame/blob/main/skill/origingame-deploy/scripts/deploy.sh)、[生成skill](https://github.com/fran0220/origingame/blob/main/skill/origingame-deploy/skills/core/using-origingame-generate/SKILL.md)、[资产skill](https://github.com/fran0220/origingame/blob/main/skill/origingame-deploy/skills/core/using-origingame-assets/SKILL.md)。
- [MCP生成参数与输出处理](https://github.com/fran0220/origingame/blob/main/packages/origin-mcp/src/service.ts)、[Meshy路由](https://github.com/fran0220/origingame/blob/main/gateway/relay/channel/meshy/native.go)、[任务输出](https://github.com/fran0220/origingame/blob/main/gateway/relay/channel/meshy/task.go)、[幂等实现](https://github.com/fran0220/origingame/blob/main/gateway/service/idempotency.go)、[幂等持久化](https://github.com/fran0220/origingame/blob/main/gateway/model/idempotency.go)。
- [Blender绑定示例](https://github.com/fran0220/origingame/blob/main/examples/teldrassil/tools/blender-humanoid-backup-rig.py)、[Blender检查示例](https://github.com/fran0220/origingame/blob/main/examples/teldrassil/tools/blender-hunyuan-review.py)、[多图客户端示例](https://github.com/fran0220/origingame/blob/main/examples/jiangnan-town/tools/assets/stylized-architecture/meshy.mjs)。

本次完成的是文档/源码核验与生产规划，没有运行真实生成、MD3导出、WASM构建、Blender或平台发布测试；任何供应商质量与实测性能均未获本次验证。
