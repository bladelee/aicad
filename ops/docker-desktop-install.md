# Docker Desktop 安装手册（macOS Intel / Monterey 专用）

> 本文档记录 **2026-08-08 在 MacBookPro12,1（13" 2015）+ macOS 12.7.6 Monterey 上重装 Docker Desktop 4.35.0** 的完整可复现步骤。
> 是 `docker-troubleshooting.md`（问题排查 / 抢救 / 备份）的姊妹篇：本文档讲"怎么干净装起来"，那篇讲"出事了怎么办"。

## 0. 适用环境

| 项目 | 本次实测 | 备注 |
|------|---------|------|
| 机型 | `MacBookPro12,1`（13" 2015, Intel i5/i7） | **此机型最高仅支持 macOS 13 Ventura**，不能升 14/15 |
| macOS | 12.7.6 Monterey | 新版 Docker 要求 ≥ 11.0，12.7.6 满足 |
| Docker Desktop | **4.35.0（build 172550）** | macOS 12 兼容的**最后一档稳定版**，更高 4.36+ 已提升系统要求 |
| Docker Engine | 27.3.1 | （Docker Desktop 4.35 自带） |
| 磁盘可用 | ≥ 20 GB | 旧 31GB qcow2 删除后实测可用 85 GB |

### ⚠️ 为什么不是最新版？

`https://desktop.docker.com/mac/main/amd64/Docker.dmg` 默认下载最新版（当前 4.85+），**最低系统要求已提升到 macOS 13/14+**。
在 macOS 12 上启动会报：

```
kLSIncompatibleSystemVersionErr: The app cannot run on the current OS version
```

**必须按"构建号"下载 4.35.0**（build `172550`）。这是 macOS 12 上能跑的最后一档稳定版。

---

## 1. 清理旧版 Docker（关键，否则启动失败）

> 经验：旧 Docker 17.12 的配置文件会留在 `~/Library/Group Containers/group.com.docker/settings.json`，新版启动时读到 `"version": "17.12.0-ce-mac55"`、`"diskPath": "...Docker.qcow2"` 这些陈旧字段，会触发**VM 启动后立即 "stopped gracefully"** 错误。
> 必须清干净再装。

### 1.1 删除 Docker.app、镜像数据和残留链接

```bash
# (1) 关闭并卸载 Docker.app（如有）
sudo rm -rf /Applications/Docker.app
sudo rm -rf "/Applications/Docker Quickstart Terminal.app"   # 2016 Toolbox 残留
sudo rm -rf "/Applications/Kitematic (Beta).app"              # 2016 Toolbox 残留

# (2) 镜像数据（含旧版 Docker.qcow2）
sudo rm -rf ~/Library/Containers/com.docker.docker
rm -rf ~/Library/Group\ Containers/group.com.docker

# (3) 用户配置
rm -rf ~/.docker

# (4) /usr/local/bin 失效链接 + 旧 backup
cd /usr/local/bin
for f in docker docker-compose docker-credential-osxkeychain docker-machine hyperkit notary vpnkit; do
  [ -L "$f" ] && rm -f "$f"
done
rm -f docker.backup docker-compose.backup docker-machine.backup
```

### 1.2 系统级残留（可选清理）

| 文件 | 处理方式 |
|------|---------|
| `/Library/LaunchDaemons/com.docker.vmnetd.plist` | 新版安装时会自动覆盖，无需手动删 |
| `/Library/PrivilegedHelperTools/com.docker.vmnetd` | 同上，新版会替换 |
| `/usr/local/bin/kubectl` / `minikube`（2016/2018 装的） | **独立工具**，按需自行决定，不删也能用 |

---

## 2. 下载 Docker Desktop 4.35.0（按构建号）

### 2.1 直接下载（推荐）

```bash
URL="https://desktop.docker.com/mac/main/amd64/172550/Docker.dmg"
curl -L --progress-bar -o ~/Downloads/Docker.dmg "$URL"
ls -lh ~/Downloads/Docker.dmg   # 应约 488 MB
file ~/Downloads/Docker.dmg     # 应显示 "XZ compressed data"
```

### 2.2 自行探测其他版本（如 172550 未来不可用时）

```bash
# 历史 release notes 查构建号：https://docs.docker.com/desktop/release-notes/
# 用 HEAD 探测 CDN 是否还在分发该构建：
for build in 172550 175034 176780; do
  URL="https://desktop.docker.com/mac/main/amd64/${build}/Docker.dmg"
  echo "build=${build}: HTTP $(curl -s -o /dev/null -I -w '%{http_code}' --max-time 8 "$URL")"
done
```

返回 `200` 即可下载；`403` 表示该构建已下线。

### 2.3 验证 dmg 版本（防止下错）

```bash
hdiutil attach ~/Downloads/Docker.dmg -nobrowse
# 应输出：
#   CFBundleShortVersionString = 4.35.0
#   LSMinimumSystemVersion    = 11.0     ← 必须满足你的 macOS 版本
cat "/Volumes/Docker/Docker.app/Contents/Info.plist" | grep -A1 \
    "CFBundleShortVersionString\|LSMinimumSystemVersion\|CFBundleVersion"

hdiutil detach "/Volumes/Docker"
```

---

## 3. 安装（命令行）

> Docker 内置的 `install` 脚本已迁移位置、不是稳定入口；
> 官方文档的 `sudo /Volumes/Docker/Docker.app/Contents/MacOS/install` 在 4.35 上会报 `command not found`。
> 实测最稳的方式是 **ditto 复制 + lsregister 注册**。

```bash
# (1) 挂载
hdiutil attach ~/Downloads/Docker.dmg -nobrowse

# (2) ditto 复制（保留全部元数据、权限、扩展属性）
sudo ditto "/Volumes/Docker/Docker.app" "/Applications/Docker.app"

# (3) 清除 quarantine（绕过 Gatekeeper 把应用隔离到 AppTranslocation 的坑）
sudo xattr -dr com.apple.quarantine /Applications/Docker.app

# (4) 注册到 LaunchServices（让 `open -a Docker` 能找到应用）
LSREGISTER="/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister"
sudo "$LSREGISTER" -f /Applications/Docker.app

# (5) 卸载 dmg 并清理下载
hdiutil detach "/Volumes/Docker"
rm -f ~/Downloads/Docker.dmg
```

---

## 4. 首次启动（GUI 必须有人值守）

```bash
open -a "Docker"
```

首次启动会：

1. **安装特权 helper** `com.docker.vmnetd`（系统会弹密码框，输入即可）
2. **接受 Docker Subscription Service Agreement**（GUI 点击 Accept）—— 这一步**必须在图形界面完成，命令行无法跳过**
3. **创建 Linux VM** + `Docker.raw` 磁盘镜像（占时 30–90 秒）
4. **初始化 Engine**（首次会看到 Docker 鲸鱼图标变绿）

观察进程确认从正确路径启动（**不能含 `AppTranslocation`**，否则 daemon 起不来）：

```bash
pgrep -lf "Docker Desktop" | head -3
# 期望看到：/Applications/Docker.app/Contents/MacOS/Docker Desktop.app/...
```

---

## 5. 验证安装成功

```bash
docker version       # Client 和 Server 都应返回
docker info          # Server Version: 27.3.1，Storage Driver: overlay2
docker run --rm hello-world   # 看到 "Hello from Docker!" 即成功
docker images        # 应列出 hello-world 镜像
```

期望输出关键项：

| 字段 | 期望值 |
|------|--------|
| Client Version | 27.3.1 |
| Context | `desktop-linux` |
| Server: Docker Desktop | `4.35.0 (172550)` |
| Engine Version | 27.3.1 |
| containerd | 1.7.21 |
| Storage Driver | overlay2 |
| Kernel | 6.10.11-linuxkit |
| Operating System | Docker Desktop |

---

## 6. 推荐配置：国内镜像加速（可选）

镜像加速器能让国内拉取 Docker Hub 镜像速度大幅提升。
两种配置方式任选其一：

### 6.1 GUI 配置（推荐新手）

`Docker Desktop → Settings → Docker Engine`，粘贴 JSON：

```json
{
  "registry-mirrors": ["https://docker.m.daocloud.io"],
  "builder": {
    "gc": { "defaultKeepStorage": "20GB", "enabled": true }
  },
  "experimental": false
}
```

点击 **Apply & restart**。

### 6.2 命令行配置

```bash
mkdir -p ~/.docker
cat > ~/.docker/daemon.json <<'EOF'
{
  "registry-mirrors": ["https://docker.m.daocloud.io"]
}
EOF
# 重启 Docker 生效
osascript -e 'quit app "Docker"'; sleep 3; open -a "Docker"
```

### 6.3 验证加速器生效

```bash
docker info | grep -A3 "Registry Mirrors"
```

---

## 7. 关键路径速查（运维参考）

| 用途 | 路径 |
|------|------|
| 应用本体 | `/Applications/Docker.app` |
| Docker CLI | `$HOME/.docker/cli-plugins/`（buildx/compose/scout 等） |
| 镜像数据（VM 磁盘） | `$HOME/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw` |
| 应用配置 | `$HOME/Library/Group Containers/group.com.docker/settings-store.json` |
| 特权 helper | `/Library/PrivilegedHelperTools/com.docker.vmnetd` |
| LaunchDaemon | `/Library/LaunchDaemons/com.docker.vmnetd.plist` |
| Backend 日志 | `$HOME/Library/Containers/com.docker.docker/Data/log/host/` |
| Virtualization 日志 | `$HOME/Library/Containers/com.docker.docker/Data/log/host/com.docker.virtualization.log` |
| Socket | `$HOME/.docker/run/docker.sock`（`/var/run/docker.sock` 是软链） |

---

## 8. 常用运维命令

```bash
# 启动 / 停止 Docker Desktop（GUI）
open -a "Docker"
osascript -e 'quit app "Docker"'

# 查看 daemon 状态
docker info
docker ps -a
docker images
docker system df   # 查看镜像/容器/卷占用磁盘

# 进入 Docker Desktop VM 内部排查
docker run -it --rm --privileged --pid=host justincormack/nsenter1
# 或者
nc -U ~/Library/Containers/com.docker.docker/Data/vms/0/tty

# 重置 Docker Desktop（保留应用，清空所有数据）
# 菜单：Troubleshoot → Reset to factory defaults
```

---

## 9. 灾难恢复快速路径

若 Docker 启动异常 / 容器起不来 / 镜像数据损坏，**按此顺序排查**：

1. 看 GUI 是否启动：`pgrep -lf "Docker Desktop"`
2. 看 daemon 是否响应：`docker info`
3. 看 VM 日志：`tail -100 ~/Library/Containers/com.docker.docker/Data/log/host/com.docker.virtualization.log`
4. 看 backend 日志：`find ~/Library/Containers/com.docker.docker/Data/log/host/ -name "*backend*"`
5. **核武级重置**：`Troubleshoot → Reset to factory defaults`（清空所有镜像/容器/卷）
6. **彻底重装**：参照本文档第 1 节清理 + 2-4 节重装

**详细排查与备份/迁移方案见 `docker-troubleshooting.md`。**

---

## 10. 复现性自检脚本

把以下存为 `ops/check-docker-install.sh`，新机器或重装后跑一遍即可：

```bash
#!/usr/bin/env bash
set -u
fail=0
echo "[1/6] docker CLI..."
docker --version >/dev/null 2>&1 || { echo "✗ docker 命令不可用"; fail=1; }
echo "[2/6] Docker daemon..."
docker info >/dev/null 2>&1 || { echo "✗ daemon 未运行"; fail=1; }
echo "[3/6] 应用路径..."
pgrep -lf "Docker Desktop" | grep -q "/Applications/Docker.app" || \
  { echo "✗ 未从 /Applications 启动"; fail=1; }
echo "[4/6] 版本号..."
v=$(docker version --format '{{.Server.Version}}' 2>/dev/null)
[[ "$v" == 27.* ]] || { echo "✗ Server 版本不符：$v"; fail=1; }
echo "[5/6] hello-world 容器..."
docker run --rm hello-world >/dev/null 2>&1 || { echo "✗ 容器运行失败"; fail=1; }
echo "[6/6] 镜像加速器..."
docker info 2>/dev/null | grep -q "Registry Mirrors" || echo "⚠️  未配置镜像加速器"
[[ $fail -eq 0 ]] && echo "✅ Docker 安装自检全部通过" || exit 1
```
