# 移植清单：sing-box-lx → sing-box-muts

本清单是 **MUTS-9（XHTTP outbound）与 MUTS-10（VLESS ENC outbound）的直接输入**。

- 移植来源：`Leadaxe/sing-box-lx`，参考 ref `v1.14.0-lx.26`（commit `3fffb0dee43b00bcc69c859ca082bca7217171bf`）。
- lx 与上游分叉点：`b0491faeee1c841df06959ce47a3e59b721c01be`（上游 main，≈1.14.0-beta.16/17 之间）。
- 本 fork 基座：`v1.13.19`（stable）。**基线漂移警告**：lx 代码基于上游 1.14.0-beta 线，与本基座存在结构差异，必须按内容移植并对照 v1.13.19 代码审查，禁止盲目 cherry-pick。
- 下表仅列**触及代码**的 commit；lx 仓库中对应的 SPECS/ 设计文档目录（如 `SPECS/TASKS/002-XHTTP_CLIENT_TRANSPORT/`、`SPECS/TASKS/032-VLESS_ENCRYPTION_MLKEM768/`）包含 PARAM_MAP、互通验证记录，移植时应一并阅读但不搬入本仓库。
- 纪律提醒：移植即审查——padding、mode 协商、0-RTT ticket 等参数解析必须与 Xray 最新稳定版源码逐字段对齐后再落库。

## 1. XHTTP（MUTS-9，build tag `with_xhttp`）

按依赖顺序排列；每条标注归属与触及的代码文件。

| # | commit | 日期 | 内容 | 触及代码文件 | 状态 |
|---|---|---|---|---|---|
| 1 | `e111f800` | 06-09 | 客户端 transport registry（`registry.go`） | `transport/v2ray/registry.go`（新增，64 行） | ✅ 已适配（不照搬 registry，用骨架既有的 `xhttp.go`/`xhttp_stub.go` 钩子 tag 对等价接入，见落地说明） |
| 2 | `2d97ff56` | 06-09 | registry 接入 `NewClientTransport` + xhttp 常量 | `transport/v2ray/transport.go`、`constant/v2ray.go` | ✅ 已适配（骨架已含 `default:` 分支切口与常量，本 issue 仅把钩子 stub 替换为真实构造调用） |
| 3 | `d1b434fc` | 06-09 | **核心**：lean-native XHTTP 客户端传输 | `transport/v2rayxhttp/{client,conn,register}.go`（新增包）、`option/v2ray_transport.go`（切口）、`option/v2ray_xhttp.go`（新增）、`include/v2rayxhttp.go` | ✅ 已移植（`register.go`/`include/v2rayxhttp.go` 由钩子模式取代，不移植；其余按内容搬入并加 `with_xhttp` tag） |
| 4 | `7bec034e` | 06-09 | sessionId 对齐 dashed UUID；padding 位置考证 | `transport/v2rayxhttp/client.go` | ✅ 已移植 |
| 5 | `5a398a5e` | 06-09 | padding 位置修复（x_padding 进 Referer）+ auto→packet-up，**已对真实 Xray 服务端活体验证** | `transport/v2rayxhttp/client.go` | ✅ 已移植 |
| 6 | `f2654e6a` | 06-21 | stream-one 下行修复（裸 path、无 sessionId）+ REALITY 下 auto→stream-one | `transport/v2rayxhttp/{client,conn,reality_detect}.go` | ✅ 已移植 |
| 7 | `4df8cf19` | 06-21 | 测试 + auto-reality 检查配置（SPEC 011） | `transport/v2rayxhttp/{reality_detect_test,url_test}.go` | ✅ 已移植 |
| 8 | `33ee291b` | 06-29 | **SPEC 002 v2**：扩展 XHTTP 参数全量客户端支持（placement/obfs/tokenish padding） | `transport/v2rayxhttp/{client,conn,meta,xpadding}.go` + 2 测试文件、`option/v2ray_xhttp.go` | ✅ 已移植 |
| 9 | `75274679` | 06-30 | 接受 legacy 参数 `sc_max_concurrent_posts`（忽略不报错） | `option/v2ray_xhttp.go` | ✅ 已移植 |
| 10 | `c0bbb1c5` | 07-01 | `uplink_http_method=GET` 在非 packet-up 下软回退 POST | `transport/v2rayxhttp/meta.go` + 测试 | ✅ 已移植 |
| 11 | `844ae936` | 07-02 | 移除 streamConn.Read 的竞态快路径（SPEC 022 #7） | `transport/v2rayxhttp/conn.go` | ✅ 已移植 |
| 12 | `3f0cfd87` | 07-20 | 保留 XHTTP path 尾部斜杠（修反向代理 301） | `transport/v2rayxhttp/{client,meta}.go` + 测试 | ✅ 已移植 |
| 13 | `497f0fc0` | 08-01 | streamed-body 请求发送 `Content-Type: application/grpc`（SPEC 042） | `transport/v2rayxhttp/{client,conn}.go`、`option/v2ray_xhttp.go` + 测试 | ✅ 已移植 |
| 14 | `165c091a` | 08-01 | stream-one path 保留尾部斜杠（SPEC 043） | `transport/v2rayxhttp/meta.go` + 测试 | ✅ 已移植 |
| 15 | `ead09967` | 08-11 | **dial 死锁修复**：packet-up/stream-up 不再等待 download 响应（SPEC 061） | `transport/v2rayxhttp/conn.go` + `dial_deadlock_test.go` | ✅ 已移植 |
| 16 | `e3b7ff4a` | 08-11 | **XMUX**：HTTP 连接复用（SPEC 059） | `transport/v2rayxhttp/{client,conn,meta,xmux}.go` + 3 测试文件、`option/v2ray_xhttp.go`、`option/v2ray_xhttp_xmux_range.go` + 测试 | ✅ 已移植 |

**与本骨架的对接说明**：lx 的 #1/#2 用 registry 重构了 `transport/v2ray/transport.go`；本骨架已用更小的 `default:` 分支钩子（`transport/v2ray/xhttp.go` / `xhttp_stub.go` tag 对）实现等价隔离。**移植时不要把 registry.go 照搬进来**——用真实实现替换 `xhttp.go` stub 的报错体即可；`constant/v2ray.go` 的常量已就位。

可忽略commit（docs 批次顺带触及代码，仅注释/路径级改动）：`09944c01`、`022d9135`（P3 卫生审计，`option/v2ray_xhttp.go` 与 `transport/v2rayxhttp/{client,meta}.go` 的注释清理）、`089d8f40`（SPECS 路径改名，代码文件每文件 1–2 行注释引用更新）。

**MUTS-9 落地说明**（2026-08-20）：

- 文件落位：新包 `transport/v2rayxhttp/`（`client` / `conn` / `meta` / `xpadding` / `xmux` / `reality_detect` + 7 个测试文件）与 `option/v2ray_xhttp{,_xmux_range}.go` 全部置于 `with_xhttp` tag 后；lx 仅 `register.go` 带 tag，本 fork 按红线整包隔离。lx 的 `register.go` / `include/v2rayxhttp.go` 不移植——骨架既有 `transport/v2ray/xhttp.go` / `xhttp_stub.go` 钩子 tag 对承担等价注册职责，本 issue 把钩子体从"未移植报错"替换为真实构造调用。
- option 层 gating：`option/v2ray_transport.go` 的字段与两个 switch case 均在 fork-patch 标记内，case 体调用 tag 对钩子（`option/v2ray_xhttp.go` / `v2ray_xhttp_stub.go`）。tag 关闭时解码路径逐字节复现上游 `unknown transport type: xhttp` 错误（fork-test 负例断言），tag 开启时 schema 生效。
- **对 Xray 最新稳定版（v26.7.28）逐字段核对结论**：sessionId（dashed UUID、stream-one 为空）、mode auto 解析（Reality→stream-one，否则 packet-up）、padding 默认（非 obfs 走 Referer 头 `x_padding` 查询参数，100-1000）、streamed-body 的 `Content-Type: application/grpc`、sc_* 默认值、uplink key 默认值（X-Data / x_data）、placement/key 默认值（X-Session / X-Seq / x_session / x_seq）、xmux 互斥约束——全部一致，无需纠正。
- 两处与 v26.3.27 相比的 Xray 侧演进，lx 实现天然对齐：a) `GetNormalizedPath` 尾部斜杠改为仅在 session/seq 有 path placement 时追加——正是 lx `barePathForStreamOne` 的条件；b) xmux 空配置的默认从 `maxConcurrency=1-1` 改为 `maxConnections=3-3`——**本 fork 保留 lx/sing-box-extended 的 `maxConcurrency=1-1` 默认**：纯客户端连接池策略，服务端按 sessionId 路由、无 wire 影响，且 lx 默认已经真机验证；差异在此记录备查。

## 2. VLESS-ENC（MUTS-10，build tag `with_vless_enc`）

| # | commit | 日期 | 内容 | 触及代码文件 | 状态 |
|---|---|---|---|---|---|
| 1 | `57ece01c` | 08-01 | **核心**：mlkem768x25519plus 加密层（SPEC 032），已对 12 个真实节点设备验证 | `protocol/vless/encryption/{client,common,lx_support,xor}.go`（新增包，本 fork 需改为 tag 对）、`protocol/vless/lx_encryption.go`（解析+wrap）、`protocol/vless/lx_encryption_test.go`、`option/vless.go`（+`encryption` 字段）、`protocol/vless/outbound.go`（切口） | ✅ 已移植（见下方落地说明） |
| 2 | `d1c2f3e2` | 08-05 | `wrapEncryption` 只设 write deadline——read 曾锁死 | `protocol/vless/lx_encryption.go` + `lx_encryption_deadline_test.go` | ✅ 已移植（终态即 write-only，含回归测试） |

**上游 provenance**：lx 的 `protocol/vless/encryption` 自身移植自 `starifly/sing-box`（同 GPL-3.0）；`lx_support.go` 是 lx 为摆脱 starifly 的 `common/xray/{cpuid,crypto}` 依赖写的本地替代。移植时以 lx 版本为准。

**与本骨架的对接说明**：lx 未给 VLESS ENC 设 build tag（常驻代码）；本 fork 要求 `with_vless_enc` 隔离——骨架已在 `protocol/vless/encryption/` 放好 `Layer` 钩子（tag 对安装），MUTS-10 需：a) 把 lx 的加密实现搬进该包并用 stub 替换位；b) 在 `option/vless.go` 加 `encryption` 字段（fork-patch 标记）；c) 在 `protocol/vless/outbound.go` 加标记切口调用 `encryption.Layer`。

**MUTS-10 落地说明**（2026-08-20）：

- 文件落位：实现搬进 `protocol/vless/encryption/`（`client.go` / `common.go` / `xor.go` / `support.go`（原 lx_support.go）/ `parse.go`（原 lx_encryption.go 的解析部分）），全部置于 `with_vless_enc` tag 后；骨架的 `Layer` 钩子重构为 `NewInstance func(spec string) (Instance, error)`（原签名拿不到 per-outbound 配置，无法承载解析后的实例）。`wrapEncryption` 与 `initVLESSEncryption` 落 `protocol/vless/vless_enc.go` / `vless_enc_stub.go` tag 对。
- 上游文件切口（均有 fork-patch 标记）：`option/vless.go` +`Encryption` 字段；`protocol/vless/outbound.go` 四处（import、struct 字段、NewOutbound 初始化、DialContext/ListenPacket 各一次 wrap 调用）。
- **对 Xray 最新稳定版（v26.7.28）逐字段核对时发现并纠正一处漂移**：lx/starifly 的 `DecodeHeader` 上限为 17000，Xray 最新稳定版为 16640（RFC 8446 §5.2：16384+256）——本 fork 对齐 16640，否则 0-RTT ticket 过期时服务端随机噪声可能被误读为合法长记录头而挂起读。完整对照表随 PR 描述交付。
- 边界 commit `4dcbb572` 的 vless 部分（握手带 deadline）以 `d1c2f3e2` 修正后的终态（write-only deadline）并入，不单独移植中间态。

## 3. 跨特性 / 边界 commit（评审决定归属）

| commit | 日期 | 内容 | 触及代码文件 | 建议 |
|---|---|---|---|---|
| `4dcbb572` | 08-05 | urltest 轮次可取消：XHTTP deadline、握手带 ctx、Close 里 cancel（SPEC 050） | `protocol/group/urltest.go`、`protocol/vless/{lx_encryption,outbound}.go`、`transport/v2rayxhttp/conn.go` + 2 测试文件 | **混合**：XHTTP 部分随 MUTS-9，vless 部分随 MUTS-10，urltest 改动属第三类——建议单独评估，不在 9/10 范围 |
| `f7341ce7` | 08-02 | 修复：trojan/vless 在 TLS disabled 时首次 dial 崩溃（SPEC 045） | `protocol/trojan/outbound.go`、`protocol/vless/outbound.go` | 上游 v1.13.19 是否有此问题需先核对；若上游已修复则跳过，否则作为独立修复提交（不属于 ENC 特性） |
| `a9ce4f9f` | 08-02 | 上述修复的 red/green 测试 | 2 个测试文件 | 同上 |
| `01c680d7` | 08-12 | detour 下 ClientHello 自动分片（SPEC 060） | `common/tls/client.go` + 6 个 outbound | **排除**：TLS 层特性，超出 MUTS-9/10 范围；触及 `protocol/vless/outbound.go`，rebase 时注意 |

## 4. 明确排除

- lx 的其余特性（AWG、masque、lxd 守护进程、observability、dns-group、urltest 平衡等）——与本项目无关，不移植。
- lx 的 `Makefile.lx`、CI、SPECS/ 文档体系——本 fork 有自己的构建矩阵（`.github/workflows/fork-ci.yml`）与本文件体系，仅作参考。
- 服务端侧（inbound）XHTTP 与 VLESS `decryption`——CEO 裁决范围外，二期再议。
