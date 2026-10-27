#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from scipy import stats

PHASES = ("keygen", "sign", "verify")
IMPLS = ("ref", "avx2")
MODES = ("2", "3", "5")
VARIANTS = (("bd", "with_bd"), ("nobd", "without_bd"))
COLOR_NOBD = "#42A5F5"
COLOR_BD = "#BBDEFB"


@dataclass
class Run:
    impl: str
    mode: str
    backdoor: bool
    phase: str
    df: pd.DataFrame


def discover(results_root: Path) -> list[Run]:
    runs: list[Run] = []
    for impl in IMPLS:
        for mode in MODES:
            for variant, folder in VARIANTS:
                base = results_root / impl / f"Dilithium{mode}" / folder
                if not base.is_dir():
                    continue
                for phase in PHASES:
                    csv = base / f"{phase}.csv"
                    if not csv.is_file():
                        continue
                    df = pd.read_csv(csv)
                    df["time_ms"] = df["time_ns"] / 1e6
                    runs.append(Run(impl, mode, variant == "bd", phase, df))
    return runs


def ci95(samples: np.ndarray) -> tuple[float, float]:
    n = len(samples)
    if n < 2:
        return float("nan"), float("nan")
    mean = float(np.mean(samples))
    sem = float(stats.sem(samples))
    if not np.isfinite(sem) or sem == 0.0:
        return mean, mean
    h = sem * stats.t.ppf(0.975, n - 1)
    return mean - h, mean + h


def summarize(runs: list[Run]) -> pd.DataFrame:
    rows = []
    for r in runs:
        n_total = len(r.df)
        ok_df = r.df[r.df["ok"] == 1]
        n_ok = len(ok_df)
        n_fail = n_total - n_ok
        if n_ok == 0:
            continue
        cyc = ok_df["cycles"].to_numpy()
        ms = ok_df["time_ms"].to_numpy()
        rss = ok_df["peak_rss_kb"].to_numpy()
        cyc_lo, cyc_hi = ci95(cyc)
        ms_lo, ms_hi = ci95(ms)
        rows.append({
            "impl": r.impl,
            "mode": int(r.mode),
            "backdoor": r.backdoor,
            "phase": r.phase,
            "n_total": n_total,
            "n_ok": n_ok,
            "n_fail": n_fail,
            "fail_rate": n_fail / n_total if n_total else 0.0,
            "cycles_mean": float(np.mean(cyc)),
            "cycles_median": float(np.median(cyc)),
            "cycles_std": float(np.std(cyc, ddof=1)) if n_ok > 1 else 0.0,
            "cycles_ci95_lo": cyc_lo,
            "cycles_ci95_hi": cyc_hi,
            "time_ms_mean": float(np.mean(ms)),
            "time_ms_median": float(np.median(ms)),
            "time_ms_std": float(np.std(ms, ddof=1)) if n_ok > 1 else 0.0,
            "time_ms_ci95_lo": ms_lo,
            "time_ms_ci95_hi": ms_hi,
            "peak_rss_kb_max": int(np.max(rss)),
            "peak_rss_kb_median": float(np.median(rss)),
        })
    df = pd.DataFrame(rows)
    return df.sort_values(["impl", "mode", "phase", "backdoor"]).reset_index(drop=True)


def boxplot_compare(runs: list[Run], metric: str, ylabel: str, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    by_key: dict[tuple[str, str], list[Run]] = {}
    for r in runs:
        by_key.setdefault((r.impl, r.mode), []).append(r)
    for (impl, mode), group in by_key.items():
        labels: list[str] = []
        data: list[np.ndarray] = []
        for phase in PHASES:
            for bd in (False, True):
                hits = [r for r in group if r.phase == phase and r.backdoor == bd]
                if not hits:
                    continue
                ok = hits[0].df[hits[0].df["ok"] == 1]
                data.append(ok[metric].to_numpy())
                labels.append(f"{phase}\n{'Backdoored' if bd else 'Original'}")
        if not data:
            continue
        fig, ax = plt.subplots(figsize=(9, 5))
        try:
            bp = ax.boxplot(data, tick_labels=labels, showfliers=False, patch_artist=True)
        except TypeError:
            bp = ax.boxplot(data, labels=labels, showfliers=False, patch_artist=True)
        colors = [COLOR_NOBD, COLOR_BD] * (len(data) // 2)
        if len(data) % 2 != 0: colors.append(COLOR_NOBD)
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
        for median in bp['medians']:
            median.set_color("black")

        metric_title = "Time" if metric == "time_ms" else "Cycles"
        ax.set_title(f"{metric_title} Distribution for Dilithium {mode} ({impl.upper()})")
        ax.set_ylabel(ylabel)
        ax.grid(True, axis="y", linestyle=":", alpha=0.5)
        ax.ticklabel_format(style="plain", axis="y")
        fig.tight_layout()
        fig.savefig(out_dir / f"box_{impl}_D{mode}_{metric}.png", dpi=130)
        plt.close(fig)


def bar_with_ci(stats_df: pd.DataFrame, metric: str, lo: str, hi: str,
                ylabel: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if stats_df.empty:
        return
    pivot = stats_df.copy()
    pivot["x"] = (
        pivot["impl"] + "/D" + pivot["mode"].astype(str) + "/" + pivot["phase"]
    )
    xs = sorted(pivot["x"].unique())
    idx = np.arange(len(xs))
    width = 0.4
    fig, ax = plt.subplots(figsize=(max(8, len(xs) * 0.55), 5))
    colors = (COLOR_NOBD, COLOR_BD)
    for offset, bd, color in zip((-width / 2, width / 2), (False, True), colors):
        ys, errs_lo, errs_hi = [], [], []
        for x in xs:
            row = pivot[(pivot["x"] == x) & (pivot["backdoor"] == bd)]
            if row.empty:
                ys.append(np.nan)
                errs_lo.append(0.0)
                errs_hi.append(0.0)
            else:
                m = float(row[metric].iloc[0])
                ys.append(m)
                errs_lo.append(m - float(row[lo].iloc[0]))
                errs_hi.append(float(row[hi].iloc[0]) - m)
        ax.bar(idx + offset, ys, width=width, color=color,
               yerr=[errs_lo, errs_hi], capsize=3, edgecolor="black", linewidth=0.5,
               label=("Backdoored" if bd else "Original"))
    ax.set_xticks(idx)
    ax.set_xticklabels(xs, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel(ylabel)
    metric_title = "Time" if "time" in metric else "Cycles"
    ax.set_title(f"Mean {metric_title} per Phase (with 95% CI)")
    ax.legend()
    ax.grid(True, axis="y", linestyle=":", alpha=0.5)
    ax.ticklabel_format(style="plain", axis="y")
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def fail_rate_chart(stats_df: pd.DataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if stats_df.empty:
        return
    pivot = stats_df.copy()
    pivot["x"] = (
        pivot["impl"] + "/D" + pivot["mode"].astype(str) + "/" + pivot["phase"]
    )
    xs = sorted(pivot["x"].unique())
    idx = np.arange(len(xs))
    width = 0.4
    fig, ax = plt.subplots(figsize=(max(8, len(xs) * 0.55), 5))
    colors = (COLOR_NOBD, COLOR_BD)
    for offset, bd, color in zip((-width / 2, width / 2), (False, True), colors):
        ys = []
        for x in xs:
            row = pivot[(pivot["x"] == x) & (pivot["backdoor"] == bd)]
            ys.append(float(row["fail_rate"].iloc[0]) if not row.empty else np.nan)
        ax.bar(idx + offset, ys, width=width, color=color, edgecolor="black", linewidth=0.5,
               label=("Backdoored" if bd else "Original"))
    ax.set_xticks(idx)
    ax.set_xticklabels(xs, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Failure rate")
    ax.set_title("Failure Rate per Phase (10,000 runs)")
    ax.legend()
    ax.grid(True, axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def bar_total_time(stats_df: pd.DataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if stats_df.empty:
        return

    grouped = stats_df.groupby(["impl", "mode", "backdoor"], as_index=False)[["time_ms_mean", "cycles_mean"]].sum()
    grouped["x"] = grouped["impl"] + "/D" + grouped["mode"].astype(str)

    xs = sorted(grouped["x"].unique())
    idx = np.arange(len(xs))
    width = 0.4

    fig, ax = plt.subplots(figsize=(max(7, len(xs) * 0.8), 5))

    colors = (COLOR_NOBD, COLOR_BD)
    for offset, bd, color in zip((-width / 2, width / 2), (False, True), colors):
        ys = []
        for x in xs:
            row = grouped[(grouped["x"] == x) & (grouped["backdoor"] == bd)]
            ys.append(float(row["time_ms_mean"].iloc[0]) if not row.empty else np.nan)

        ax.bar(idx + offset, ys, width=width, color=color, edgecolor="black", linewidth=0.5, label=("Backdoored" if bd else "Original"))

    ax.set_xticks(idx)
    ax.set_xticklabels(xs, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Total Time (ms)")
    ax.set_title("Mean Cumulative Time of Full Cycle")
    ax.legend()
    ax.grid(True, axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def bar_rss(stats_df: pd.DataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if stats_df.empty:
        return

    pivot = stats_df.copy()
    pivot["x"] = pivot["impl"] + "/D" + pivot["mode"].astype(str) + "/" + pivot["phase"]
    xs = sorted(pivot["x"].unique())
    idx = np.arange(len(xs))
    width = 0.4

    fig, ax = plt.subplots(figsize=(max(8, len(xs) * 0.55), 5))

    colors = (COLOR_NOBD, COLOR_BD)
    for offset, bd, color in zip((-width / 2, width / 2), (False, True), colors):
        ys = []
        for x in xs:
            row = pivot[(pivot["x"] == x) & (pivot["backdoor"] == bd)]
            ys.append(float(row["peak_rss_kb_max"].iloc[0]) if not row.empty else np.nan)
        ax.bar(idx + offset, ys, width=width, color=color, edgecolor="black", linewidth=0.5, label=("Backdoored" if bd else "Original"))

    ax.set_xticks(idx)
    ax.set_xticklabels(xs, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Peak RSS (KB)")
    ax.set_title("Peak Resident Memory per Phase")
    ax.legend()
    ax.grid(True, axis="y", linestyle=":", alpha=0.5)

    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    here = Path(__file__).resolve().parent
    repo_root = here.parent.parent

    parser = argparse.ArgumentParser(
        description="Aggregate Dilithium benchmark CSVs into a stats table and comparison plots"
    )
    parser.add_argument("--results", type=Path,
                        default=repo_root / "benchmarks" / "results",
                        help="Root directory with benchmark CSVs")
    parser.add_argument("--out", type=Path,
                        default=repo_root / "benchmarks" / "analysis",
                        help="Output directory for stats.csv and plots/")
    args = parser.parse_args(argv)

    runs = discover(args.results)
    if not runs:
        print(f"No CSVs found under {args.results}", file=sys.stderr)
        return 1

    stats_df = summarize(runs)
    args.out.mkdir(parents=True, exist_ok=True)
    stats_csv = args.out / "stats.csv"
    stats_df.to_csv(stats_csv, index=False)
    print(f"Wrote {stats_csv}  ({len(stats_df)} rows)")

    plots_dir = args.out / "plots"
    boxplot_compare(runs, "cycles", "Cycles", plots_dir)
    boxplot_compare(runs, "time_ms", "Time (ms)", plots_dir)
    bar_with_ci(stats_df, "time_ms_mean", "time_ms_ci95_lo", "time_ms_ci95_hi",
                "Time (ms)", plots_dir / "bar_time_ms.png")
    bar_with_ci(stats_df, "cycles_mean", "cycles_ci95_lo", "cycles_ci95_hi",
                "Cycles", plots_dir / "bar_cycles.png")
    bar_total_time(stats_df, plots_dir / "bar_total_time_ms.png")
    bar_rss(stats_df, plots_dir / "bar_rss_kb.png")
    fail_rate_chart(stats_df, plots_dir / "bar_fail_rate.png")
    print(f"Wrote plots to {plots_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
