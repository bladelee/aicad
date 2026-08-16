"""
align_vision_to_dxf — 方案 H 场景 A 的 VLM 跨模态对齐骨架

本工具把以下 3 类资产对齐：
    1. DXF 结构化 JSON（含 DIMENSION 实测值）
    2. 设计师原 PDF 单页（按页选）
    3. VLM 输出 alignment 报告

支持 3 种 VLM 调用模式（按部署场景选）：

| 模式 | 工作方式 | 适用场景 | 需要 |
|------|---------|---------|------|
| stub  | 不调模型，返回固定示例结构 | 调试、CI 测试 | 无 |
| inline | 把 prompt + 图片**送给当前 M3 对话**（即"模型即我"）| 端到端验证、无 API key | 已经在 M3 对话里 |
| http  | 真 HTTP POST 到外部 API endpoint | 生产/批处理 | API base URL + key |

★ 关键概念：
- stub 是**纯离线**（没任何模型）
- inline 是**当前对话里调用**（这是你这个会话里的 M3 直接看图，不是真的"离线"）
- http 才是**远程真 API 调用**

inline 模式的设计原因：本项目当前会话模型就是 M3，inline 模式让对齐脚本能把图 + prompt
直接送给当前 M3（即"我把 prompt+图作为这次 chat 的输入"），无需 API key 闭环。
在 M3 Code / Agent / Chat 等环境里，inline 模式就是生产路径——M3 直接看图给答案。

输出 alignment 报告结构：
    {
        "summary": {...},            # 总览
        "vlm_input_prompt": "...",   # 给 VLM 的 prompt（含 DXF 摘要）
        "vlm_output": {              # VLM 返回的结构化对齐结果
            "room_labels": [...],
            "furniture_labels": [...],
            "dimension_check": {...},
            "warnings": [...],
            "style_assessment": {...},
            "alignment_status": "ok|partial|failed"
        }
    }

用法：
    # stub 调试（不调模型）
    python tools/visual/align_vision_to_dxf.py \\
        --dxf_json tmp_vision/phase_h0/dimensions_plan.json \\
        --pdf_png tmp_vision/phase_h0/pdf_plan/p00.png \\
        --out tmp_vision/phase_h0/alignment_p00.json --mode stub

    # inline（在 M3 对话里直接看图给答案）
    python tools/visual/align_vision_to_dxf.py \\
        --dxf_json ... --pdf_png ... --out ... --mode inline \\
        --inline-json m3_answers.json     # M3 已经看图后写的答案 JSON

    # http（真 API 调用）
    python tools/visual/align_vision_to_dxf.py \\
        --dxf_json ... --pdf_png ... --out ... --mode http \\
        --api-base https://api.minimax.chat/v1 --api-key $MINIMAX_API_KEY

设计依据：方案-H §1.1 场景 A + §3 Phase H-0 交付清单
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from typing import Any


def call_vlm(prompt: str, image_path: str) -> dict:
    """
    STUB: 调用多模态 LLM 给出对齐结果。
    实现方需要自己接入 Goose/OpenWork/M3 API 等。

    返回结构示例：
        {
            "room_labels": [...],
            "furniture_labels": [...],
            "dimension_check": {...},
            "warnings": [...]
        }
    """
def call_vlm_stub(prompt: str, image_path: str) -> dict:
    """纯 stub：返回固定结构（不调任何模型）"""
    return {
        "room_labels": [
            {"name": "(stub) 会客区", "bbox_approx": [0, 0, 0, 0],
             "matched_dxf_layers": ["A原建筑墙体"]},
        ],
        "furniture_labels": [],
        "dimension_check": {"note": "stub, 未实际调 VLM"},
        "warnings": ["本报告为 stub 模式"],
        "_stub": True,
    }


def call_vlm_inline(prompt: str, image_path: str, inline_json_path: str | None = None) -> dict:
    """inline 模式：从 JSON 文件读 VLM 答案（用于"当前 M3 自己看图后给答案"的离线场景）。

    用法:
        1. M3 在另一会话里看图, 把答案写到 inline_json_path (JSON 格式)
        2. 本函数读那个 JSON 作为 VLM 输出
        3. 这样不需要 API key 也能跑端到端 pipeline
    """
    if inline_json_path is None:
        raise ValueError("inline 模式必须指定 inline_json_path（指向 M3 已经给的答案 JSON）")
    import json
    with open(inline_json_path, encoding="utf-8") as f:
        return json.load(f)


def _http_env() -> tuple[str | None, str | None, str]:
    """从环境变量读 HTTP 模式配置。"""
    api_base = os.environ.get("MINIMAX_API_BASE", "https://api.minimax.chat/v1")
    api_key = os.environ.get("MINIMAX_API_KEY") or os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("MINIMAX_MODEL", "MiniMax-M3")
    return api_base, api_key, model


def call_vlm_http(prompt: str, image_path: str,
                  api_base: str | None = None,
                  api_key: str | None = None,
                  model: str | None = None) -> dict:
    """真 HTTP 调用多模态模型（OpenAI 兼容 chat completions 格式）。

    若不显式传 api_base/api_key/model，从环境变量读：
        MINIMAX_API_BASE (默认 https://api.minimax.chat/v1)
        MINIMAX_API_KEY  或  OPENAI_API_KEY
        MINIMAX_MODEL    (默认 MiniMax-M3)

    支持 endpoint（任选其一设置 api_base）：
        - MiniMax M3:    https://api.minimax.chat/v1
        - OpenAI:        https://api.openai.com/v1
        - 任何 OpenAI 兼容 chat completion 端点
    """
    if api_base is None or api_key is None or model is None:
        env_base, env_key, env_model = _http_env()
        api_base = api_base or env_base
        api_key = api_key or env_key
        model = model or env_model
    if not api_key:
        raise ValueError(
            "http 模式需要 API key。请通过 --api-key 传或设置 MINIMAX_API_KEY 环境变量。"
        )

    import base64
    import json
    import requests

    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("ascii")

    # 缩图策略：若图 > 1MB，临时压缩到 ≤1MB 再传
    img_path_for_api = image_path
    tmp_compressed = None
    try:
        sz = os.path.getsize(image_path)
        if sz > 1_000_000:
            try:
                from PIL import Image
                img = Image.open(image_path).convert("RGB")
                # 缩到 ≤1024 px 长边
                img.thumbnail((1024, 1024))
                tmp_compressed = image_path + ".compressed.jpg"
                img.save(tmp_compressed, "JPEG", quality=80, optimize=True)
                img_path_for_api = tmp_compressed
                with open(img_path_for_api, "rb") as f2:
                    img_b64 = base64.b64encode(f2.read()).decode("ascii")
                print(f"  [compressed {sz//1024}KB → {os.path.getsize(img_path_for_api)//1024}KB]")
            except ImportError:
                pass  # 没 PIL 就硬传

    except Exception:
        pass

    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
            ],
        }],
        "temperature": 0.1,
        "max_tokens": 4096,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    resp = requests.post(
        f"{api_base.rstrip('/')}/chat/completions",
        json=payload, headers=headers, timeout=60,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]

    # 清理可能的 markdown 包裹
    content = content.strip()
    if content.startswith("```"):
        content = "\n".join(content.split("\n")[1:])  # 去首行
    if content.endswith("```"):
        content = "\n".join(content.split("\n")[:-1])  # 去末行

    if tmp_compressed:
        try:
            os.remove(tmp_compressed)
        except OSError:
            pass

    return json.loads(content)


def call_vlm(prompt: str, image_path: str,
             mode: str = "stub",
             inline_json_path: str | None = None,
             api_base: str | None = None,
             api_key: str | None = None,
             model: str | None = None) -> dict:
    """VLM 调度入口：按 mode 分发到 stub/inline/http 实现。

    mode 含义（重要！别混淆）：
        - stub: 纯离线（无任何模型），返回固定结构（仅用于调试/CI）
        - inline: 把 prompt+图送给**当前对话里的 M3**（即模型"自己"），从预先写好的
                  JSON 文件读 VLM 答案。这是"在当前 M3 会话里端到端验证" 的桥梁，
                  不需要 API key，因为模型就是当前对话本身。
        - http: 真 HTTP POST 到外部 API endpoint。需要 api_base + api_key。

    参数：
        inline_json_path: inline 模式下必填。M3 在某次对话里看图后写出的答案 JSON。
        api_base, api_key: http 模式可省略（从 MINIMAX_API_BASE / MINIMAX_API_KEY
                       或 OPENAI_API_KEY 环境变量读）。
        model: http 模式下的模型名（默认 MiniMax-M3）。
    """
    if mode == "stub":
        return call_vlm_stub(prompt, image_path)
    if mode == "inline":
        return call_vlm_inline(prompt, image_path, inline_json_path)
    if mode == "http":
        # 让 call_vlm_http 自己去读环境变量，避免 CLI 没传参数时报错的假象
        return call_vlm_http(prompt, image_path,
                             api_base=api_base, api_key=api_key,
                             model=model or "MiniMax-M3")
    raise ValueError(f"unknown mode: {mode}")


def build_alignment_prompt(dxf_json: dict, pdf_basename: str) -> str:
    """构造给 VLM 的 prompt（中文，因为目标项目是中文装修图）"""
    summary = dxf_json.get("summary", {})
    by_layer = summary.get("by_layer", {})
    stats = summary.get("by_layer_value_stats", {})

    # 提取关键尺寸数字供 VLM 校验
    key_dimensions = []
    for layer, s in stats.items():
        if "原建筑" in layer or "隔墙" in layer:
            key_dimensions.append({
                "layer": layer,
                "count": s["n"],
                "max_mm": s["max"],
                "avg_mm": round(s["avg"], 0),
            })

    return f"""你是 CAD 工程师。请对比【DXF 解析出的尺寸数据】与【PDF 图像】，给出对齐报告。

【DXF 解析摘要】（来自 {summary.get('file', '?')}）:
- DIMENSION 总数: {summary.get('total_dimensions', '?')}
- 按图层分类: {json.dumps(by_layer, ensure_ascii=False)}
- 关键尺寸（墙体/隔墙）: {json.dumps(key_dimensions, ensure_ascii=False)}

【PDF 图像】（{pdf_basename}）：请仔细查看上图。

请回答以下问题并以 JSON 格式输出：

1. room_labels: PDF 上你能读出的房间名（如 "会客区"、"中厨"、"卫生间"），每个标注近似位置（图像坐标像素）。
2. furniture_labels: PDF 上你能识别的家具/物品（钢琴/沙发/餐桌/钢琴品牌如 BECHSTEIN 等），每个标注近似位置。
3. dimension_check: PDF 上看到的尺寸数字（如 4900/4500/9400/6200 等），与 DXF 提供的最大/平均尺寸是否合理对得上？差异在哪？
4. warnings: PDF 上看到但 DXF 数据里**没有对应信息**的事项（如 PDF 有"钢琴"但 DXF 没有此家具类型字段）。
5. alignment_status: "ok" / "partial" / "failed"

输出严格的 JSON，不要 markdown 代码块包裹。
"""


def align(dxf_json_path: str, pdf_png_path: str,
          mode: str = "stub",
          inline_json_path: str | None = None,
          api_base: str | None = None,
          api_key: str | None = None,
          model: str | None = None) -> dict:
    """主函数：执行 VLM 跨模态对齐"""
    with open(dxf_json_path, encoding="utf-8") as f:
        dxf_data = json.load(f)
    pdf_basename = os.path.basename(pdf_png_path)
    prompt = build_alignment_prompt(dxf_data, pdf_basename)

    vlm_output = call_vlm(
        prompt, pdf_png_path,
        mode=mode,
        inline_json_path=inline_json_path,
        api_base=api_base, api_key=api_key, model=model,
    )

    return {
        "summary": {
            "dxf_file": dxf_data.get("summary", {}).get("file"),
            "dxf_total_dimensions": dxf_data.get("summary", {}).get("total_dimensions"),
            "pdf_page": pdf_basename,
            "alignment_status": vlm_output.get("alignment_status",
                                               "ok" if not vlm_output.get("_stub") else "stub"),
            "vlm_mode": mode,
        },
        "vlm_input_prompt": prompt,
        "vlm_output": vlm_output,
    }


def _cli() -> int:
    p = argparse.ArgumentParser(description="VLM 跨模态对齐骨架")
    p.add_argument("--dxf_json", required=True, help="DIMENSION JSON 路径")
    p.add_argument("--pdf_png", required=True, help="PDF 单页 PNG 路径")
    p.add_argument("--out", required=True)
    p.add_argument("--mode", choices=["stub", "inline", "http"], default="stub")
    p.add_argument("--inline-json", help="inline 模式：M3 已给的答案 JSON 路径")
    p.add_argument("--api-base", help="http 模式：API base URL")
    p.add_argument("--api-key", help="http 模式：API key")
    p.add_argument("--model", default="MiniMax-M3", help="http 模式：模型名")
    args = p.parse_args()

    report = align(
        args.dxf_json, args.pdf_png,
        mode=args.mode,
        inline_json_path=args.inline_json,
        api_base=args.api_base, api_key=args.api_key, model=args.model,
    )
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"✅ alignment report: {args.out}")
    print(f"   status: {report['summary']['alignment_status']}, mode: {args.mode}")
    if report["vlm_output"].get("_stub"):
        print("   (stub 模式)")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
