# sing-box-muts — 薄 fork 基座档案

本仓库是 [SagerNet/sing-box](https://github.com/SagerNet/sing-box) 的薄 fork，目标是在客户端侧支持 **XHTTP 传输** 与 **VLESS encryption（mlkem768x25519plus）**，两个上游不存在且无法通过配置层覆盖的特性。薄 fork 纪律与 rebase 流程见 [docs/fork-maintenance.md](docs/fork-maintenance.md)。

## 基座（随上游 tag 更新时同步修改本段）

| 项 | 值 |
|---|---|
| 上游基座 tag | `v1.13.19` |
| 上游基座 commit | `b5ebaa1fc0f2b94256180b95468e73ef53caa27d` |
| 基座发布时间 | 2026-08-17（选型日 2026-08-20 时的上游最新稳定版） |
| 上游 remote | `https://github.com/SagerNet/sing-box` |
| 主干分支 | `muts-main`（从基座 tag 切出，fork 改动只进此分支） |

## 移植来源

| 项 | 值 |
|---|---|
| 来源仓库 | [Leadaxe/sing-box-lx](https://github.com/Leadaxe/sing-box-lx) |
| 参考 ref | tag `v1.14.0-lx.26` |
| 参考 commit | `3fffb0dee43b00bcc69c859ca082bca7217171bf`（2026-08-14） |
| lx 与上游分叉点 | `b0491faeee1c841df06959ce47a3e59b721c01be`（上游 main，介于 1.14.0-beta.16/17 之间；该 commit 亦包含于 v1.13.19） |
| 移植清单 | [docs/porting-checklist.md](docs/porting-checklist.md) |

**基线漂移提示**：lx 的代码基于上游 main（≈1.14.0-beta.17），本 fork 基座是 v1.13.19 stable。移植（MUTS-9 / MUTS-10）必须按内容搬运并对照本基座代码审查，禁止盲目 cherry-pick。

VLESS ENC 在 lx 中亦非原创：lx 的 `protocol/vless/encryption` 移植自 [starifly/sing-box](https://github.com/starifly/sing-box)（同为 GPL-3.0），wire 行为对标 Xray-core v25.8.3+ 的 VLESS `encryption` 字段。

## 许可证

GPL-3.0，与上游 sing-box、sing-box-lx 一致。fork 新增文件沿用 GPL-3.0。

## 特性开关（build tag）

| tag | 特性 | 落地 issue | 接入点 |
|---|---|---|---|
| `with_xhttp` | XHTTP 客户端传输 | MUTS-9 | `constant/v2ray.go`（常量）+ `transport/v2ray/transport.go`（分发切口）+ `transport/v2ray/xhttp.go` / `xhttp_stub.go`（tag 对） |
| `with_vless_enc` | VLESS 协议层加密（outbound `encryption`） | MUTS-10 | `protocol/vless/encryption/`（`NewInstance func(spec string) (Instance, error)` 钩子，tag 对安装）+ `protocol/vless/vless_enc.go` / `vless_enc_stub.go`（outbound 接线 tag 对） |

`with_xhttp` 仍为**骨架 stub**：编译通过；由于 option schema 尚未落地，引用 `xhttp` transport 的配置目前在**解码层**即被上游错误拒绝（`unknown transport type: xhttp`），与上游行为逐字节一致、无静默降级；MUTS-9 补齐 schema 后，stub 的 "feature not ported yet" 显式报错才可达。`with_vless_enc` 已由 MUTS-10 落地：tag 开时 `encryption` 配置正常生效，tag 关时该配置在 outbound 构造期显式报错（不静默降级为明文），`encryption: none` 或缺省则与上游行为一致。tag 全关时二进制行为与上游同基座 tag 等价。

## 构建

```sh
# 全关（与上游等价）
go build ./cmd/sing-box
# 全开
go build -tags "with_xhttp,with_vless_enc" ./cmd/sing-box
```

CI 矩阵与验收见 `.github/workflows/fork-ci.yml` 与 `docs/fork-maintenance.md`。
