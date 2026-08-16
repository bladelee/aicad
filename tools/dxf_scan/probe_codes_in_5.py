"""在 5-节点里查所有编号路径上的 TEXT/MTEXT/INSERT，看跨图编号到底存在哪。"""
import ezdxf

P = "/data/workdir/19-102/dxf/5-19-102节点.dxf"
CODES = ["DE-02", "DE-03", "DE-08", "1EA-08", "1EA-09", "FU-03",
         "DE-W02", "DE-W03", "DE-W04", "DE-W05", "FU-02", "FU-04"]
print(f"=== 在 5-节点 ({P.split('/')[-1]}) 里搜 {len(CODES)} 个编号 ===\n")

doc = ezdxf.readfile(P)
hits = 0
for layout in doc.layouts:
    for ent in layout:
        etype = ent.dxftype()
        if etype == "TEXT":
            txt = ent.dxf.text or ""
            for c in CODES:
                if c in txt:
                    print(f"  TEXT layout={layout.name} layer={ent.dxf.layer} text={txt[:50]!r}")
                    hits += 1
                    break
        elif etype == "MTEXT":
            try:
                txt = ent.text or ""
            except:
                txt = ""
            for c in CODES:
                if c in txt:
                    print(f"  MTEXT layout={layout.name} layer={ent.dxf.layer} text={txt[:50]!r}")
                    hits += 1
                    break
        elif etype == "INSERT":
            try:
                for a in ent.attribs:
                    v = a.dxf.text or ""
                    for c in CODES:
                        if c in v:
                            print(f"  INSERT[{ent.dxf.name}] layout={layout.name} attrib={a.dxf.tag}={v[:30]!r}")
                            hits += 1
                            break
            except:
                pass
print(f"\n总命中: {hits}")

# 再扫标题栏 / 图框区，常见节点编号在标题栏里
print("\n=== 扫 5-节点 标题栏常见图层 ===")
TITLE_LAYERS = ["A图框", "0", "标题栏", "LAYOUT"]
found_in_title = 0
for layout in doc.layouts:
    for ent in layout:
        if ent.dxf.layer not in TITLE_LAYERS:
            continue
        if ent.dxftype() == "TEXT":
            txt = ent.dxf.text or ""
            # 看含 DE / EA / FU 的
            for c in CODES:
                if c in txt:
                    print(f"  标题栏 TEXT layout={layout.name} layer={ent.dxf.layer} text={txt[:60]!r}")
                    found_in_title += 1
                    break
print(f"标题栏命中: {found_in_title}")
