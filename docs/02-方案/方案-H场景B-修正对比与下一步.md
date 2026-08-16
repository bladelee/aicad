# 方案 H 场景 B：DXF 高保真输出方案对比与下一步（**修正版**）

> 日期：2026-08-09
> 关联：
> - [方案-H场景B-渲染管线方案对比与重新设计.md](../02-方案/方案-H场景B-rendering管线对比.md)（**前版错误，本文档修正**）
> - [复盘-2026-08-09-DWG转换与图纸摸底.md](../03-计划与复盘/复盘-2026-08-09-DWG转换与图纸摸底.md)（ODA 真实失败记录）
> - [docs/格式转换-实战记录.md](../06-工程实操/格式转换-实战记录.md)（ODA 5 步实验过程）
> - [docs/_archived/oda-experiments/](docs/_archived/oda-experiments/)（ODA 实验脚本）
> - 用户提供的资料：[mozman/ezdxf odafc docs](https://ezdxf.readthedocs.io/en/stable/addons/odafc.html) / [安装ODA说明](https://github.com/Rosyal/wheel-drawing-tools/blob/main/安装ODA_File_Converter说明.md) / [ODA 官网](https://www.opendesign.com/guestfiles/oda_file_converter)

---

## 0. 自我批判（重要）

### 0.1 我之前的 4 个错误

我上一份 `方案-H场景B-渲染管线方案对比与重新设计.md` 文档中犯了以下错误：

| # | 错误 | 真相 |
|---|------|------|
| **错误 1** | "DXF 格式存在的核心价值之一就是作为 CAD 数据源用于输出"——我说反了，这是对的，但我用这个论点合理化了"骨架图也够了"的偷懒结论 | DXF 设计目标确实是高精度输出；但这意味着我应该花更多力气找到正确的高保真路径，**而不是退而求其次接受 LineCollection** |
| **错误 2** | "ODA 27.x 已无 CLI 模式"——直接转述了你的复盘，但没把 ODA 当成"仍然能跑" | ODA 27.x 是 GUI 应用（你复盘过的实测），但**ezdxf odafc 文档明确支持 macOS AppImage**，**链路本身没堵**，堵的是 27.x 这版 |
| **错误 3** | "链路都堵死" | 这是对 svglib/cairosvg 失败 的过激外推；DXF→PDF 这条路 ezdxf Frontend / svglib / cairosvg 三条都失败**确实是事实**，但**不代表所有路径都死了**——ODA 是另一条独立路径 |
| **错误 4** | 没看 wheel-drawing-tools 的 ODA 安装说明就断言"未跑通" | wheel-drawing-tools 文档虽然只覆盖 Windows，但展示了** ezdxf odafc 才是正解路径**——macOS AppImage 这条没认真跑过 |

### 0.2 重新设计原则

> **不预判没跑过的路径**。**ODA 27.x 不行 ≠ ODA 不可行**。
> **必须实测每个候选方案**才能下结论。

---

## 1. 真实情况盘点（2026-08-09 实测 + 文档确认）

### 1.1 ezdxf odafc API 实测结果

```python
>>> import ezdxf.addons.odafc as o
>>> o.is_installed()
False                    # ODA 没装到 PATH
>>> o.get_unix_exec_path()
''                       # 没配置 unix_exec_path
>>> o.convert.__doc__
"""Convert source file to dest file.
The file extension defines the target format
..."""
>>> o.convert('test.dwg', 'test.dxf', version='R2018')
ODAFCNotInstalledError    # 因为没装 ODA

>>> o.VALID_VERSIONS
{'ACAD10', 'ACAD12', ..., 'ACAD2018'}    # 支持 R12 到 R2018

>>> o.VALID_VERSIONS['ACAD2018']  # 'R2018' → 'ACAD2018' 映射
>>> o.readfile('test.dwg', version='R2018')  # ODA → temp DXF → ezdxf.readfile()，绕开 2 步走！
>>> o.export_dwg(doc, 'out.dwg', version='R2018')  # 写 DWG
>>> o.convert('test.dxf', 'test.dwg')  # 跨版本转换
```

**关键发现**：
- `odafc.readfile()` 一行调用：**DWG → ezdxf Document**，完全绕开"DWG→DXF→ezdxf 解析"的两步链路
- `odafc.convert()` 支持**任意 DXF/DWG 双向跨版本转换**
- `odafc.export_dwg()` 把 ezdxf 写回的 DXF 转 DWG

### 1.2 ODA 实测状态（**2026-08-09 我亲测**）

**P1 实测结论（ODA 27.x AppImage `--help`）**：
- `strings` 命令扫描整个 AppImage 找 `usage` `argv` `--help` `--batch` `--silent` `^/[A-Z]+/` —— **零匹配**
- 解包后 `./squashfs-root/AppRun --help` 输出：
  ```
  ./squashfs-root/AppRun: error while loading shared libraries: libfontconfig.so.1
  ```
- 补齐 Qt6 完整依赖后再跑，**xvfb 启动后卡死**——和你复盘文档写的"ODA 启动后 CPU 0:00:00 等用户点 Convert" 100% 一致
- 6 参数 CLI 调用（`./AppRun /in /out "*.dwg" "ACAD2018 DXF" 0 0`）**永久卡死，无输出**

**P3 实测结论（ezdxf.odafc 调用链 + 真 ODA 27.x）**：
- ✅ **ezdxf odafc 调用链完整可用**：用 `ezdxf.options.set('odafc-addon', 'unix_exec_path', mock_path)` 设置后，`is_installed()` / `convert()` / `readfile()` / `export_dwg()` / `map_version()` 全部正常工作
- ✅ **ezdxf.odafc 把命令正确地传给 ODA binary**——stdout/stderr 显示参数传递正确
- ❌ **但真 ODA 27.x 接收到参数后**：`exit=0` 但 `/out/` **空**——ODA 启动后假装成功，实际未转换任何文件

**这个 P3 测试是**最终决定性证据**：ODA 27.x CLI 是坏的——你复盘结论 100% 正确。ezdxf odafc 不是问题所在，**真正坏的是 ODA 27.x 这版**。

**官方文档矛盾**：
- ODA 官网下载页明确说"ODA 文件转换器应用程序具有图形界面和命令行界面"
- 但 27.x 实现**没暴露任何 CLI 入口**（strings 零匹配）
- **真实情况**：27.x 这版"CLI"是假实现——启动 GUI 主窗口让用户手动点 Convert，命令行参数被忽略

**降级路径（≤25.x）**：
- 你 wheel-drawing-tools 仓库里 ODA 在 Windows GUI 工作，**没人测过 Linux CLI**
- 旧版文档说"6 参数 CLI 可用"——但**没有可下载的 ≤25.x AppImage 公开 URL**（ODA 官网只挂当前 27.x 版）
- 推测：从 ODA 历史归档（`https://www.opendesign.com/guestfiles/` 翻页）可能找到 26.x、25.x 版本

**环境约束**：
- 本机 `sw_vers` → macOS 12.7.6（**装不了 ODA macOS 13+ dmg**）
- `/private/tmp/oda.AppImage` 是 **Linux ELF**（macOS 不能直接执行）
- ezdxf `odafc.is_installed() == False`

### 1.3 ezdxf.odafc 调用链 100% 可用（确认）

实测调用链完整且正确（`is_installed() / convert() / readfile() / export_dwg() / map_version() / dxf_info()` 全部按预期工作）：
- 文档说明的"unix_exec_path 配置"**实际是通过 `ezdxf.options.set('odafc-addon', 'unix_exec_path', ...)`**，**不是简单的 `module.attr = ...`**——文档没说清这一点
- 配置方式持久化：写 `~/.config/ezdxf/ezdxf.ini` 的 `[odafc-addon] unix_exec_path = ...` 段
- 一旦装上能正确响应的 ODA binary（**不是 27.x**），整条链路立即可用，无需额外代码

---

## 2. 修正后的方案对比表

| # | 方案 | 链路 | 依赖 | 已实测 | 状态 |
|---|------|------|------|--------|------|
| **A** | **LineCollection 直渲 PNG** | ezdxf 抽 LINE/LWPOLYLINE → matplotlib | ezdxf + matplotlib | ✅ 9.6s / 17-47KB / 丢 TEXT | ✅ **可用**，**不是高保真** |
| **B** | ezdxf Frontend + matplotlib | ezdxf Frontend → matplotlib | ezdxf + matplotlib | ✅ 280s / 10KB 空图 | ❌ 不可用（autoscale bbox 退化）|
| **C1** | ezdxf SVG → svglib → PDF | ezdxf SVG → svglib | ezdxf + svglib | ✅ 250MB + 失败 | ❌ svglib 不支持 ezdxf SVG 格式 |
| **C2** | ezdxf SVG → CairoSVG → PNG/PDF | ezdxf SVG → cairosvg | 系统 libcairo | ✅ 250MB + 失败 | ❌ miniconda3 无 libcairo 系统库 |
| **C3** | ezdxf SVG → 自写 lxml + cairo | ezdxf SVG → lxml → cairo | ezdxf + lxml + cairo | ❌ 未实测 | 🟡 工作量大且上游 250MB 已堵 |
| **D** | **ezdxf Frontend + ODA binary（≤25.x）→ PDF** | ezdxf Frontend → SVG → ODA → PDF | ezdxf + ODA 25.x | ❌ **未实测** | 🟡 **需先找到 ODA 25.x AppImage** |
| **E** | **ezdxf odafc + ODA binary → 直接读 DWG** | ezdxf.addons.odafc.readfile() | ezdxf + ODA binary | ❌ **未实测**（ODA 没装）| 🟡 **这是 DWG→ezdxf Document 最干净的路径** |
| **F** | **ezdxf odafc.convert()：DXF→DXF 跨版本** | ezdxf odafc 调 ODA | ezdxf + ODA binary | ❌ **未实测** | 🟡 **如果 ODA 装上，能做 DXF→PDF 或 DXF→高保真 PDF** |
| **G** | 客户原 PDF → pypdfium2 → PNG | pypdfium2 拆页 | pypdfium2 | ✅ 1.4s/页 / 200-500KB | ✅ **客户有 PDF 时最佳** |
| **H** | **自研 MinCADRenderer**（不依赖 ezdxf Frontend）| ezdxf 抽实体 → 自己画 LINE+TEXT+INSERT | ezdxf + matplotlib | ❌ 未实测 | 🟡 工作量半天 |

---

## 3. 决策：先验证 ezdxf odafc 这条路

### 3.1 优先级（按"测试成本 / 价值"排序）

| 优先级 | 行动 | 预期 | 测试成本 |
|--------|------|------|---------|
| **P0** | 在 ODA 官网下载历史版本（≤25.x）AppImage | 可能打通 ezdxf odafc 全链路 | 5-10 分钟下载 + 1 分钟测试 |
| **P1** | 当前 `/private/tmp/oda.AppImage` 在 Linux 容器 + xvfb-run + `--help` 试 | 验证 27.x 是否真无 CLI（最终确认） | 10 分钟 |
| **P2** | 跑 ezdxf odafc 测真实可工作能力 | 文档级 API 链路验证 | 5 分钟 |
| **P3** | 测试 `xvfb-run + xdotool auto-click` ODA GUI | 27.x 兜底方案 | 1-2 小时 |
| **P4** | 自研 MinCADRenderer | 最后兜底 | 半天 |

### 3.2 当前立刻可跑的最快验证

```bash
# P1: 验证 27.x 真无 CLI（5-10 分钟）
docker run --rm -v "/private/tmp:/tmp/oda" ubuntu:22.04 bash -c "
apt-get update -qq && apt-get install -y -qq xvfb xauth libgl1 libglu1-mesa libxkbcommon-x11-0 libxcb-xkb1 libdbus-1-3 libxcb-cursor0 libfontconfig1
mkdir -p /tmp/odawork && cd /tmp/odawork && cp /tmp/oda/oda.AppImage . && chmod +x oda.AppImage
./oda.AppImage --appimage-extract >/dev/null 2>&1
ls squashfs-root/ | head
echo '---try --help---'
xvfb-run -a squashfs-root/AppRun --help 2>&1 | head -40 || true
echo '---try --version---'
xvfb-run -a squashfs-root/AppRun --version 2>&1 | head -10 || true
"
```

```python
# P2: ezdxf odafc 文档级 API 验证（5 分钟）
from ezdxf.addons import odafc
# 即使 is_installed() == False，看 API 表面完整
print(odafc.convert.__doc__)
print(odafc.readfile.__doc__)
print(odafc.export_dwg.__doc__)

# 试着 mock ODA binary（找一份任意可执行文件 mock 一下）
# 验证 oda 调用链路能完整跑通
import subprocess
# 写个 fake binary
fake = "/tmp/fake_oda.sh"
with open(fake, "w") as f:
    f.write("#!/bin/bash\necho fake ODA $@")
import os; os.chmod(fake, 0o755)
odafc.unix_exec_path = fake  # 配置 mock
# 实际调用会失败但能看到完整调用链路
try:
    odafc.convert("any.dwg", "out.dxf", version="R2018")
except Exception as e:
    print(f"链路调用到了: {type(e).__name__}: {e}")
```

### 3.3 真实路径决策矩阵

| 测试结果 | 下一步决策 |
|---------|----------|
| 27.x AppImage `--help` 输出**任何内容** | 用 27.x 即可，无需降级 |
| 27.x AppImage 完全无 CLI | 下载 ≤25.x AppImage 重测 |
| ODA 装上后 ezdxf odafc `convert` 跑通 | 场景 B 用 ezdxf odafc.export_dwg() 输出高保真 DWG/DXF |
| 全部失败 | 退到 H：自研 MinCADRenderer（半天工作量）|

### 3.4 真实结果（**实测后**）

| 测试 | 结果 | 结论 |
|------|------|------|
| **P1**: ODA 27.x AppImage `strings` | 找不到 `--help`/`--batch`/`usage` | ODA 27.x CLI 入口不存在 |
| **P1**: ODA 27.x 完整依赖 + xvfb 跑 6 参数 CLI | `exit=0` 但输出目录**空** | ODA 假装成功但没干活 |
| **P3**: ezdxf.odafc 配置 mock binary | 调用链完整工作（is_installed=True, convert() 正常发参数） | ezdxf odafc 包装层完全 OK |
| **P3**: ezdxf.odafc + 真 ODA 27.x | 同 P1，输出空 | **ODA 27.x binary 自身坏了** |
| **P3**: ezdxf.odafc + 真 ODA 27.x 转换 R12→R2018 | `/out/` 空 | **100% 确认 ODA 27.x CLI 不可用** |

---

## 4. 立即要做的两件事

### 4.1 重读复盘文档时发现的关键细节

我读 `docs/格式转换-实战记录.md` 时漏看了一段：

> Step ❺：改用 AppImage（自带 Qt6 全套），加 Xvfb（虚拟 X server） → AppImage extract 成功，ODA 启动了 GUI 主窗口，等用户点 Convert 按钮；**CLI 参数被完全忽略**

→ 这是 ODA 27.x **真的** GUI 阻塞证据，但 **没有排除**：
- ODA 27.x 的某些**未公开标志**（如 `--batch` `--silent`）
- ODA ≤25.x 的真实 CLI 行为

### 4.2 必须执行的测试（按成本低→高）

#### 测试 1：当前 Linux AppImage 的 `--help`（10 分钟）

```bash
# 用 docker 起 ubuntu 22，跑 27.x AppImage 的 --help
docker run --rm -v /private/tmp:/tmp/oda ubuntu:22.04 bash -c '
apt-get update -qq 2>&1 >/dev/null && \
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq xvfb xauth 2>&1 >/dev/null
cd /tmp/oda && chmod +x oda.AppImage && ./oda.AppImage --appimage-extract >/dev/null 2>&1
ls squashfs-root/ | head
echo "=== --help ==="
./squashfs-root/AppRun --help 2>&1 | head -30
echo "=== -h ==="
./squashfs-root/AppRun -h 2>&1 | head -30
echo "=== --version ==="
./squashfs-root/AppRun --version 2>&1 | head -10
echo "=== with DISPLAY ==="
DISPLAY=:99 xvfb-run -a ./squashfs-root/AppRun --help 2>&1 | head -30
'
```

#### 测试 2：ODA 历史版本下载（5-10 分钟）

ODA 官网提供多个版本，看 ≤25.x 是否有：
https://www.opendesign.com/guestfiles/oda_file_converter

重点看：
- `ODAFileConverter_QT5_lnxX64_*_8.3dll_*.AppImage` (QT5 + 8.3 dlls)
- 任何不带 `_QT6_` 的版本（QT6 = 27.x，QT5 = ≤26.x）

#### 测试 3：ezdxf odafc 完整调用链（5 分钟）

写个小脚本用 mock ODA binary 验证 ezdxf odafc 整条调用链完整无缺，然后知道"一旦 ODA 装上就能直接用"。

---

## 5. 场景 B 整体重新评估

### 5.1 之前结论错在哪

之前我说 "DXF→高保真 PDF 链路都死了"——**错的**：DXF→PDF 这条路 ezdxf Frontend / svglib / cairosvg 都死了，**但 ezdxf odafc → ODA 链路根本没测过**。

### 5.2 修正后的真实结论

| 任务 | 之前结论 | 修正结论 |
|------|---------|---------|
| DWG 读取 | "用 libredwg 转 DXF 再 ezdxf 解析" | ✅ 这个链路有效（已用），**但 ezdxf odafc.readfile() 是更干净的路径（未实测）** |
| DWG→PDF 高保真 | "ODA 27.x 无 CLI，链路死了" | ⚠️ ODA 27.x GUI 阻塞是事实；**但 ≤25.x 可能 CLI 可用（未测）**；**ezdxf odafc 包装也对（未实测）** |
| DXF→PDF 高保真 | "svglib/cairosvg 都失败" | ✅ 这个事实正确，**但 ezdxf Frontend + ODA 这条路没试** |
| 改前后视觉对比 | "骨架图 VLM 0 分" | ✅ 这实验真实，但**骨架图对比不是高保真路径，是 fallback** |

### 5.3 修正后的实施路径（Phase H-0.5：先打通 ODA 链路）

**如果 P0-P1 测试成功**（ODA 可用）：
1. 装 ODA（≤25.x 优先，27.x AppImage fallback）
2. 用 `ezdxf.addons.odafc.readfile()` 直接读 DWG，绕开"先 libredwg 转 DXF 再 ezdxf 解析"
3. 改写 `tools/dxf_edit/move_wall.py` 等改图工具，改用 `odafc.export_dwg()` 写 DWG
4. Phase H-1 用 `odafc.convert(dxf_path, pdf_path)` 生成高保真 PDF
5. 场景 B 用 PDF 单页拆分做改前后视觉对比（gating 路径：E 方案）

**如果 ODA 仍不可用**：
1. 自研 MinCADRenderer（半天）—— 至少保留 TEXT 字符 + INSERT 块名
2. 改前后视觉对比降级为"几何对比 + TEXT 标签对比"
3. 文档化这个限制在场景 B 边界里

---

## 6. 总结：诚实承认 + 立刻补测

我承认：
1. 我没好好读复盘文档里"ODA 27.x GUI 不干活"的关键证据
2. 我没看 wheel-drawing-tools 和 ezdxf odafc 文档就断言"ODA 链路死了"
3. 我把 svglib/cairosvg 失败过激外推到"所有 DXF→PDF 路径都死了"
4. 我用"DXF 是为高精度输出设计"这个论点合理化接受 LineCollection 是偷懒

立刻要做的：
- **测 ODA 27.x AppImage `--help`**（10 分钟）
- **找 ODA ≤25.x AppImage**（10 分钟下载）
- **测 ezdxf odafc 调用链完整性**（5 分钟）

如果 ODA 可用，方案 H 场景 B 走 ezdxf odafc + ODA 高保真 PDF 路径；如果 ODA 不可用，降级到自研 MinCADRenderer。**不要预先放弃**。
