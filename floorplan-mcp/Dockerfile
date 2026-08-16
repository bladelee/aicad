# floorplan-mcp 镜像
# 单镜像三平台通用（Win/macOS/Linux Docker）
#
# 关键决策（调研自 ghbalf/freecad-ai）:
#   1. headless 渲染用 QT_QPA_PLATFORM=offscreen（不是 Xvfb，省 ~500MB）
#   2. AppImage 先 --appimage-extract 解包，绕开容器无 FUSE 问题
#   3. FreeCAD C++ 非线程安全 —— 复用 freecad-ai 的 QtMainThreadToolExecutor
#   4. 锁 FreeCAD_1.0.2-conda-Linux-x86_64-py311.AppImage（freecad-ai conftest 同版本）
#   5. ODA 不打包（EULA），entrypoint 引导用户挂载（见 install_oda.sh）
#
# 镜像 build 出来后通过 entrypoint.sh 启动 freecad-ai 的 mcp_server_http.py（SSE）

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV QT_QPA_PLATFORM=offscreen
ENV PYTHONUNBUFFERED=1

# 系统依赖：FreeCAD AppImage 运行需要（FUSE 不需，因我们 extract）+ offscreen Qt 的 GL
RUN apt-get update && apt-get install -y --no-install-recommends \
        wget ca-certificates \
        libgl1 libglu1-mesa libgl1-mesa-dri \
        libxkbcommon0 libdbus-1-3 libfontconfig1 \
        libxrender1 libxext6 libx11-6 libxcb1 \
        libglib2.0-0 libsm6 libxrandr2 libxi6 \
        libfreetype6 libpng16-16 \
        python3 python3-pip \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt

# ─── FreeCAD（extract AppImage，避免 FUSE 依赖）───
ARG FREECAD_APPIMAGE=FreeCAD_1.0.2-conda-Linux-x86_64-py311.AppImage
ARG FREECAD_URL=https://github.com/FreeCAD/FreeCAD/releases/download/1.0.2/${FREECAD_APPIMAGE}
RUN wget -q "${FREECAD_URL}" -O /tmp/FreeCAD.AppImage \
    && chmod +x /tmp/FreeCAD.AppImage \
    && cd /opt && /tmp/FreeCAD.AppImage --appimage-extract >/dev/null \
    && mv squashfs-root FreeCAD \
    && rm /tmp/FreeCAD.AppImage
ENV FREECAD_HOME=/opt/FreeCAD
ENV PATH="${FREECAD_HOME}/usr/bin:${PATH}"
# FreeCAD 的 Python 在 /usr/lib，把 FreeCAD 的 Mod 加入 PYTHONPATH
ENV PYTHONPATH="${FREECAD_HOME}/usr/lib:${FREECAD_HOME}/usr/Mod:${PYTHONPATH}"

# ─── freecad-ai（作为 FreeCAD 工作台插件）───
ARG FREECAD_AI_REF=master
RUN mkdir -p /opt/freecad-ai \
    && wget -qO- "https://github.com/ghbalf/freecad-ai/archive/${FREECAD_AI_REF}.tar.gz" \
       | tar xz -C /opt/freecad-ai --strip-components=1
# freecad-ai stdlib only，无需装包；它的 user_tools 扩展机制自动发现工具

# ─── 我们自己的装修图工具 + stdio 入口 + backends ──
COPY tools /opt/floorplan/tools
COPY backends /opt/floorplan/backends
COPY mcp_server_stdio.py /opt/floorplan/mcp_server_stdio.py
ENV FLOORPLAN_TOOLS_FILE=/opt/floorplan/tools/floorplan_tools.py
ENV FLOORPLAN_BACKEND=${FLOORPLAN_BACKEND:-freecad}
ENV PYTHONPATH="${PYTHONPATH}:/opt/floorplan:/opt/freecad-ai"

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
        ezdxf matplotlib shapely pytest

# ─── 我们的 user_tools 注册到 freecad-ai 的 USER_TOOLS_DIR ──
# freecad-ai 扩展机制默认 USER_TOOLS_DIR = ~/.config/FreeCAD/FreeCADAI/tools/
# 容器里设 HOME=/root，启动时 entrypoint 把我们的工具链接进去
ENV HOME=/root

WORKDIR /data
VOLUME ["/data"]

EXPOSE 3000

COPY entrypoint.sh /entrypoint.sh
COPY install_oda.sh /opt/install_oda.sh
RUN chmod +x /entrypoint.sh /opt/install_oda.sh

ENTRYPOINT ["/entrypoint.sh"]
