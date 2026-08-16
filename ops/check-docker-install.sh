#!/usr/bin/env bash
# Docker Desktop 安装自检脚本
# 用法：bash ops/check-docker-install.sh
# 退出码 0 = 全部通过；非 0 = 有失败项

set -u

green() { printf "\033[32m%s\033[0m\n" "$1"; }
red()   { printf "\033[31m%s\033[0m\n" "$1"; }
yellow(){ printf "\033[33m%s\033[0m\n" "$1"; }

fail=0

echo "==============================="
echo " Docker Desktop 安装自检"
echo "==============================="
echo ""

# 1. docker CLI
printf "[1/7] docker CLI 是否可用... "
if docker --version >/dev/null 2>&1; then
  green "✓ $(docker --version)"
else
  red "✗ docker 命令不可用"; fail=1
fi

# 2. daemon 响应
printf "[2/7] Docker daemon 是否响应... "
if docker info >/dev/null 2>&1; then
  green "✓ daemon 响应中"
else
  red "✗ daemon 未运行（先 open -a Docker）"; fail=1
fi

# 3. 应用从 /Applications 启动
printf "[3/7] Docker Desktop 是否从 /Applications 启动... "
if pgrep -lf "Docker Desktop" 2>/dev/null | grep -q "/Applications/Docker.app"; then
  green "✓ 正确路径"
else
  red "✗ 未从 /Applications 启动（可能落入 AppTranslocation）"; fail=1
fi

# 4. 版本号
printf "[4/7] Server 版本... "
v=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "")
if [[ "$v" == 27.* ]]; then
  green "✓ $v"
else
  red "✗ Server 版本异常：$v"; fail=1
fi

# 5. Storage driver
printf "[5/7] Storage Driver... "
sd=$(docker info --format '{{.Driver}}' 2>/dev/null || true)
if [[ "${sd:-}" == "overlay2" ]]; then
  green "✓ overlay2"
else
  yellow "⚠️  Storage Driver: $sd（推荐 overlay2）"
fi

# 6. 容器运行测试
printf "[6/7] 容器运行测试 (hello-world)... "
if docker run --rm hello-world 2>/dev/null | grep -q "Hello from Docker"; then
  green "✓ 容器可运行"
else
  red "✗ 容器运行失败"; fail=1
fi

# 7. 镜像加速器（仅警告）
printf "[7/7] 镜像加速器... "
if docker info 2>/dev/null | grep -q "Registry Mirrors"; then
  green "✓ 已配置"
else
  yellow "⚠️  未配置镜像加速器（拉镜像慢时建议配 daocloud）"
fi

echo ""
echo "==============================="
if [[ $fail -eq 0 ]]; then
  green "✅ Docker 安装自检全部通过"
  exit 0
else
  red   "❌ 有失败项，请参阅 ops/docker-troubleshooting.md"
  exit 1
fi
