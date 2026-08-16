"""一次性脚本：在 ubuntu 22.04 容器里从源码编译 libredwg 并试转 5 张 dwg。
本身是给宿主机的 docker run 用的，不在 workspace 里跑。"""
static_notice = """
宿主机用：
docker run --rm \\
    -v "$PWD/dwg:/data" \\
    -v "$PWD/dwg/test_libredwg.sh:/test.sh:ro" \\
    --entrypoint=/bin/bash \\
    ubuntu:22.04 \\
    -lc "bash /test.sh"
"""
print(static_notice)  # 仅当误执行时提示
import sys; sys.exit(0)
