#!/usr/bin/env python3
"""Validate the structure and common guardrails of a final travel Markdown file."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


REQUIRED_HEADINGS = (
    "全部景点 Checklist",
    "固定交通与住宿",
    "超过 1 小时停留复核",
    "每日安排",
    "餐厅安排",
    "预约清单",
    "临行复核",
    "官方链接",
)

FORBIDDEN_FINAL_HEADINGS = (
    "不加入",
    "没有加入",
    "未采用",
    "淘汰方案",
    "酒店 Options",
    "小红书景点候选",
    "小红书餐厅候选",
)

TRANSPORT_WORDS = (
    "步行",
    "地铁",
    "公交",
    "火车",
    "高铁",
    "轻轨",
    "游船",
    "轮渡",
    "飞机",
    "自驾",
    "Walk",
    "Underground",
    "Metro",
    "Bus",
    "Train",
    "Ferry",
    "Flight",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--bilingual", action="store_true")
    parser.add_argument("--no-taxi", action="store_true")
    args = parser.parse_args()

    if not args.path.is_file():
        print(f"ERROR: file not found: {args.path}")
        return 2

    text = args.path.read_text(encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []

    if len(text.strip()) < 500:
        errors.append("文件内容过短，不像完整最终行程。")

    for heading in REQUIRED_HEADINGS:
        if not re.search(rf"^##\s+.*{re.escape(heading)}", text, re.MULTILINE):
            errors.append(f"缺少必需章节：{heading}")

    for heading in FORBIDDEN_FINAL_HEADINGS:
        if re.search(rf"^##+\s+.*{re.escape(heading)}", text, re.MULTILINE):
            errors.append(f"最终稿不应包含研究或落选章节：{heading}")

    if args.no_taxi and re.search(r"打车|出租车|\bTaxi\b|\bUber\b(?!\s*Boat)", text, re.I):
        errors.append("发现打车相关安排，但启用了 --no-taxi。")

    checklist_match = re.search(
        r"^##\s+.*全部景点 Checklist.*?\n(.*?)(?=^##\s|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    checklist_text = checklist_match.group(1) if checklist_match else ""
    checklist_lines = [
        line
        for line in checklist_text.splitlines()
        if re.match(r"^- \[[ xX]\] ", line)
    ]
    if not checklist_lines:
        errors.append("没有找到 Markdown checklist。")

    if args.bilingual:
        unpaired = [
            line for line in checklist_lines if "｜" not in line and "|" not in line
        ]
        if unpaired:
            errors.append(
                f"双语模式下有 {len(unpaired)} 个 checklist 项缺少中英文分隔符。"
            )

    day_sections = re.split(r"^###\s+", text, flags=re.MULTILINE)[1:]
    itinerary_days = [section for section in day_sections if re.search(r"\d{1,2}[/-]\d{1,2}|Day\s*\d+", section)]
    if not itinerary_days:
        errors.append("未找到逐日行程三级标题。")
    for section in itinerary_days:
        title = section.splitlines()[0].strip()
        bullets = [line for line in section.splitlines() if line.startswith("- ")]
        if len(bullets) >= 3 and not any(word in section for word in TRANSPORT_WORDS):
            warnings.append(f"{title} 有多个行程节点，但没有发现交通方式。")

    if "http://" not in text and "https://" not in text:
        warnings.append("官方链接章节中没有发现 URL。")

    for message in errors:
        print(f"ERROR: {message}")
    for message in warnings:
        print(f"WARNING: {message}")

    if errors:
        print(f"FAIL: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"PASS: 0 errors, {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
