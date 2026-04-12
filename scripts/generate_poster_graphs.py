#!/usr/bin/env python3
"""
DocuMind.ai — Generate two poster-ready result figures (matplotlib only).

Outputs high-resolution PNGs for a narrow vertical slot on an academic poster.
Run: python scripts/generate_poster_graphs.py
"""

from __future__ import annotations

import os

import matplotlib as mpl
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Poster theme: dark navy, teal, white (matches DocuMind.ai poster aesthetic)
# ---------------------------------------------------------------------------
NAVY = "#0F172A"
NAVY_LIGHT = "#1E293B"
TEAL = "#14B8A6"
WHITE = "#F8FAFC"
MUTED = "#94A3B8"
GRID = "#334155"
BASELINE_BAR = "#475569"  # slate for baselines
DOCUMIND_BAR = "#2DD4BF"  # brighter teal for DocuMind.ai
LATENCY_BASE = "#64748B"
LATENCY_CRITIC = "#F59E0B"  # amber — emphasizes cost of retries

# Figure size (inches): narrow portrait for right column of poster
FIG_W, FIG_H = 3.6, 4.8
DPI = 400  # sharp for Canva / print

OUT_DIR = os.path.join(os.path.dirname(__file__), "poster_output")


def _apply_dark_style(ax: plt.Axes) -> None:
    """Shared axis styling for both figures."""
    ax.set_facecolor(NAVY_LIGHT)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.spines["bottom"].set_color(GRID)
    ax.spines["left"].set_color(GRID)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def graph_quality_comparison(out_dir: str) -> str:
    """Vertical bar chart: Faithfulness across four systems."""
    labels = ["Standard\nRAG", "Hybrid\nRAG", "Self-\nRAG", "DocuMind.ai"]
    values = [0.77, 0.82, 0.85, 0.91]
    colors = [BASELINE_BAR, BASELINE_BAR, BASELINE_BAR, DOCUMIND_BAR]

    fig = plt.figure(figsize=(FIG_W, FIG_H), facecolor=NAVY)
    ax = fig.add_subplot(111)
    _apply_dark_style(ax)

    x = range(len(labels))
    bars = ax.bar(
        x,
        values,
        width=0.62,
        color=colors,
        edgecolor=TEAL,
        linewidth=0.8,
        zorder=3,
    )
    # Subtle highlight on DocuMind.ai bar
    bars[-1].set_edgecolor("#5EEAD4")
    bars[-1].set_linewidth(1.4)

    ax.set_ylim(0.70, 0.95)
    ax.set_yticks([0.70, 0.75, 0.80, 0.85, 0.90, 0.95])
    ax.set_ylabel("Faithfulness", color=WHITE, fontsize=11, fontweight="medium", labelpad=8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=8.5, color=WHITE, fontweight="medium")
    ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color=GRID, alpha=0.7, zorder=0)
    ax.set_axisbelow(True)

    ax.set_title(
        "Quality Comparison",
        color=WHITE,
        fontsize=13,
        fontweight="bold",
        pad=12,
    )

    for rect, v in zip(bars, values):
        ax.text(
            rect.get_x() + rect.get_width() / 2,
            rect.get_height() + 0.008,
            f"{v:.2f}",
            ha="center",
            va="bottom",
            fontsize=10,
            color=WHITE,
            fontweight="semibold",
            zorder=4,
        )

    fig.subplots_adjust(left=0.16, right=0.97, top=0.88, bottom=0.20)
    path = os.path.join(out_dir, "graph_quality_comparison.png")
    fig.savefig(path, dpi=DPI, facecolor=fig.get_facecolor(), edgecolor="none", bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    return path


def graph_latency_tradeoff(out_dir: str) -> str:
    """Vertical bar chart: p95 latency with / without critic retry."""
    labels = ["Without\nCritic Retry", "With\nCritic Retry"]
    values = [4.2, 7.8]

    fig = plt.figure(figsize=(FIG_W, FIG_H), facecolor=NAVY)
    ax = fig.add_subplot(111)
    _apply_dark_style(ax)

    x = [0, 1]
    colors_bars = [LATENCY_BASE, LATENCY_CRITIC]
    bars = ax.bar(
        x,
        values,
        width=0.55,
        color=colors_bars,
        edgecolor=GRID,
        linewidth=0.8,
        zorder=3,
    )

    ax.set_ylim(0, max(values) * 1.35)
    ax.set_ylabel("p95 latency (seconds)", color=WHITE, fontsize=11, fontweight="medium", labelpad=8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9, color=WHITE, fontweight="medium")
    ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color=GRID, alpha=0.7, zorder=0)
    ax.set_axisbelow(True)

    ax.set_title(
        "Latency Tradeoff",
        color=WHITE,
        fontsize=13,
        fontweight="bold",
        pad=12,
    )

    for rect, v in zip(bars, values):
        ax.text(
            rect.get_x() + rect.get_width() / 2,
            rect.get_height() + 0.15,
            f"{v:.1f} s",
            ha="center",
            va="bottom",
            fontsize=10,
            color=WHITE,
            fontweight="semibold",
            zorder=4,
        )

    # Annotation: share of queries that triggered retry (emphasizes when the cost applies)
    ax.annotate(
        "~12% of queries\ntriggered critic retry",
        xy=(1, values[1]),
        xytext=(0.35, max(values) * 1.12),
        fontsize=8.5,
        color=TEAL,
        ha="center",
        va="bottom",
        linespacing=1.2,
        bbox=dict(boxstyle="round,pad=0.35", facecolor=NAVY_LIGHT, edgecolor=TEAL, linewidth=0.8),
        arrowprops=dict(arrowstyle="-|>", color=TEAL, lw=1.0, shrinkA=0, shrinkB=4),
    )

    fig.subplots_adjust(left=0.16, right=0.97, top=0.88, bottom=0.20)
    path = os.path.join(out_dir, "graph_latency_tradeoff.png")
    fig.savefig(path, dpi=DPI, facecolor=fig.get_facecolor(), edgecolor="none", bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    return path


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    # Consistent matplotlib defaults for crisp poster text
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans", "Helvetica", "Arial", "sans-serif"],
            "axes.unicode_minus": False,
        }
    )

    p1 = graph_quality_comparison(OUT_DIR)
    p2 = graph_latency_tradeoff(OUT_DIR)

    print("Generated poster figures:")
    print(f"  {p1}")
    print(f"  {p2}")


if __name__ == "__main__":
    main()
