# Fork 维护手册：薄 fork 纪律与上游 rebase 流程

本文件是 sing-box-muts 的工程宪法。任何向本仓库提交代码的人都必须先读完本文件。基座信息见根目录 [FORK.md](../FORK.md)。

## 1. 薄 fork 纪律（红线）

### 1.1 新代码只进新文件 / 新包

- 特性实现一律放在新建的包或新建的文件中，例如 `transport/v2rayxhttp/`（XHTTP，MUTS-9）、`protocol/vless/encryption/`（VLESS ENC，MUTS-10）。
- 在上游包目录里新建 fork 自有文件（如 `transport/v2ray/xhttp.go`）是允许的——新文件在上游 rebase 时永不产生冲突。
- 禁止在上游已有文件中添加未标记的函数、类型、字段或改动上游已有行。

### 1.2 上游文件改动必须包在成对标记注释内

确需改动上游文件（注册点、常量、option 结构等）时，改动必须包在成对标记内：

```go
// fork-patch: begin <特性名>
<改动内容>
// fork-patch: end <特性名>
```

- `<特性名>` 取 `xhttp` / `vless-enc` 等短名，与 build tag 对应。
- 标记对内只放与上游逻辑正交的最小切口（一个 case、一个常量块、一次钩子调用）。复杂逻辑一律下沉到 fork 自有文件，标记内只做调用。
- 标记行本身不缩进逻辑、不改写上游既有行；优先选择"追加独立的 const/var 块"这类零侵入形式。
- 禁止散落改动：任何不在标记内的上游文件 diff 都是事故，评审必须打回。

### 1.3 当前切口清单（每次改动后必须更新本表）

| 上游文件 | 特性 | 切口内容 |
|---|---|---|
| `constant/v2ray.go` | xhttp | 追加独立 const 块：`V2RayTransportTypeXHTTP = "xhttp"` |
| `transport/v2ray/transport.go` | xhttp | `NewClientTransport` 的 `default:` 分支内调用 `newXHTTPClientTransport` 钩子 |

VLESS ENC 当前**零上游文件切口**：钩子 `encryption.Layer` 定义在 fork 自有包 `protocol/vless/encryption/` 中，MUTS-10 落地时才在 `protocol/vless/outbound.go` 增加标记切口。

### 1.4 build tag 隔离

- 每个特性一个 tag：`with_xhttp` / `with_vless_enc`。
- 特性代码按上游惯例组成 tag 对文件（`xhttp.go` + `xhttp_stub.go`，参照上游 `constant/quic.go`/`quic_stub.go`、`include/quic.go`/`quic_stub.go`）。
- **tag 全关时二进制行为必须与上游同基座 tag 等价**：tag 关闭路径不得改变任何既有错误文本、配置解析结果或连接行为。
- tag 开启但特性未落地时，配置引用该特性必须显式报错，禁止静默降级。

## 2. 分支与 tag 模型

- `muts-main`：fork 主干，从上游基座 tag 切出，全部 fork 改动进此分支。它是仓库默认分支。
- 上游通过 remote `upstream`（`https://github.com/SagerNet/sing-box`）只读跟踪，**不**向上游提 PR。
- fork 发布 tag 命名：`v<上游版本>-muts.<N>`，例如基于 v1.13.19 的第一个发布为 `v1.13.19-muts.1`。N 在同一上游基座内递增；换基座后归 1。
- 特性分支命名 `feat/<name>`，修复分支 `fix/<name>`，PR 进 `muts-main`。

## 3. 跟随上游 tag 的 rebase 流程

上游每个新**稳定版** tag 发布后执行（alpha/beta/rc 不跟，除非有安全修复）。负责人：发布工程师。

### 3.1 操作步骤

```sh
# 0. 确认上游新 tag，例如 v1.13.20
git fetch upstream --tags

# 1. 从当前 muts-main 切 rebase 工作分支
git checkout -b rebase/v1.13.20 muts-main

# 2. 把 fork 提交整体平移到新 tag 上
git rebase --onto v1.13.20 v1.13.19 rebase/v1.13.20
#    （v1.13.19 为旧基座；fork 提交数应极少，本命令预期秒级完成）

# 3. 解冲突（原则见 3.2），直至 rebase 完成

# 4. rebase 后验证（清单见 3.3），全绿后：
git checkout muts-main
git reset --hard rebase/v1.13.20
git push --force-with-lease origin muts-main

# 5. 更新 FORK.md 的基座 tag / commit / 发布时间，单独一个 commit 落在 muts-main
# 6. 删除 rebase 工作分支
```

若某次 rebase 冲突面大到按 3.2 原则无法干净解决（例如上游重写了切口所在函数），改用 merge 策略兜底：`git merge v1.13.20` 进 `muts-main`，冲突解决原则不变，并在 PR 描述中说明降级原因。

### 3.2 冲突处理原则

1. **fork 自有文件**（新包、新文件、`docs/`、`FORK.md`）：上游永远不会碰到；一旦出现冲突，说明误把代码写进了上游文件，停下来纠正。
2. **上游文件的标记切口**：冲突时**保留上游新版本的行为逻辑**，把我们的标记块重新套回对应位置。先理解上游改了什么，再决定切口是否需要跟着移动；禁止为保住旧切口而回退上游改动。
3. 上游新增的同特性实现（例如上游自己支持了 xhttp）：优先评估切换到上游实现、废弃 fork 切口——薄 fork 的终极目标是切口归零。
4. 拿不准的冲突：停下来，在 issue 中贴出冲突双方 diff 请人评审，禁止"差不多就行"式解决。

### 3.3 rebase 后验证清单（全部通过才算完成）

- [ ] `git diff v<新基座> --stat` 文件清单可控：上游已有文件仅含 `fork-patch` 标记块内的改动，其余全是 fork 自有新文件。
- [ ] 构建矩阵全绿：`with_xhttp,with_vless_enc` 全开与全关两种组合 `go build ./...` 通过。
- [ ] 上游既有检查在全关配置通过：`go vet ./...`、`go test ./...`、golangci-lint（`.golangci.yml` 既有配置）。
- [ ] 冒烟等价：全关构建 vs 上游同 tag 构建，ws / grpc / httpupgrade 三种传输 loopback 冒烟结果一致。
- [ ] CI（`.github/workflows/fork-ci.yml`）在 muts-main 上全绿。
- [ ] FORK.md 基座信息已更新；本文件 1.3 切口清单与实际 `git diff` 一致。

## 4. CI / 构建矩阵

`.github/workflows/fork-ci.yml`（push / PR 到 muts-main 时触发）：

| job | 内容 |
|---|---|
| `build-matrix` | tag 全关 / 全开 × `go build ./...` + `go build ./cmd/sing-box`，两种组合都必须通过 |
| `check-off` | 全关配置下 `go vet ./...` + `go test ./...`（上游既有检查的等价口径） |
| `lint` | golangci-lint，默认 tag 集 + 追加 fork tag 各跑一遍 |
| `diff-hygiene` | 对基座 tag 做 `git diff --stat`，断言上游既有文件的改动全部落在 `fork-patch` 标记内（grep 校验） |

本地等价命令见 3.3。
