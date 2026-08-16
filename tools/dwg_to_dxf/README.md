# tools/dwg_to_dxf

## 它是什么

用 LibreDWG 把 `.dwg` 文件批量转成 `.dxf`，方便后续 ezdxf 读入。

主理由：开源 ezdxf 不能直接读 DWG，必须先转 DXF。LibreDWG 是 GNU 项目，完全开源免 EULA。

## 包含

- `Dockerfile.libredwg` —— 编译 libredwg 源码进 docker 镜像
- `convert_dwg.sh` —— 批量转换入口脚本

## 用法

### 1. 构建镜像（首次，~5 分钟）

```bash
cd /Users/bladelee/project/cad
docker build -f tools/dwg_to_dxf/Dockerfile.libredwg \
             -t libredwg-cli \
             tools/dwg_to_dxf/
```

### 2. 批量转换所有 DWG → DXF

```bash
bash tools/dwg_to_dxf/convert_dwg.sh samples/19-102 workdir/19-102/dxf
```

转完后 `workdir/19-102/dxf/` 下有同名 `.dxf` 文件。

### 3. 单文件转换

```bash
docker run --rm -v "$PWD:/data" libredwg-cli \
    -y -o /data/workdir/19-102/dxf/某图.dxf \
    /data/samples/19-102/某图.dwg
```

## DWG 支持的版本

libredwg 编译时启用 `--enable-write`，对以下版本支持：

| ACAD magic | DWG 版本 | 状态 |
|------------|---------|------|
| AC1015 | R2000-R2002 | ✅ 完整 |
| AC1018 | R2004-R2006 | ✅ 完整 |
| AC1021 | R2007-R2009 | ✅ 完整 |
| AC1024 | R2010-R2012 | ✅ 完整 |
| AC1027 | R2013-R2014 | ✅ 基本完整 |
| AC1032 | R2018+ | ⚠️ 可能丢字段（MATERIAL、DIMASSOC 等高级类）|

实测 6 张 19-102 别墅 DWG (含 3 张 R2018+) 全部转换成功。粗略警告：
- `MATERIAL` 对象 → 不影响实体结构，只丢材质元数据
- `DIMASSOC` 标注关联 → 可能影响标注自动更新
- `BLOCKREPRESENTATION_DATA` → 块外观参数，不影响几何

详见 `docs/格式转换-实战记录.md`、`docs/DXF扫描报告.md`。
