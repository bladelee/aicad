# Docker 排错与运维手册

> 记录 **2026-08-08 升级 Docker 17.12 → 4.35.0 过程中踩过的所有坑**，以及日后出现问题时的运维、备份、迁移方案。
> 是 `docker-desktop-install.md`（干净安装步骤）的姊妹篇。

## 目录

- [1. 本次升级踩坑实录](#1-本次升级踩坑实录)
- [2. 常见错误 & 速查表](#2-常见错误--速查表)
- [3. 日志位置与查看](#3-日志位置与查看)
- [4. 镜像备份与迁移](#4-镜像备份与迁移)
- [5. 磁盘空间治理](#5-磁盘空间治理)
- [6. 重置与彻底重装](#6-重置与彻底重装)
- [7. 性能与资源调优](#7-性能与资源调优)
- [8. 紧急联系路径](#8-紧急联系路径)

---

## 1. 本次升级踩坑实录

按时间顺序，每个坑都标注**根因**与**永久规避方法**。下次再遇到能直接对号入座。

### 坑 #1：直接下 `main/amd64/Docker.dmg` 拿到的是最新版（macOS 12 跑不了）

**症状**
```
kLSIncompatibleSystemVersionErr: The app cannot run on the current OS version
```

**根因**：Docker 官方 `main/amd64/Docker.dmg` 始终重定向到最新版，最新版要求 macOS 13+。
旧机器（如 MacBookPro12,1）最高只能升到 macOS 13 Ventura，但即便升上去也不一定能满足 Docker 4.x 的最新要求。

**永久规避**：按**构建号**下载 4.35.0（build `172550`）。
```bash
curl -L -o Docker.dmg https://desktop.docker.com/mac/main/amd64/172550/Docker.dmg
```

⚠️ 构建号会下线。可以用 HEAD 探测 CDN：
```bash
for build in 172550 175034 176780; do
  url="https://desktop.docker.com/mac/main/amd64/${build}/Docker.dmg"
  echo "build=${build}: HTTP $(curl -s -o /dev/null -I -w '%{http_code}' --max-time 8 "$url")"
done
```
有 `200` 就能下。

---

### 坑 #2：旧 settings.json 让新版 VM 启动后立即退出

**症状**：`docker info` 报 `Cannot connect to the Docker daemon`。
查 `~/Library/Containers/com.docker.docker/Data/log/host/com.docker.virtualization.log` 看到：
```
VM has started
... (60 秒后)
VM has stopped gracefully
vz.RunApplication returned
```

**根因**：`~/Library/Group Containers/group.com.docker/settings.json` 是 2018 年 Docker 17.12 的旧配置：
```json
{
  "version": "17.12.0-ce-mac55",
  "diskPath": ".../Docker.qcow2"   // 这个文件已被我们删除
}
```
新版 Docker 4.35 读到这个配置，去挂载不存在的 qcow2，VM 起不来。

**永久规避**：装新版前**必须**完全清除旧配置（见 `docker-desktop-install.md` 第 1.1 节）。
清理 `~/Library/Group Containers/group.com.docker/` 下所有 json 后，新版本才能用自己的 `settings-store.json` 重建配置。

---

### 坑 #3：AppTranslocation 让 daemon 起不来

**症状**：GUI 起来了，但 daemon 不响应。
`ps aux | grep Docker` 看到进程路径是：
```
/var/folders/.../T/AppTranslocation/C5C07E2E-.../d/Docker.app/...
```

**根因**：macOS Gatekeeper 对带 `com.apple.quarantine` 扩展属性、且非通过 `install` 命令注册的 DMG 应用，会把它"转位"（translocate）到 `/private/var/folders/.../T/AppTranslocation/...` 隔离区执行。
**在 translocation 路径下 Docker 不能创建/读取真实镜像数据**，VM 起得来但 backend 找不到资源。

**永久规避**：复制后立即清除 quarantine 属性。
```bash
sudo ditto "/Volumes/Docker/Docker.app" "/Applications/Docker.app"
sudo xattr -dr com.apple.quarantine /Applications/Docker.app   # 关键
```
然后再启动。

---

### 坑 #4：CLI 插件路径 `~/.docker/cli-plugins/` 是死链

**症状**：
```
WARNING: Plugin "/Users/bladelee/.docker/cli-plugins/docker-buildx" is not valid:
failed to fetch metadata: fork/exec ...: no such file or directory
```

**根因**：`~/.docker/cli-plugins/` 下原是 2018 旧版 Docker 创建的死链，新版 Docker 启动时还没来得及重新写入。

**永久规避**：装新版前删干净。
```bash
rm -rf ~/.docker/cli-plugins ~/.docker/config.json ~/.docker/context.json
```
Docker Desktop 启动后会把 plugins 重新装到 `~/.docker/cli-plugins/`（buildx/compose/scout 等）。

⚠️ 之后再次完整启动（保留配置），插件本身就在正确路径了，不用每次清。

---

### 坑 #5：`sudo /Volumes/Docker/Docker.app/Contents/MacOS/install` 报 `command not found`

**症状**：执行官方文档的命令行安装指令直接失败。

**根因**：Docker Desktop 4.35 调整了内部结构，`install` 二进制不再放在 `Docker.app/Contents/MacOS/` 下。

**永久规避**：用 ditto + lsregister 替代：
```bash
sudo ditto "/Volumes/Docker/Docker.app" "/Applications/Docker.app"
sudo xattr -dr com.apple.quarantine /Applications/Docker.app
LSREGISTER="/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister"
sudo "$LSREGISTER" -f /Applications/Docker.app
```

---

### 坑 #6：buildkit 报 `failed size validation: X != Y: failed precondition`

**症状**：执行 `docker compose build` 或 `docker build` 时报：
```
ERROR: failed commit on ref "unknown-sha256:...": "..." failed size validation: 316357 != 316273: failed precondition
failed to solve: ubuntu:22.04: failed to resolve source metadata for docker.io/library/ubuntu:22.04
```

**根因**：Docker buildkit 内部 metadata 缓存损坏，`docker pull` 单独能成功，但 buildkit 走的是另一条 metadata 路径。
> 注意 `docker builder prune -af` 第一次可能只清出 3.4KB（看似没用），其实它清的是 dangling。**真正的损坏层会留在另一份 cache 里**。

**永久规避**：先 stop buildkit，再 prune，再 pull：
```bash
docker buildx stop                                              # 关掉 builder
docker builder prune -af                                        # 强清（这次会列出真实损坏层大小，约 200MB+）
docker pull <你的基础镜像>:<tag>                                 # 重新拉取
docker compose build --progress plain 2>&1 | tee build.log      # 重试构建，输出到文件方便定位
```

⚠️ 不要相信 `docker compose build ... | tail -40`，pipe 会缓冲构建进度，让人误以为卡住。
**应该用 `tee build.log`**，再用 `tail -f build.log` 在另一个终端实时看。

---

### 坑 #7：FreeCAD AppImage 解包后 `python3` 路径与环境变量

**症状**：Dockerfile 里 `RUN /opt/FreeCAD/usr/bin/python3 -m pip install ...` 报：
```
/bin/sh: 1: /opt/FreeCAD/usr/bin/python3: not found
```
即使文件确实存在。

**根因（双重坑）**：
1. **文件名**：AppImage 解包后可执行文件是 `/opt/FreeCAD/usr/bin/python`（**无版本号后缀**），不是 `python3` 或 `python3.11`。
2. **动态链接器**：即使调用 `python` 也报 "not found" —— 因为 FreeCAD 是 conda 打包的，依赖 `PYTHONHOME` 环境变量来定位 `libpython3.11.so`。**裸调不设环境变量，loader 找不到依赖**。这并非 `python` 文件不存在，而是 loader 报错。

**永久规避**：所有在容器内调用 FreeCAD Python 的命令，**必须**带上 AppRun 等价的环境变量：
```dockerfile
RUN PYTHONHOME=/opt/FreeCAD/usr \
    LD_LIBRARY_PATH=/opt/FreeCAD/usr/lib \
    SSL_CERT_FILE=/opt/FreeCAD/usr/ssl/cacert.pem \
    /opt/FreeCAD/usr/bin/python -m pip install --no-cache-dir ezdxf shapely
```

对应的运行时（`docker exec`、entrypoint）也必须导出这些变量。

⚠️ **不要用 `RUN ... || true` 吞掉 pip 失败**。本次踩坑就是因为 Dockerfile 里写了 `|| true`，pip 没装上但镜像"构建成功"，**到运行时才会爆**。

---

### 坑 #8：错误的 `<none>:<none>` 镜像堆积

**症状**：每次重 build 后，旧版本镜像变成 `<none>:<none>`（dangling），仍占满磁盘却不显眼。

**永久规避**：
```bash
docker image prune -f           # 清理 dangling（未被任何 tag 引用的镜像）
# 或在 build 时直接覆盖：
docker compose build            # 自动让新 build 复用同 tag，老的悬空
```

定期跑 `docker system df` 监控磁盘占用。

---

## 2. 常见错误 & 速查表

| 错误信息 / 症状 | 根因 | 解决 |
|----------------|------|------|
| `Cannot connect to the Docker daemon at unix:///Users/.../docker.sock` | Docker Desktop 没启动 / VM 没起来 | `open -a Docker`，等 30 秒重试 `docker info` |
| `kLSIncompatibleSystemVersionErr` (LSOpen -10825) | Docker 版本要求高于当前 macOS | 装构建号 172550（4.35.0） |
| `kLSServerCommunicationErr` (LSOpen -10822) | 旧应用在 macOS 12 上 LaunchServices 拒绝加载 | 同上，必须升级 |
| `hdiutil attach failed - 设备未配置` | dmg 文件损坏 / 第一次 attach 时 IO 延迟 | 等 2 秒重试 `hdiutil attach` |
| VM 启动 60 秒后 `stopped gracefully` | settings.json 是旧版残留 | 删 `Group Containers/group.com.docker/` |
| docker info 只看到 Client，没有 Server | VM 还在 booting 中，或 backend 起不来 | 等 30-60 秒；查 virtualization.log |
| `fork/exec .../docker-buildx: no such file or directory` | ~/.docker/cli-plugins 是死链 | 删 ~/.docker，重启 Docker Desktop |
| Docker 鲸鱼图标一直转不绿 | 特权 helper 权限 / 网络代理 / 数据库损坏 | Troubleshoot → Reset to factory defaults |
| Docker.qcow2 损坏提示 | qcow2 跨代不兼容（17.12 → 4.35） | 直接删除重建，不要尝试转换 |
| `AppTranslocation` 出现在进程路径 | dm 解压后被 Gatekeeper 隔离 | `xattr -dr com.apple.quarantine` |
| 拉镜像超时（`i/o timeout`） | 国内访问 Docker Hub 慢 | 配 daocloud 镜像加速器 |

---

## 3. 日志位置与查看

### 3.1 主日志目录

```
~/Library/Containers/com.docker.docker/Data/log/host/
```

含以下关键日志：

| 日志 | 作用 |
|------|------|
| `com.docker.virtualization.log` | **VM 启停日志**，VM 起不来查这个 |
| `com.docker.backend.log` | backend 服务日志 |
| `electron-YYYY-MM-DD.log` | GUI（Electron）日志，含 GUI 报错 |
| `httpproxy.log` | HTTP 代理日志（拉镜像慢可查） |
| `com.docker.build.stderr.log` | buildkit 构建错误 |

### 3.2 快速诊断命令

```bash
# 一键体检
docker info 2>&1 | head -20
docker system df
docker ps -a

# VM 是否在跑
pgrep -fl "Virtualization.VirtualMachine"

# 最近的 VM 错误
tail -100 ~/Library/Containers/com.docker.docker/Data/log/host/com.docker.virtualization.log | grep -iE "error|fail|stop"

# 收集诊断包（给 Docker 官方支持用）
/Applications/Docker.app/Contents/Resources/bin/com.docker.diagnose
# 或菜单：Troubleshoot → Get support
```

---

## 4. 镜像备份与迁移

### 4.1 单镜像导出/导入（最常用）

```bash
# 导出（保留所有层）
docker save -o myimage.tar myimage:latest
# 或多个镜像打包
docker save -o all.tar image1:tag1 image2:tag2

# 导入到另一台机器
docker load -i myimage.tar
```

### 4.2 容器内文件系统导出（含数据但不层结构化）

```bash
docker export <容器ID> > container.tar
docker import container.tar newimage:latest
```

⚠️ `export/import` 会丢层历史和元数据，**不推荐**用于正式迁移。优先用 `save/load`。

### 4.3 全量备份 Docker.raw（VM 磁盘）

```bash
# 停掉 Docker（保证一致性）
osascript -e 'quit app "Docker"'
sleep 5

# 备份 VM 磁盘（Docker.raw）
RAW=~/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw
ls -lh "$RAW"   # 看实际占用
cp "$RAW" ~/DockerDesktop-backup-$(date +%Y%m%d).raw
```

⚠️ Docker.raw 是稀疏文件，实际占用可能远小于显示大小。
备份时建议用 `rsync --sparse`：
```bash
rsync --sparse --progress "$RAW" /Volumes/外置硬盘/Docker.raw.bak
```

### 4.4 迁移到另一台 Mac

```bash
# 源机器（导出所有镜像）
docker images -q | xargs -n1 docker save -o /Volumes/外置盘/images-bundle.tar

# 目标机器（导入）
docker load -i /Volumes/外置盘/images-bundle.tar
```

### 4.5 Volume 数据备份

```bash
# 单个 volume
docker run --rm -v myvolume:/data -v $(pwd):/backup alpine \
  tar czf /backup/myvolume.tar.gz -C /data .

# 恢复
docker run --rm -v myvolume:/data -v $(pwd):/backup alpine \
  tar xzf /backup/myvolume.tar.gz -C /data
```

---

## 5. 磁盘空间治理

Docker 是磁盘大户，定期清理很必要。

### 5.1 查看占用

```bash
docker system df -v   # 详细到每层每镜像
```

### 5.2 安全清理

```bash
# 清理停止的容器、悬空镜像、悬空卷、未使用网络
docker system prune

# 进一步清理：含未被任何容器引用的镜像（小心！）
docker system prune -a

# 还加上未使用的 volume（最激进，确认无重要数据再跑）
docker system prune -a --volumes
```

### 5.3 防止未来膨胀

Docker Desktop 设置：**Settings → Resources → Disk image size** 限制 VM 磁盘上限。
或在 `settings-store.json` 改：
```json
{
  "diskSizeMiB": 65536   // 64 GB，根据磁盘调整
}
```

---

## 6. 重置与彻底重装

按"力度"由弱到强排列。

### 6.1 软重置：保留应用、清空所有数据

Docker Desktop 菜单：**Troubleshoot → Reset to factory defaults**

等价命令（删除 VM 磁盘和容器数据，保留 Docker.app）：
```bash
osascript -e 'quit app "Docker"'
sleep 5
rm -f ~/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw
rm -f ~/Library/Group\ Containers/group.com.docker/settings-store.json
open -a "Docker"
```

### 6.2 彻底重装：从零开始

完全按 [`docker-desktop-install.md`](./docker-desktop-install.md) 第 1 节清理 + 第 2-4 节重装。

### 6.3 核武级：手动清理系统级残留

```bash
# 关闭并卸载
osascript -e 'quit app "Docker"'
sudo rm -rf /Applications/Docker.app
sudo rm -rf /Library/PrivilegedHelperTools/com.docker.vmnetd
sudo rm -f /Library/LaunchDaemons/com.docker.vmnetd.plist
sudo rm -rf ~/Library/Containers/com.docker.docker
sudo rm -rf ~/Library/Group\ Containers/group.com.docker
sudo rm -rf ~/.docker
# 再按 docker-desktop-install.md 重装
```

---

## 7. 性能与资源调优

### 7.1 调整 CPU/内存

Docker Desktop：**Settings → Resources**

或编辑 `~/Library/Group Containers/group.com.docker/settings-store.json`：
```json
{
  "cpus": 4,        // 上限：物理核数
  "memoryMiB": 8192 // 上限：物理内存一半
}
```

### 7.2 VirtioFS 文件系统挂载（macOS 12+ 推荐）

新版默认 VirtioFS（远快于旧的 osxfs/Grumble）。
确认在 Settings → Resources → File sharing 启用。

### 7.3 关闭不需要的功能

Settings → Features in development：
- 关闭 Kubernetes（如不用 K8s）
- 关闭 Docker Extensions
- 关闭 Background Updates（减少后台 CPU）

### 7.4 调整镜像 GC

```json
{
  "builder": {
    "gc": {
      "enabled": true,
      "defaultKeepStorage": "20GB"   // 超过就自动清理旧 buildkit 缓存
    }
  }
}
```

### 7.5 减小镜像体积

- 基镜像优先用 `alpine` / `*-slim`
- 多阶段构建（multi-stage build）
- 合并 RUN 指令减少层
- 用 `.dockerignore` 排除 `.git`、`node_modules`、`__pycache__` 等

---

## 8. 紧急联系路径

| 资源 | URL |
|------|-----|
| 官方 Mac 安装文档 | https://docs.docker.com/desktop/install/mac-install/ |
| Release Notes（查构建号） | https://docs.docker.com/desktop/release-notes/ |
| 故障排查总览 | https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/ |
| 已知问题 | https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/known-issues/ |
| Docker Forum | https://forums.docker.com/ |
| GitHub Issue（Docker Desktop） | https://github.com/docker/desktop/issues |
| 本机诊断信息收集 | `/Applications/Docker.app/Contents/Resources/bin/com.docker.diagnose` |

---

## 附录：本次升级关键决策记录

| 决策 | 原因 |
|------|------|
| 不保留旧 31GB Docker.qcow2 | 跨 7 年格式不兼容（qcow2/HyperKit → raw/Virtualization.framework），且旧 daemon 已无法启动 |
| 装构建号 172550 (4.35.0) | macOS 12.7.6 支持的最高稳定版 |
| 用 ditto + lsregister 替代 install 命令 | 4.35 已无 `install` 入口 |
| 必须清 quarantine 属性 | 否则触发 AppTranslocation，daemon 起不来 |
| 必须删 Group Containers 旧 settings.json | 否则新版读到旧版 qcow2 路径，VM 启动后立即退出 |
