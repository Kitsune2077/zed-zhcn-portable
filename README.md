# Zed 汉化便携版 for Windows

[![Build official upstream](https://github.com/Kitsune2077/zed-zhcn-portable/actions/workflows/build-official.yml/badge.svg)](https://github.com/Kitsune2077/zed-zhcn-portable/actions/workflows/build-official.yml)

用 GitHub Actions 自动编译的 **Windows 便携版 Zed 编辑器**：开箱即简体中文、所有数据都保存在程序目录的 `data` 文件夹内、跟随官方版本自动升级。每次发布同时提供**单文件 exe** 和 **ZIP 包**两种形态。

> 社区非官方构建，与 Zed Industries 无关。基于 GPL-3.0 协议的 Zed 官方源码与 [zed-i18n](https://github.com/LI-NA/zed-i18n) 汉化项目。

## 下载

到 [Releases](../../releases) 页面下载最新版本：

| 文件 | 说明 |
| --- | --- |
| `Zed-zhCN-<版本>-portable-x64.exe` | 单文件版，下载后直接双击运行 |
| `Zed-zhCN-<版本>-portable-x64.zip` | ZIP 版，解压后双击 `zed.exe`，自带预置中文配置 |
| `*.sha256` | 校验和 |

> tag 不带后缀的 release（如 `v1.27.0`）来自官方源码管线（默认）；带 `-zhcn` 后缀（如 `v1.27.0-zhcn`）来自 zed-ZH_CN fork 兜底管线（手动）。

## 使用

- **开箱中文**：界面默认简体中文（翻译直接编译进程序，无需语言设置）。
- **真正的便携**：首次启动自动在 `zed.exe` 所在目录创建 `data` 文件夹，配置、扩展、数据库、日志全部保存在内。删除 `data` 即完全重置，拷贝整个文件夹即可迁移到其他电脑。
- **升级**：下载新版本覆盖 `zed.exe` 即可，`data` 文件夹不受影响。
- **只读目录回退**：若把 `zed.exe` 放进不可写的目录（如 `Program Files`），会自动回退到系统默认数据目录（`%LOCALAPPDATA%\Zed`）。
- **SmartScreen**：exe 未签名，首次运行如遇蓝色提示，点"更多信息"→"仍要运行"。

## 工作原理

本仓库是"壳仓库"，**不含任何 Zed 源码**，只有四样东西：两个工作流、一个便携化补丁、两份预置配置。默认发版跟随链：

```
zed-industries/zed(官方)             源码 tag,如 v1.27.0
      │  发布 stable(每 3~7 天)
      ▼
LI-NA/zed-i18n(汉化工具集,非 fork)   发布 vX.Y.Z-i18n.N,表示"官方 vX.Y.Z 的
      │  简体中文翻译已就绪"(0~1 天跟进,AI 翻译)
      ▼
zed-zhcn-portable(本仓库)            checkout 官方源码 → zed-i18n apply zh-CN
                                     (翻译写入源码)→ 便携补丁 → cargo build → 出包
```

### 汉化机制（zed-i18n apply）

[zed-i18n](https://github.com/LI-NA/zed-i18n) 不是 Zed 的 fork，而是独立的汉化工具集：它把简体中文翻译**逐行写入官方 Rust 源码**（`manifest/ui-strings.json` 记录每个字符串在源码中的精确文件与行号）。`apply` 时任何位置对不上都会**硬失败**，绝不会悄悄产出半汉化构建；这也意味着必须使用与翻译清单匹配的官方版本——所以工作流的触发器是 zed-i18n 的 release（它本身就代表"官方版本 + 翻译已就绪"），每天检查两次，官方发版后通常 1 天内跟进，远快于依赖人工 merge 的源码 fork。

注意：翻译由 zed-i18n 项目用 AI 生成并持续迭代，可能存在少量误译，发现问题请到该项目提 issue。

### 便携化补丁（`scripts/apply_portable_patch.py`）

Zed 官方源码目前**不支持**用环境变量重定向数据目录（社区的[便携模式提案](https://github.com/zed-industries/zed/discussions/21103)尚未落地），只提供编程接口 `paths::set_custom_data_dir()`。因此本仓库用一个**基于锚点的纯插入式补丁**（不是 unified diff，不怕上游无关改动）往 `crates/zed/src/main.rs` 的 `init_paths()` 前插入约 30 行：

- `zed.exe` 所在目录可写 → 自动创建 `data\` 并把全部用户数据重定向进去，同时在 `data\config\settings.json` 预写禁用自动更新、关闭遥测的配置（官方源码构建用 `seed/settings-official.json`，zed-ZH_CN fork 构建额外带 `ui_language: zh-CN`）；
- 目录不可写 → 什么都不做，Zed 回退到平台默认目录；
- 用户显式传了 `--user-data-dir` 参数 → 补丁不干预。

补丁对官方源码和 zed-ZH_CN fork 源码通用，幂等，并在上游代码漂移（锚点/API 消失）时让 CI **明确失败**而不是悄悄产出非便携构建。已对官方 v1.27.0 与 zed-ZH_CN v1.27.0 实测通过。

### 编译配置

- 长路径 + 开发者模式 + 符号链接（zed 仓库有约 240 个符号链接）、`CARGO_HOME=C:\c` 短路径——来自 Zed 官方 CI；
- `RUSTFLAGS=-C target-feature=+crt-static` 静态链接 CRT（单文件 exe 不依赖 VC 运行库）——来自 [zed-windows-stable](https://github.com/sonercirit/zed-windows-stable) 的已验证配置；
- 优化级别与 LTO 沿用官方发布同款配置：`cargo --config .cargo/bundle-config.toml`（thin LTO + `codegen-units=1` 等）。相比关闭 LTO 的快速编译配置，exe 体积小 10~25%，编译时间约多半个小时；
- ZIP 用 7-Zip `-mx=9` 制作（压缩率优于 PowerShell 自带的 Compress-Archive，产物仍是标准 .zip）；
- Rust 工具链按源码树里的 `rust-toolchain.toml` 安装，发布渠道写 `stable`，sccache 编译缓存。

## 跟随官方升级

默认工作流 `Build Windows portable (zh-CN) · official upstream`（`build-official.yml`）每天 UTC 1:30 / 13:30（北京时间 9:30 / 21:30）自动检查 zed-i18n 是否发布新 release：

- 有新版本（且官方仓库已有对应 release）→ checkout 官方源码（按 zed-i18n 锁定的 commit）→ 应用翻译 → 打补丁 → 编译 → 发布到本仓库 Releases（干净 tag 如 `v1.27.0`）→ 回写 `latest_build.txt`；
- 版本没有变化 → 直接跳过，几乎不消耗 Actions 时长；
- 版本比较是语义化的（`[version]` 比较），zed-i18n 落后于本仓库已发布版本时会正确跳过，不会"降级"覆盖。

### 兜底工作流

`Build Windows portable (zh-CN) · ZH_CN fallback`（`build.yml`）跟随 [ReachForStar/zed-ZH_CN](https://github.com/ReachForStar/zed-ZH_CN)（zed 源码 fork，rust-i18n 运行时方案，支持 `ui_language` 设置切换语言）构建，**仅手动触发**，发布的 tag 带 `-zhcn` 后缀（如 `v1.27.0-zhcn`）。适用场景：zed-i18n 停止维护、需要 fork 源的运行时语言切换。

### 手动触发

在 Actions 页面选择工作流后点 **Run workflow**：

- **official upstream 工作流**：
  - **force_build**：官方版本没变也强制重新构建（比如改了补丁或工作流之后）；
  - **i18n_tag**：指定 zed-i18n 的 ref（如 `v1.27.0-i18n.1`）测试，这种构建不回写 `latest_build.txt`。
- **ZH_CN fallback 工作流**：
  - **source_ref**：指定 zed-ZH_CN 的 tag/分支/commit；留空用其最新 release。该工作流不做版本比较，触发即构建。

## 迁移说明（v1.27.0）

现有 `v1.27.0` release 由旧管线（zed-ZH_CN fork）产出。新管线首次自动发布将发生在官方 v1.28.0 stable + zed-i18n `v1.28.0-i18n.N` 就绪后（版本比较会跳过 ≤1.27.0，不会降级覆盖）。若想提前用新管线重建 v1.27.0：删除旧 release 与 tag 后，手动触发 official 工作流并指定 `i18n_tag: v1.27.0-i18n.1`。

## 维护指南

日常零维护。唯一可能需要动手的场景：

**官方工作流 apply 失败**：说明 zed-i18n 的翻译清单与 checkout 的官方源码不匹配（通常是 zed-i18n 自身 tag 间不同步）。处理：查看 "Apply zh-CN translations" 步骤日志，等其修复或换一个 `i18n_tag` 重试。

**zed-i18n 停止维护**：两个选择——(a) 手动跑 ZH_CN fallback 工作流出包（如果 zed-ZH_CN 还在维护）；(b) 接管翻译：clone zed-i18n，按其文档跑 extract/翻译流程更新 `manifest` 与 `translations/zh-CN.json`，推到自己的 fork，然后把 `build-official.yml` 里的 `I18N_REPO` 指向它。

**便携补丁失败**：上游重构了 `main.rs` 导致锚点（或 `set_custom_data_dir` API）消失，CI 会在 "Apply portable-data-dir patch" 一步明确报错。处理方式：参考报错信息，更新 `scripts/apply_portable_patch.py` 里的 `ANCHORS` / `RUST_BLOCK`，本地用真实源码验证后提交，再手动 force_build。

## 本地构建

不必本地构建，CI 全自动。若想自己编译（以官方源码管线为例）：

```powershell
git clone https://github.com/LI-NA/zed-i18n zed-i18n
git -C zed-i18n checkout v1.27.0-i18n.1           # 或最新 vX.Y.Z-i18n.N
# 检出官方源码到 zed-i18n 期望的位置(版本与 commit 以其 config/project.toml 为准)
git clone --branch v1.27.0 https://github.com/zed-industries/zed zed-i18n/.cache/zed/v1.27.0
cd zed-i18n
uv run zed-i18n apply --language zh-CN            # 需要 uv;首次运行自动装依赖
cd .cache/zed/v1.27.0
python ..\..\..\scripts\apply_portable_patch.py . --seed-settings ..\..\..\seed\settings-official.json
Set-Content crates\zed\RELEASE_CHANNEL 'stable' -NoNewline
$env:RUSTFLAGS = '-C target-feature=+crt-static'
cargo --config .cargo/bundle-config.toml build --release -p zed
# 产物:target\release\zed.exe
```

要求：Windows 10+、VS 2022 C++ 构建工具、启用开发者模式和长路径、Rust（经 rustup）、[uv](https://docs.astral.sh/uv/)、Python 3.12+。全量编译约 1~3 小时（取决于 CPU），磁盘需要 30GB+。

## 已知限制

- **自动更新已禁用**（补丁和预置配置双重保证）：Zed 官方自动更新会下载英文官方安装包，破坏便携性和汉化。升级请来本仓库 Releases。
- **不支持运行时切换界面语言**：官方管线把中文翻译编译进了程序；如需 `ui_language` 切换，用 ZH_CN fallback 工作流的构建。
- **翻译为 AI 生成**（zed-i18n 项目），可能存在误译；zed-ZH_CN fork 构建为社区维护的翻译。
- exe 未签名，SmartScreen 会提示；介意者可自行对 exe 签名。
- 官方 Windows 安装包额外带的 `conpty.dll`/`OpenConsole.exe` 等伴生文件未包含（参考项目 zed-windows-stable 长期单文件分发未报告集成终端问题）；若你遇到终端异常，请提 issue，可在 ZIP 版中补上这些 DLL。
- 遥测与崩溃诊断已在预置配置中关闭。

## 致谢

- [Zed Industries](https://github.com/zed-industries/zed) —— Zed 编辑器本体（GPL-3.0）
- [LI-NA/zed-i18n](https://github.com/LI-NA/zed-i18n) —— 官方源码汉化工具集与简体中文翻译（默认管线）
- [ReachForStar/zed-ZH_CN](https://github.com/ReachForStar/zed-ZH_CN) —— 简体中文汉化（fallback 管线）
- [sonercirit/zed-windows-stable](https://github.com/sonercirit/zed-windows-stable) —— Windows 单文件构建的编译配置参考

## 许可

- 本仓库的构建脚本与补丁：[GPL-3.0](LICENSE)
- 构建产物：Zed 源码为 GPL-3.0（部分组件 Apache-2.0），翻译内容源自 zed-i18n（GPL-3.0），按原协议分发
- "Zed" 名称与商标归 Zed Industries 所有，本构建为非官方社区版本
