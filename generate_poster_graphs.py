#!/usr/bin/env python3
"""
Generate two poster-ready PNG figures for DocuMind.ai (matplotlib only).

Outputs high-resolution vertical rectangles (3.6 x 4.8 inches) suitable for
narrow slots on an academic conference poster. Theme: navy, teal, white.

Usage:
    python generate_poster_graphs.py

Requires: matplotlib
"""

from __future__ import annotations

import os

import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Poster theme (dark navy, teal, white — readable on white figure background)
# ---------------------------------------------------------------------------
NAVY = "#0f172a"          # slate-900 — titles, labels, baseline bars
NAVY_MUTED = "#334155"    # slate-700 — secondary text
TEAL = "#0d9488"          # teal-600 — DocuMind.ai accent
GRID = "#e2e8f0"          # slate-200 — subtle grid
BAR_BASELINE = "#64748b"  # slate-500 — baseline systems
BAR_CRITIC_LOW = "#14b8a6"  # teal-500 — without retry (lower latency)
BAR_CRITIC_HIGH = "#c2410c"  # orange-700 — with retry (emphasize cost)

# Figure size (inches) — vertical portrait for narrow poster column (fixed for layout tools)
FIG_W = 3.6
FIG_H = 4.8
DPI = 400  # print-friendly for Canva / large-format posters


def save_poster_png(fig: plt.Figure, path: str) -> None:
    """Save PNG at exactly FIG_W × FIG_H inches (no tight crop — keeps poster slot size)."""
    fig.set_size_inches(FIG_W, FIG_H)
    fig.savefig(
        path,
        dpi=DPI,
        facecolor="#ffffff",
        edgecolor="none",
        bbox_inches=None,
        pad_inches=0,
    )


def ensure_output_dir(path: str) -> None:
    """Create output directory if it does not exist."""
    os.makedirs(path, exist_ok=True)


def style_axes_poster(ax, ylabel: str) -> None:
    """Apply consistent spine, tick, and grid styling."""
    ax.set_facecolor("#ffffff")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(NAVY_MUTED)
    ax.spines["bottom"].set_color(NAVY_MUTED)
    ax.tick_params(colors=NAVY_MUTED, labelsize=9)
    ax.set_ylabel(ylabel, fontsize=10, fontweight="600", color=NAVY, labelpad=6)
    ax.yaxis.grid(True, linestyle="-", linewidth=0.6, color=GRID, zorder=0)
    ax.set_axisbelow(True)


def graph_quality_comparison(out_dir: str) -> str:
    """
    Graph 1: Faithfulness comparison (vertical bar chart).
    DocuMind.ai highlighted in teal; baselines in muted slate.
    """
    systems = ["Standard\nRAG", "Hybrid\nRAG", "Self-\nRAG", "DocuMind.ai"]
    values = [0.77, 0.82, 0.85, 0.91]
    colors = [BAR_BASELINE, BAR_BASELINE, BAR_BASELINE, TEAL]

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.patch.set_facecolor("#ffffff")

    x = range(len(systems))
    bars = ax.bar(
        x,
        values,
        color=colors,
        width=0.62,
        edgecolor="white",
        linewidth=1.0,
        zorder=2,
    )
    # Subtle edge on DocuMind bar for emphasis
    bars[3].set_edgecolor(TEAL)
    bars[3].set_linewidth(1.4)

    ax.set_xticks(list(x))
    ax.set_xticklabels(systems, fontsize=8.5, color=NAVY, fontweight="500")
    ax.set_ylim(0.70, 0.95)
    ax.set_yticks([0.70, 0.75, 0.80, 0.85, 0.90, 0.95])

    style_axes_poster(ax, "Faithfulness")

    ax.set_title(
        "Quality Comparison",
        fontsize=12,
        fontweight="bold",
        color=NAVY,
        pad=10,
    )

    # Exact values above bars
    for bar, val in zip(bars, values):
        height = bar.get_height()
        ax.annotate(
            f"{val:.2f}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="600",
            color=NAVY,
        )

    fig.tight_layout(pad=0.35)
    out_path = os.path.join(out_dir, "graph_quality_comparison.png")
    save_poster_png(fig, out_path)
    plt.close(fig)
    return out_path


def graph_latency_tradeoff(out_dir: str) -> str:
    """
    Graph 2: p95 latency — horizontal bars with explicit margins so title,
    labels, and footer are not clipped on a fixed 3.6 x 4.8 inch canvas.
    """
    p95_without = 4.2
    p95_with = 7.8
    delta_s = p95_with - p95_without
    pct_slower = 100.0 * delta_s / p95_without

    # Two-line y labels fit the narrow width without crowding the left edge
    labels = ["Without\ncritic retry", "With\ncritic retry"]
    y_idx = [1.0, 0.0]
    values = [p95_without, p95_with]
    colors_bar = [BAR_CRITIC_LOW, BAR_CRITIC_HIGH]

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.patch.set_facecolor("#ffffff")

    bars = ax.barh(
        y_idx,
        values,
        height=0.34,
        color=colors_bar,
        edgecolor="white",
        linewidth=1.0,
        zorder=2,
    )

    # Round axis to 0–10 s so ticks align with the grid
    ax.set_xlim(0, 10)
    ax.set_xticks([0, 2, 4, 6, 8, 10])
    ax.set_ylim(-0.42, 1.42)
    ax.set_yticks(y_idx)
    ax.set_yticklabels(labels, fontsize=8.5, color=NAVY, fontweight="600", linespacing=0.95)
    ax.set_xlabel("p95 latency (seconds)", fontsize=9.5, fontweight="600", color=NAVY, labelpad=5)

    ax.xaxis.grid(True, linestyle="-", linewidth=0.6, color=GRID, zorder=0)
    ax.yaxis.grid(False)
    ax.set_facecolor("#ffffff")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(NAVY_MUTED)
    ax.spines["bottom"].set_color(NAVY_MUTED)
    ax.tick_params(axis="x", colors=NAVY_MUTED, labelsize=8.5)
    ax.tick_params(axis="y", colors=NAVY, labelsize=8.5, pad=6)

    # Fixed margins first (avoids tight_layout cropping title/footer)
    fig.subplots_adjust(left=0.30, right=0.96, top=0.79, bottom=0.28)

    # Title and footer in figure coordinates (inside reserved bands)
    fig.text(
        0.5,
        0.965,
        "Latency tradeoff (critic retry)",
        ha="center",
        va="top",
        fontsize=10,
        fontweight="bold",
        color=NAVY,
    )
    fig.text(
        0.5,
        0.135,
        "~12% of queries trigger critic retry\n(additional retrieval + verification)",
        ha="center",
        va="center",
        fontsize=7.2,
        color=NAVY_MUTED,
        linespacing=1.12,
    )

    # Values at bar ends (data coords, inside axes)
    for bar, sec in zip(bars, values):
        w = bar.get_width()
        y = bar.get_y() + bar.get_height() / 2
        ax.annotate(
            f"{sec:.1f} s",
            xy=(w, y),
            xytext=(4, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=8.5,
            fontweight="700",
            color=NAVY,
            clip_on=False,
        )

    # Delta: bracket between bar tips + label in gap (data coordinates)
    y_mid = 0.5
    ax.annotate(
        "",
        xy=(p95_with, y_mid),
        xytext=(p95_without, y_mid),
        arrowprops=dict(
            arrowstyle="<->",
            color=NAVY,
            lw=1.25,
            shrinkA=0,
            shrinkB=0,
        ),
        zorder=3,
    )
    ax.text(
        (p95_without + p95_with) / 2,
        y_mid + 0.12,
        f"+{delta_s:.1f} s  (+{pct_slower:.0f}%)",
        ha="center",
        va="bottom",
        fontsize=8,
        fontweight="700",
        color=NAVY,
    )

    out_path = os.path.join(out_dir, "graph_latency_tradeoff.png")
    save_poster_png(fig, out_path)
    plt.close(fig)
    return out_path


def main() -> None:
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "poster_graphs_output")
    ensure_output_dir(out_dir)

    p1 = graph_quality_comparison(out_dir)
    p2 = graph_latency_tradeoff(out_dir)

    print("Generated poster figures:")
    print(f"  {p1}")
    print(f"  {p2}")


if __name__ == "__main__":
    main()
