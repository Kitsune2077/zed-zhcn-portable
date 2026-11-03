# Zed 汉化便携版 for Windows

[![Build](https://github.com/Kitsune2077/zed-zhcn-portable/actions/workflows/build.yml/badge.svg)](https://github.com/Kitsune2077/zed-zhcn-portable/actions/workflows/build.yml)

用 GitHub Actions 自动编译的 **Windows 便携版 Zed 编辑器**:开箱即简体中文、所有数据都保存在程序目录的 `data` 文件夹内、跟随官方版本自动升级。每次发布同时提供**单文件 exe** 和 **ZIP 包**两种形态。

> 社区非官方构建,与 Zed Industries 无关。基于 GPL-3.0 协议的开源 Zed 源码与 [zed-ZH_CN](https://github.com/ReachForStar/zed-ZH_CN) 汉化项目。

## 下载

到 [Releases](../../releases) 页面下载最新版本:

| 文件 | 说明 |
| --- | --- |
| `Zed-zhCN-<版本>-portable-x64.exe` | 单文件版,下载后直接双击运行 |
| `Zed-zhCN-<版本>-portable-x64.zip` | ZIP 版,解压后双击 `zed.exe`,自带预置中文配置 |
| `*.sha256` | 校验和 |

## 使用

- **开箱中文**:界面默认简体中文(`ui_language: zh-CN`)。
- **真正的便携**:首次启动自动在 `zed.exe` 所在目录创建 `data` 文件夹,配置、扩展、数据库、日志全部保存在内。删除 `data` 即完全重置,拷贝整个文件夹即可迁移到其他电脑。
- **升级**:下载新版本覆盖 `zed.exe` 即可,`data` 文件夹不受影响。
- **只读目录回退**:若把 `zed.exe` 放进不可写的目录(如 `Program Files`),会自动回退到系统默认数据目录(`%LOCALAPPDATA%\Zed`)。
- **SmartScreen**:exe 未签名,首次运行如遇蓝色提示,点"更多信息"→"仍要运行"。

## 工作原理

本仓库是"壳仓库",**不含任何 Zed 源码**,只有三样东西:一个工作流、一个便携化补丁、一份预置配置。版本跟随链:

```
zed-industries/zed(官方)          官方源码,发 stable/preview 版
      │  手动 merge(汉化项目维护者负责,通常几天内跟进)
      ▼
ReachForStar/zed-ZH_CN(汉化)     完整源码 fork,新增 zed_i18n crate,
      │  发布 release(如 v1.27.0)
      ▼  本仓库定时检测新 release tag → checkout 对应源码
zed-zhcn-portable(本仓库)         打便携补丁 → cargo build → 出包
```

### 便携化补丁(`scripts/apply_portable_patch.py`)

Zed 官方源码目前**不支持**用环境变量重定向数据目录(社区的[便携模式提案](https://github.com/zed-industries/zed/discussions/21103)尚未落地),只提供编程接口 `paths::set_custom_data_dir()`。因此本仓库用一个**基于锚点的纯插入式补丁**(不是 unified diff,不怕上游无关改动)往 `crates/zed/src/main.rs` 的 `init_paths()` 前插入约 30 行:

- `zed.exe` 所在目录可写 → 自动创建 `data\` 并把全部用户数据重定向进去,同时在 `data\config\settings.json` 预写中文、禁用自动更新的配置;
- 目录不可写 → 什么都不做,Zed 回退到平台默认目录;
- 用户显式传了 `--user-data-dir` 参数 → 补丁不干预。

补丁幂等,并在上游代码漂移(锚点/API 消失)时让 CI **明确失败**而不是悄悄产出非便携构建。已针对 zed-ZH_CN v1.27.0 实测通过。

### 编译配置

来自两个已验证项目的组合:

- 长路径 + 开发者模式 + 符号链接(zed 仓库有约 240 个符号链接)、`CARGO_HOME=C:\c` 短路径——来自 zed-ZH_CN 官方 CI;
- `RUSTFLAGS=-C target-feature=+crt-static` 静态链接 CRT(单文件 exe 不依赖 VC 运行库)、关 LTO 换编译速度、sccache 编译缓存——来自 [zed-windows-stable](https://github.com/sonercirit/zed-windows-stable);
- Rust 工具链按源码树里的 `rust-toolchain.toml` 安装,发布渠道写 `stable`。

## 跟随官方升级

工作流每天 UTC 1:30 / 13:30(北京时间 9:30 / 21:30)自动检查 zed-ZH_CN 是否发布新 release:

- 有新 tag → checkout 新源码 → 打补丁 → 编译 → 发布到本仓库 Releases → 把版本号写回 `latest_build.txt`;
- 没有新版本 → 直接跳过,几乎不消耗 Actions 时长。

汉化与官方版本的同步由 zed-ZH_CN 维护者负责(历史记录非常及时),因此你无需关心翻译维护。

### 手动触发

在 Actions 页面 `Build Windows portable (zh-CN)` 工作流上点 **Run workflow**:

- **force_build**:上游没发新版也强制重新构建(比如改了补丁或工作流之后);
- **source_ref**:指定 zed-ZH_CN 的任意 tag/分支/commit 构建(用于测试),这种构建不会回写 `latest_build.txt`。

## 维护指南

日常零维护。唯一可能需要动手的场景:

**补丁失败**:上游重构了 `main.rs` 导致锚点(或 `set_custom_data_dir` API)消失,CI 会在 "Apply portable-data-dir patch" 一步明确报错。处理方式:参考报错信息,更新 `scripts/apply_portable_patch.py` 里的 `ANCHORS` / `RUST_BLOCK`,本地用真实源码验证后提交,再手动 force_build。

**想换上游**(比如 zed-ZH_CN 停止维护):改 `.github/workflows/build.yml` 顶部的 `ZED_REPO` 环境变量即可指向任何 zed fork(官方仓库 `zed-industries/zed` 也行,但会失去汉化)。

## 本地构建

不必本地构建,CI 全自动。若想自己编译:

```powershell
git clone https://github.com/ReachForStar/zed-ZH_CN zed
python scripts\apply_portable_patch.py zed
Set-Content zed\crates\zed\RELEASE_CHANNEL 'stable' -NoNewline
cd zed
rustup show          # 按 rust-toolchain.toml 安装工具链
$env:RUSTFLAGS = '-C opt-level=3 -C codegen-units=16 -C target-feature=+crt-static'
cargo build --release -p zed
# 产物:target\release\zed.exe
```

要求:Windows 10+、VS 2022 C++ 构建工具、启用开发者模式和长路径、Rust(经 rustup)。全量编译约 1~3 小时(取决于 CPU),磁盘需要 30GB+。

## 已知限制

- **自动更新已禁用**(补丁和预置配置双重保证):Zed 官方自动更新会下载英文官方安装包,破坏便携性和汉化。升级请来本仓库 Releases。
- exe 未签名,SmartScreen 会提示;介意者可自行对 exe 签名。
- 官方 Windows 安装包额外带的 `conpty.dll`/`OpenConsole.exe` 等伴生文件未包含(参考项目 zed-windows-stable 长期单文件分发未报告集成终端问题);若你遇到终端异常,请提 issue,可在 ZIP 版中补上这些 DLL。
- 遥测与崩溃诊断已在预置配置中关闭。

## 致谢

- [Zed Industries](https://github.com/zed-industries/zed) —— Zed 编辑器本体(GPL-3.0)
- [ReachForStar/zed-ZH_CN](https://github.com/ReachForStar/zed-ZH_CN) —— 简体中文汉化
- [sonercirit/zed-windows-stable](https://github.com/sonercirit/zed-windows-stable) —— Windows 单文件构建的编译配置参考

## 许可

- 本仓库的构建脚本与补丁:[GPL-3.0](LICENSE)
- 构建产物:Zed 源码为 GPL-3.0(部分组件 Apache-2.0),按原协议分发
- "Zed" 名称与商标归 Zed Industries 所有,本构建为非官方社区版本
