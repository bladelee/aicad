"""一次探查：天正 (TArch/TWT) 在 DXF 里留下哪些 XData / 自定义对象痕迹。

宿主机用：
    docker run --rm -v "$PWD:/data" \
        -e PYTHONHOME=/opt/FreeCAD/usr \
        -e LD_LIBRARY_PATH=/opt/FreeCAD/usr/lib \
        -e SSL_CERT_FILE=/opt/FreeCAD/usr/ssl/cacert.pem \
        --entrypoint=/bin/bash \
        floorplan-mcp:latest \
        -lc "/opt/FreeCAD/usr/bin/python /data/tools/dxf_scan/probe_xdata.py"
"""
from __future__ import annotations
import sys
from collections import Counter, defaultdict
from pathlib import Path

import ezdxf


def main():
    in_dir = Path("/data/workdir/19-102/dxf")
    dxfs = sorted(in_dir.glob("*.dxf"))
    print(f"=== 探查 {len(dxfs)} 张 DXF 的天正痕迹 ===\n")

    summary = {}

    for dxf_path in dxfs:
        name = dxf_path.stem
        print(f"--- {name} ---")
        try:
            doc = ezdxf.readfile(str(dxf_path))
        except Exception as e:
            print(f"  ✗ 读失败: {e}")
            continue

        msp = doc.modelspace()

        # 1. 找 APPID（XData 注册名）
        appids = [a.dxf.name for a in doc.appids]
        # 业务相关 APPID：天正的 TCH/TWT/TARCH 系列 + 自定义 SYS/HUSD
        TCH_KEYS = ("TCH", "TWT", "TARCH", "TWG", "HUSD", "SYS")
        tarch_appids = [a for a in appids
                        if any(k in a.upper() for k in TCH_KEYS)]
        print(f"  图层: {len(list(doc.layers))}, APPID: {len(appids)} 个")
        print(f"  业务相关 APPID: {tarch_appids[:10]}")
        if len(tarch_appids) > 10:
            print(f"    ... 共 {len(tarch_appids)} 个业务 APPID")

        # 2. 统计 model space 实体类型 + 找 PROXY 实体
        type_count = Counter()
        proxy_count = 0
        xdata_apps_seen = Counter()
        proxy_proxy_byte_total = 0

        for ent in msp:
            type_count[ent.dxftype()] += 1

            # PROXY_ENTITY（天正对象的代理形式）
            if ent.dxftype() in ("ACAD_PROXY_ENTITY", "PROXY_ENTITY"):
                proxy_count += 1

            # 统计所有 XData APPID
            try:
                xdata = ent.xdata
                if xdata:
                    for xd in xdata:
                        xdata_apps_seen[xd.appid] += 1
            except Exception:
                pass

        print(f"  Top 实体类型: {type_count.most_common(8)}")
        print(f"  PROXY 实体数: {proxy_count}")
        print(f"  XData APPID 命中 top10: {xdata_apps_seen.most_common(10)}")

        # 3. 深入：找 1 个 PROXY + 1 个 LINE，看真实数据
        sample_proxy = None
        sample_line = None
        for ent in msp:
            if ent.dxftype() in ("ACAD_PROXY_ENTITY", "PROXY_ENTITY") and not sample_proxy:
                sample_proxy = ent
            if ent.dxftype() == "LINE" and not sample_line:
                sample_line = ent
            if sample_proxy and sample_line:
                break

        if sample_proxy:
            print(f"  --- 1 个 PROXY 样本（dxf name = {sample_proxy.dxf.name}）---")
            print(f"    layer: {sample_proxy.dxf.layer}")
            attrs = [a for a in dir(sample_proxy.dxf) if not a.startswith("_")][:15]
            print(f"    dxf attrs: {attrs}")
            try:
                props = sample_proxy.proxy_graphic
                print(f"    proxy_graphic (bytes): {len(props) if props else 0}")
            except Exception:
                pass
            try:
                xd_list = sample_proxy.xdata
                if xd_list:
                    for xd in xd_list[:3]:
                        # xd 是 XData 对象，但具体表现因版本不同
                        # 这里只是大致看下
                        print(f"    XData appid={getattr(xd, 'appid', '?')}")
            except Exception as e:
                print(f"    XData 读取失败: {e}")

        if sample_line:
            print(f"  --- 1 个 LINE 样本 ---")
            try:
                print(f"    start: {tuple(sample_line.dxf.start)}, end: {tuple(sample_line.dxf.end)}")
                print(f"    layer: {sample_line.dxf.layer}")
                xd = sample_line.xdata
                if xd:
                    print(f"    带 XData: {[getattr(x, 'appid', '?') for x in xd]}")
            except Exception as e:
                print(f"    读失败: {e}")

        summary[name] = {
            "tarch_appids": tarch_appids,
            "proxy_count": proxy_count,
            "top_types": type_count.most_common(10),
            "xdata_apps": dict(xdata_apps_seen),
        }
        print()

    print("=== 总结 ===")
    for n, s in summary.items():
        print(f"{n}: proxy={s['proxy_count']}, top types={s['top_types'][:3]}")


if __name__ == "__main__":
    main()
