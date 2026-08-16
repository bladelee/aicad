# Homebrew 排错与运维手册

> 记录 **2026-08-09 修复 2016 年老 Homebrew 安装（升级到 6.0.15）踩过的所有坑**，以及日后再次出现 brew 失效时的诊断、修复、运维方案。
> 适用环境：macOS 12.7.6 Monterey / Intel x86_64 / Homebrew 在 `/usr/local`。

## 目录

- [1. TL;DR — brew 坏了的 30 秒诊断法](#1-tldr--brew-坏了的-30-秒诊断法)
- [2. 本次修复实录（4 个叠加根因）](#2-本次修复实录4-个叠加根因)
- [3. 常见错误 & 速查表](#3-常见错误--速查表)
- [4. 关键路径与目录](#4-关键路径与目录)
- [5. brew 4.x API mode 必知](#5-brew-4x-api-mode-必知)
- [6. CLT 与 Xcode 的关系](#6-clt-与-xcode-的关系)
- [7. VS Code 集成终端的沙箱坑](#7-vs-code-集成终端的沙箱坑)
- [8. 备选 git 方案（无 CLT/Xcode 时）](#8-备选-git-方案无-cltxcode-时)
- [9. 重置与彻底重装](#9-重置与彻底重装)
- [10. 后续清理清单](#10-后续清理清单)

---

## 1. TL;DR — brew 坏了的 30 秒诊断法

按顺序跑下面 4 条，输出异常的就是病根所在：

```bash
brew --version                 # 1. 应输出 Homebrew 4.x/5.x/6.x。完全无输出 = 主程序挂了
/usr/bin/git --version         # 2. 应输出版本号。报 dyld / xcrun 错 = git/Xcode/CLT 损坏
xcode-select -p                # 3. 应指向 /Library/Developer/CommandLineTools 或 Xcode.app
brew doctor 2>&1 | head -20    # 4. 看具体报错对号入座第 3 节
```

**调用顺序口诀**：先修 `git`（最底层），再修 `CLT/Xcode`（中层数据取决于 git），最后 `brew update-reset`（最上层）。brew 内部 spawn 的就是系统 `/usr/bin/git`，git 不通则 brew 的 update/install/reset 全报 "No remote 'origin'" 的误判错误。

---

## 2. 本次修复实录（4 个叠加根因）

按发现顺序记录，每个坑都标注**症状**、**根因**、**修复**，便于下次直接对号入座。

### 坑 #1：陈旧 `homebrew-core` tap（2019）用了淘汰的 DSL

**症状**
```
Error: A legacy DSL was used: sha256 ({"8e1...abb" => :mojave})
/usr/local/Homebrew/Library/Homebrew/bottle_specification.rb:131:in 'block in BottleSpecification#sha256'
/usr/local/Homebrew/Library/Taps/homebrew/homebrew-core/Formula/python@2.rb:10:...
```
任何 `brew install` / `brew upgrade` 都崩。

**根因**：`/usr/local/Homebrew/Library/Taps/homebrew/homebrew-core` 这个 git 仓库停留在 2019 年的 `master` 分支。其中 `Formula/python@2.rb` 用了 `sha256(:mojave)` 这种老 hash DSL，新版 brew（≥4.x）不再容忍。同时还跟踪了已被 GitHub 删除的 `master` 分支（远程默认分支早已改名为 `main`），`brew update-reset / git fetch` 都会失败。

**修复**：Homebrew 4.0+ 默认走 **API mode**（直接从 `formulae.brew.sh` 拉 JSON），不再需要本地 taps 的 git checkout。直接把陈旧 taps 移走：
```bash
mv /usr/local/Homebrew/Library/Taps/homebrew/homebrew-core /tmp/homebrew-core.old.2019
mv /usr/local/Homebrew/Library/Taps/homebrew/homebrew-cask /tmp/homebrew-cask.old.2019
```
移走后 brew 自动切到纯 API mode，无需任何额外配置。

---

### 坑 #2：缺 `/usr/local/sbin` 目录

**症状**：`brew doctor` 报：
```
Warning: The following directories do not exist:
/usr/local/sbin
You should create these directories and change their ownership to your user.
```

**根因**：旧 Homebrew 安装脚本没建这目录，新版要求存在。

**修复**：
```bash
sudo mkdir -p /usr/local/sbin
sudo chown -R $(whoami) /usr/local/sbin
```

---

### 坑 #3：损坏的旧 Xcode 让"Xcode too outdated"

**症状**
```
Error: Your Xcode (7.3.1) at /Applications/Xcode.app is too outdated.
Please update to Xcode 14.2 (or delete it).
```

**根因**：`/Applications/Xcode.app` 是 **2016 年 4 月**的老 Xcode 7.3.1（看 `DVTFoundation.framework` 时间戳），跟 macOS 12 完全不匹配。brew 要求要么升到 14.2+，要么干脆删掉（删了之后 brew 改用 CLT）。

**先判断是否真用过 Xcode**（决定删不删）：
```bash
du -sh /Applications/Xcode.app                              # 占多少空间
du -sh ~/Library/Developer/CoreSimulator 2>/dev/null       # 有无 iOS 模拟器数据
du -sh ~/Library/Developer/Xcode/DerivedData 2>/dev/null   # 有无编译产物
mdfind "kMDItemFSName == '*.xcodeproj'"                     # 有无 iOS/macOS 项目
```
四个全空 = 从没用过 Xcode，删了无损失。

**修复**（确认不用后删）：
```bash
sudo rm -rf /Applications/Xcode.app    # 7G+，要等几分钟，无进度属正常
sudo xcode-select --reset              # 让系统下次找 CLT
```

---

### 坑 #4：缺 Command Line Tools（CLT）

**症状**：所有 `brew install` 报：
```
Error: No developer tools installed.
Install the Command Line Tools:
  xcode-select --install
```

**根因**：装包需要编译/链接器（clang/make/headers），来自 CLT 或完整 Xcode。两个都没有就装不了。

**修复**（重点：必须在 macOS 原生 Terminal.app，VS Code 集成终端会失败）：
```bash
xcode-select --install
```
弹 GUI 窗口 → 点"安装"→ 同意条款 → 5-10 分钟下载。

完成后验证：
```bash
xcode-select -p                              # 应输出 /Library/Developer/CommandLineTools
/usr/bin/git --version                       # 应输出版本号（CLT 自带 git）
ls /Library/Developer/CommandLineTools/usr/bin/git    # 应存在
```

---

## 3. 常见错误 & 速查表

| 错误信息 | 根因 | 修复 |
|---------|------|------|
| `Error: A legacy DSL was used: sha256(...=>:mojave)` | 陈旧 homebrew-core tap | 见坑 #1，移走老 taps |
| `Error: Your Xcode (X.Y) at ... is too outdated` | Xcode 太老 | 见坑 #3，删 Xcode |
| `Error: No developer tools installed` | 缺 CLT | 见坑 #4，`xcode-select --install` |
| `Warning: No remote 'origin' in /usr/local/Homebrew` | brew 内部 spawn 的 `/usr/bin/git` 崩溃（通常因 Xcode/CLT 损坏），不是真的没 remote | 先修 git，见第 8 节 |
| `dyld: Library not loaded: '/usr/lib/libauto.dylib'` | 系统 git 依赖的 Xcode framework 缺文件 | 删 Xcode + 装 CLT |
| `xcrun: error: invalid active developer path` | `xcode-select` 指向的目录不存在（如删了 Xcode 没切指向） | `sudo xcode-select --switch /Library/Developer/CommandLineTools` |
| `xcode-select: error: no developer tools were found at '...', and no install could be requested (perhaps no UI is present)` | 在 VS Code 终端跑 `xcode-select --install` 没法弹 GUI | 改到 Terminal.app 跑 |
| `Errno::EPERM ... ~/Library/Caches/Homebrew/bootsnap` | VS Code 沙箱拦截写 ~/Library/Caches | 见第 7 节 |
| `git: error: unable to locate xcodebuild` | 系统 git 找不 Xcode（已删或损坏） | 装 CLT，或用第 8 节的备选 git |
| `/usr/local/Cellar is not writable` | 目录所有权不对 | `sudo chown -R $(whoami) /usr/local/Cellar` |
| `Warning: You are using macOS 12. We (and Apple) do not provide support` | macOS 12 不在 brew Tier 1 | 无害警告，可忽略；功能正常 |

---

## 4. 关键路径与目录

### macOS Intel 上的 Homebrew（注意不是 `/opt/homebrew`）
| 路径 | 作用 |
|------|------|
| `/usr/local/bin/brew` | brew 主入口（symlink → `/usr/local/Homebrew/bin/brew`） |
| `/usr/local/Homebrew/` | brew 主仓库（git clone of Homebrew/brew） |
| `/usr/local/Homebrew/Library/Taps/homebrew/` | 本地 taps（4.x+ 默认 ABC 用 API mode，不需要） |
| `/usr/local/Cellar/` | 已安装的 keg（每个包一个目录） |
| `/usr/local/opt/<pkg>/` | keg 的稳定 symlink（不随版本号变） |
| `/usr/local/sbin/` | brew 装的系统级命令 |
| `/usr/local/var/homebrew/` | brew 运行时数据、locks |
| `~/Library/Caches/Homebrew/` | 下载缓存、bootsnap 缓存 |

### Xcode / CLT
| 路径 | 作用 |
|------|------|
| `/Applications/Xcode.app` | 完整 Xcode（10G+，iOS/macOS GUI 开发用） |
| `/Library/Developer/CommandLineTools/` | 独立 CLT（1-2G，自带 git/clang/make，不依赖 Xcode） |
| `/Library/Developer/CommandLineTools/usr/bin/git` | CLT 自带的 git |
| `/usr/bin/git` | 系统 git（实际是 shim，调用 xcode-select 指向的工具） |

### xcode-select 控制
- `xcode-select -p`：查当前指向
- `sudo xcode-select --switch /path`：切换指向
- `sudo xcode-select --reset`：恢复默认（优先 Xcode，无则 CLT）

---

## 5. brew 4.x API mode 必知

**核心变化**：Homebrew 4.0（2023）开始**默认走 API mode**，`brew install/info/search` 直接从 `https://formulae.brew.sh` 拉 JSON，**不再需要本地 homebrew-core git 仓库**。

### 这意味着什么
1. 老教程说的 `brew tap homebrew/core`、`brew update-reset` 在 API mode 下**不需要**
2. 陈旧的本地 taps（如本案例的 2019 年 homebrew-core）反而是**毒瘤**，会因淘汰 DSL 让 brew 崩溃
3. 想确认是否在 API mode：`brew info hello` 能输出最新版本号 = 在 API mode

### 怎么强制走 API mode（不要本地 taps）
默认就是 API mode。如果环境变量里有 `HOMEBREW_NO_INSTALL_FROM_API=1`，删掉它：
```bash
grep -rn HOMEBREW_NO_INSTALL_FROM_API ~/.zshrc ~/.bashrc ~/.zprofile ~/.profile 2>/dev/null
# 找到的那行删掉或注释掉
```

### 什么时候需要本地 tap
- 自己写 formula 测试时（`brew tap your/repo`）
- 公司内部 formula 仓库
- 极端网络受限环境（无法访问 formulae.brew.sh）

其它情况一律不需要。

---

## 6. CLT 与 Xcode 的关系

```
PATH/git (/usr/bin/git)
        ↓ shim
        ↓
xcode-select 当前指向
        ↓
   ┌────────────┴────────────┐
   ↓                         ↓
/Applications/Xcode.app    /Library/Developer/CommandLineTools
（完整 Xcode 10G+）          （独立 CLT 1-2G）
                            （自带 git/clang/make，brew 用这个就够）
```

### 经验法则
- **只用 brew / 命令行开发** → 只装 CLT 就够，不需要 Xcode
- **要 iOS / macOS GUI app 开发** → 装 Xcode
- **同一个 Mac 同时有损坏的旧 Xcode + 没 CLT** → brew 会报"Xcode too outdated"，删 Xcode 或升 Xcode
- **只要装了 Xcode，xcode-select 默认指向 Xcode**，删了 Xcode 后要手动 `sudo xcode-select --switch /Library/Developer/CommandLineTools`

### 装 CLT 的有效 / 无效方式
| 方式 | 有效？ |
|------|--------|
| 在 macOS Terminal.app 跑 `xcode-select --install` | ✅ |
| 在 macOS Terminal.app 跑 `softwareupdate --install "Command Line Tools for Xcode-X.Y"` | ✅ |
| 在 VS Code 集成终端跑 `xcode-select --install` | ❌（无 GUI 会话，装不了） |
| 从 developer.apple.com 手动下 `.dmg` 装 | ✅（兜底方案，需 Apple ID） |

---

## 7. VS Code 集成终端的沙箱坑

VS Code 的集成终端默认在沙箱里跑，**禁止写 `~/Library/Caches/` 和大部分 `~` 下的隐私目录**。

### 症状
brew 在 VS Code 终端跑报：
```
Errno::EPERM ... Operation not permitted @ rb_sysopen -
/Users/bladelee/Library/Caches/Homebrew/bootsnap/.../bootsnap/load-path-cache
```

### 这不是 brew 坏了
brew 本身完全正常，是 VS Code 沙箱拦截写入 caches。在 macOS 原生 Terminal.app 跑同一命令不会有问题。

### 解决方案（按推荐度排序）
1. **在 macOS Terminal.app 跑 brew**（最干净，永远不会有这类问题）
2. VS Code 配置里关终端沙箱（`settings.json`）：
   ```json
   { "terminal.integrated.sandbox": false }
   ```
3. 临时绕开：用环境变量重定向 cache（部分有效，bootsnap 仍写 ~/Library/Caches）：
   ```bash
   mkdir -p ~/.homebrew-cache
   HOMEBREW_CACHE=~/.homebrew-cache brew install <pkg>
   ```

### 判断当前终端是否被沙箱拦
```bash
echo "HOME=$HOME"
touch ~/Library/Caches/test-write 2>&1 && echo "可写" || echo "被沙箱拦"
```

---

## 8. 备选 git 方案（无 CLT/Xcode 时）

如果暂时没法装 CLT（例如系统很老、GUI 弹窗一直不出现），可用下面任一独立 git 让 brew 至少能跑 update/info（但 install 仍需 CLT 来编译）。

### 方案 A：conda 自带的 git
```bash
conda install -n base git                       # 默认装到 /Users/<user>/miniconda3/bin/git
DYLD_FALLBACK_LIBRARY_PATH=$(conda info --base)/lib $(conda info --base)/bin/git --version
```
⚠️ conda git 在某些 cwd 下找不到自己的 `libpcre2-8.0.dylib`，必须带 `DYLD_FALLBACK_LIBRARY_PATH`。可写 wrapper：
```bash
mkdir -p ~/.local/bin
cat > ~/.local/bin/git <<'EOF'
#!/bin/bash
export DYLD_FALLBACK_LIBRARY_PATH=/Users/<user>/miniconda3/lib
exec /Users/<user>/miniconda3/bin/git "$@"
EOF
chmod +x ~/.local/bin/git
```
然后把 `~/.local/bin` 加到 PATH 前面。注意：VS Code 沙箱间歇会拦 wrapper（报 `Operation not permitted`）。

### 方案 B：GitHub Desktop / Sourcetree / GitKraken 等自带 git
查路径：
```bash
ls "/Applications/GitHub Desktop.app/Contents/Resources/app/static/git/bin/git" 2>/dev/null
ls /Applications/Sourcetree.app/Contents/Resources/git_staging/bin/git 2>/dev/null
```
有的话直接用绝对路径。

### 方案 C：让 brew 用指定 git
```bash
HOMEBREW_GIT_PATH=/path/to/git brew update-reset
```
（注：实测这个变量名在 brew 6.x 中可能不被识别，更可靠是 PATH 注入。）

### 注意
所有这些**只是临时让 git 命令可用的方案**，并不能让 brew install 工作。brew install 必须有 clang/make/headers（来自 CLT 或 Xcode）。所以**最终解决方案还是装 CLT**。

---

## 9. 重置与彻底重装

### 软重置（推荐先试）
```bash
# 1. 重置陈旧 taps（brew 4.x+ API mode 下一般不需要）
brew update-reset

# 2. 健康检查
brew doctor

# 3. 清缓存重试
brew cleanup -s
rm -rf ~/Library/Caches/Homebrew/downloads/*
```

### 彻底卸载 / 重装 Homebrew（核选项）
⚠️ 会删掉所有通过 brew 装的包（`/usr/local/Cellar` 内容全没）。

**官方卸载脚本**：
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/uninstall.sh)"
```

**官方重装**：
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

重装后会回到默认状态，自己装的包都要重装。

---

## 10. 后续清理清单

修复完成后可以做的清理（**非必须**，但能省空间和减少混乱）：

```bash
# 删陈旧的备份 taps（已经移到 /tmp 的）
rm -rf /tmp/homebrew-core.old.2019 /tmp/homebrew-cask.old.2019

# 清理老的废弃 keg（python@2、android-sdk 等 2016-2018 装的）
brew autoremove                       # 自动删无依赖的孤儿包
brew cleanup -s                       # 清老的下载和缓存

# 如果有自己建的 git wrapper 不再需要
rm -f ~/.local/bin/git
rmdir ~/.local/bin 2>/dev/null || true

# 如果之前为绕开沙箱建了 redirect cache
rm -rf ~/.homebrew-cache
```

### 本次修复后保留的状态（参考）
- `/usr/local/Homebrew/` — brew 主仓，已是 6.0.15
- `/usr/local/Cellar/` — 含 hello + 老的 android-sdk/ansible/gdbm/libyaml/openssl/python@2/readline/sqlite 等
- `/Library/Developer/CommandLineTools/` — CLT，已装
- `/Applications/Xcode.app` — **已删**（释放 7.4G）
- `/usr/local/sbin` — 已建并 chown

---

## 附：本次修复时间线（参考）

| 时间 | 动作 | 结果 |
|------|------|------|
| 00:35 | 建 `/usr/local/sbin` + 删旧 CLT 空壳 | brew update 仍报 git 错 |
| 00:45 | 移走陈旧 homebrew-core / homebrew-cask tap | brew info 切 API mode 可用 |
| 00:50 | 删除损坏的 Xcode 7.3.1（7.4G） | "Xcode too outdated" 消失，但缺 CLT |
| 01:00 | 用 conda 装 git 作备选 | 验证 origin remote 都存在，确认根因在系统 git |
| 01:28 | 用户在 Terminal.app 装 CLT（`xcode-select --install`） | git 恢复，brew install hello 成功 |
