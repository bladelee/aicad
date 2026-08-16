# floorplan-mcp 镜像构建手册

> 记录 **2026-08-08 在 macOS 12.7 + Docker Desktop 4.35 上构建 `floorplan-mcp:latest`（3.47GB）** 的全过程，
> 含本次踩过的 2 个坑（buildkit cache 损坏、FreeCAD Python 路径）和正确的复现命令。
> 排错见 `docker-troubleshooting.md` 坑 #6 / #7。

## 1. 镜像概览

| 项目 | 值 |
|------|-----|
| 镜像名 | `floorplan-mcp:latest` |
| 当前 image id | `26e26d996da0`（2026-08-08 构建） |
| 大小 | 3.47 GB |
| 基镜像 | `ubuntu:22.04` (78 MB) |
| 关键组件 | FreeCAD 1.0.2（AppImage 解包）+ freecad-ai + ezdxf 1.4.4 + shapely 2.1.2 + matplotlib 3.10.5 + numpy 1.26.4 |
| 工具数 | 49（freecad-ai 自带 + user_tools 扩展） |
| 构建耗时 | 首次约 **2-3 分钟**（macOS 12.7 + SSD + 国内裸连 GitHub） |

## 2. 构建前检查

```bash
# Docker 健康检查
bash ops/check-docker-install.sh

# 项目源文件齐全
ls /Users/bladelee/project/cad/floorplan-mcp/
# 应含: Dockerfile, docker-compose.yml, entrypoint.sh, install_oda.sh,
#        mcp_server_stdio.py, tools/, backends/
```

## 3. 标准构建流程

```bash
cd /Users/bladelee/project/cad/floorplan-mcp

# 构建并把日志写到文件（重要：tee 比 tail 管道更可靠）
docker compose build --progress plain 2>&1 | tee /tmp/floorplan-build.log

# 构建完成后立即清掉 dangling（避免磁盘膨胀）
docker image prune -f
```

### 3.1 构建日志关键检查点

构建完成后 grep 这几行确认无异常：

```bash
# 1. ubuntu 基镜像 metadata commit 无 size validation 错误
grep "failed size validation" /tmp/floorplan-build.log   # 应无输出

# 2. FreeCAD AppImage 解包成功
grep "DONE.*appimage-extract" /tmp/floorplan-build.log    # 应有 DONE 标记

# 3. pip install 正常完成（不再有 "not found"）
grep "Successfully installed" /tmp/floorplan-build.log    # 应有输出
grep "python3: not found" /tmp/floorplan-build.log        # 应无输出

# 4. 最终镜像写入
grep "naming to docker.io/library/floorplan-mcp" /tmp/floorplan-build.log
```

## 4. 镜像自检（构建后必跑）

```bash
# 验证所有依赖包都能 import
docker run --rm \
    -e PYTHONHOME=/opt/FreeCAD/usr \
    -e LD_LIBRARY_PATH=/opt/FreeCAD/usr/lib \
    -e SSL_CERT_FILE=/opt/FreeCAD/usr/ssl/cacert.pem \
    --entrypoint=/bin/bash \
    floorplan-mcp:latest \
    -lc '/opt/FreeCAD/usr/bin/python -c "import ezdxf, shapely, matplotlib, numpy; print(\"ezdxf\", ezdxf.__version__); print(\"shapely\", shapely.__version__); print(\"matplotlib\", matplotlib.__version__); print(\"numpy\", numpy.__version__)"'
```

期望输出：
```
ezdxf 1.4.4
shapely 2.1.2
matplotlib 3.10.5
numpy 1.26.4
```

## 5. 容器启动与端到端验证

```bash
cd /Users/bladelee/project/cad/floorplan-mcp
mkdir -p ~/dwgs
# 放一张测试 DXF 进去（可选）
cp examples/test_apartment.dxf ~/dwgs/ 2>/dev/null || true

# 启动容器
docker compose up -d

# 验证 entrypoint 输出（应看到 "容器已就绪"）
docker logs floorplan-mcp | head -10

# 端到端：通过 docker exec 拉起 MCP server，发个 initialize 看响应
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"local-test","version":"0.0"}}}' | \
    docker exec -i floorplan-mcp /opt/FreeCAD/usr/bin/python /opt/floorplan/mcp_server_stdio.py 2>&1 | head -3

# 应输出（最后一行即注册的 49 个工具）：
# [floorplan-mcp] user_tools linked at /root/.config/FreeCAD/FreeCADAI/tools
# [floorplan-mcp] backend = freecad
# [floorplan-mcp] registered tools: ['create_primitive', 'create_body', ...]

# 停掉容器（保留镜像）
docker compose down
```

## 6. 常用运维命令

```bash
# 查看镜像信息
docker images floorplan-mcp
docker image inspect floorplan-mcp:latest --format '{{.Size}}'

# 进入容器排查（带正确的环境变量）
docker run --rm -it \
    -e PYTHONHOME=/opt/FreeCAD/usr \
    -e LD_LIBRARY_PATH=/opt/FreeCAD/usr/lib \
    -e SSL_CERT_FILE=/opt/FreeCAD/usr/ssl/cacert.pem \
    --entrypoint=/bin/bash \
    floorplan-mcp:latest

# 查看镜像构建层（用于诊断镜像体积）
docker history floorplan-mcp:latest --no-trunc | head -30

# 重新构建（强制不缓存某层）
# 例：只重跑 pip install 那一层（如果改了 Dockerfile 的依赖列表）
docker compose build --no-cache --build-arg CACHEBUST=$(date +%s)
```

## 7. 改了源代码后

只要 Dockerfile + tools/backends/entrypoint 等没变，仅 `tools/` 或 `backends/` 下 Python 文件改了，
**docker compose build 会自动识别 COPY 层失效，只重跑后面几层**（约 30 秒）。

```bash
# 日常修改后的标准操作
docker compose build            # 增量构建
docker compose up -d            # 重启容器（用新镜像）
docker logs floorplan-mcp       # 看日志
```

## 8. 镜像导出与分发

```bash
# 导出（约 1.4 GB 压缩，3.47 GB 未压缩）
docker save floorplan-mcp:latest | gzip > floorplan-mcp.tar.gz

# 在另一台机器导入
gunzip -c floorplan-mcp.tar.gz | docker load
```

## 9. 故障排查清单

| 症状 | 排查路径 |
|------|---------|
| `docker compose up` 起不来、容器秒退 | `docker logs floorplan-mcp` 看 entrypoint 报错 |
| `pip install ... not found` | 见 `docker-troubleshooting.md` 坑 #7，环境变量没设 |
| build 报 `failed size validation` | 见 `docker-troubleshooting.md` 坑 #6，buildkit cache 损坏 |
| 容器里 `python` 报 `No such file` | 同坑 #7，PYTHONHOME 没设 |
| 镜像超过磁盘限制 | `docker system df -v`；`docker image prune -f` |
| 工具数 < 49 | 检查 `tools/floorplan_tools.py` 是否正确链接到 user_tools 目录 |
| MCP server 无响应 | entrypoint 是否成功（看 `docker logs`）；PYTHONPATH 是否含 `/opt/floorplan` |

## 10. 关键 Dockerfile 段落解读（2026-08-08 修订后的正确写法）

```dockerfile
# 备选 backend 需要 ezdxf + shapely（装到 FreeCAD 的 conda Python）
# 注意：AppImage 解包后可执行文件是 /opt/FreeCAD/usr/bin/python（无版本号后缀），
# 且必须设 PYTHONHOME（AppRun 的关键 env），否则 loader 找不到 libpython，报 "No such file"。
# 不用 `|| true`，让 pip 失败立即失败（更容易发现构建问题）。
ENV FREECAD_PYTHONHOME=/opt/FreeCAD/usr
ENV FREECAD_LIBDIR=/opt/FreeCAD/usr/lib
RUN PYTHONHOME=/opt/FreeCAD/usr \
    LD_LIBRARY_PATH=/opt/FreeCAD/usr/lib:/opt/FreeCAD/usr/lib/python3.11/site-packages/numpy.libs \
    SSL_CERT_FILE=/opt/FreeCAD/usr/ssl/cacert.pem \
    /opt/FreeCAD/usr/bin/python -m pip install --no-cache-dir \
        ezdxf matplotlib shapely
```

要点：
1. **`python`** 不是 `python3`
2. **必须**带 `PYTHONHOME` + `LD_LIBRARY_PATH`
3. **不要** `|| true`
4. matplotlib/numpy 在 conda 里自带，pip 会自动跳过
