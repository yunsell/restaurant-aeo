"""리포트용 matplotlib 차트 (PNG)."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.report.aggregate import Summary  # noqa: E402


def channel_mention_chart(summary: Summary, out_path: Path) -> Path:
    """채널별 언급률 막대 차트."""
    channels = list(summary.by_channel)
    rates = [
        summary.by_channel[c]["mentioned"] / summary.by_channel[c]["total"] * 100
        if summary.by_channel[c]["total"]
        else 0
        for c in channels
    ]
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(channels, rates, color="#4C72B0")
    ax.set_ylabel("mention rate (%)")
    ax.set_title(f"Mention rate by channel ({summary.date})")
    ax.set_ylim(0, 100)
    ax.bar_label(bars, fmt="%.0f%%")
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def trend_chart(summaries: list[Summary], out_path: Path) -> Path:
    """날짜별 총 언급 횟수 추이 라인 차트."""
    dates = [s.date for s in summaries]
    counts = [s.mentioned for s in summaries]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(dates, counts, marker="o", color="#DD8452")
    ax.set_ylabel("mentions")
    ax.set_title("Mentions over time")
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path
