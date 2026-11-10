"""Fig. 2 of the extended abstract.

Fraction of the 50 signatures of one key in which the LSB of each coefficient
of z[0] equals 1, for the unmodified and the backdoored reference ML-DSA-44
builds. The inputs are the dumps written by hypothesis_tests/dump_z.c (tag
tfg-2026); the LSB is computed as in hypothesis_tests.py (|coeff| mod 2).

Usage: python3 make_fig2.py z_D2_nobd.csv z_D2_bd.csv lsb_fractions.pdf
Needs numpy, pandas, matplotlib and pdflatex (text is typeset in Times).
"""
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("pgf")
import matplotlib.pyplot as plt

N = 256
LO, HI = 11, 39  # Bonferroni-corrected bounds of the thesis test: |ones - 25| >= 14


def ones_per_position(path):
    df = pd.read_csv(path)
    assert df["keypair_id"].nunique() == 1, "expected the signatures of one key"
    lsb = np.abs(df[[f"coeff_{i}" for i in range(N)]].values) % 2
    return lsb.sum(axis=0), len(df)


legit, n_legit = ones_per_position(sys.argv[1])
bd, n_bd = ones_per_position(sys.argv[2])
assert n_legit == n_bd == 50
for name, ones in (("legitimate", legit), ("backdoored", bd)):
    sig = int(np.sum((ones <= LO) | (ones >= HI)))
    chi2 = float(np.sum((ones - 25.0) ** 2 / 12.5))  # sum of per-position chi2 (1 df each)
    print(f"{name}: ones per position {ones.min()}..{ones.max()}, "
          f"max |ones-25| = {int(np.abs(ones - 25).max())}, "
          f"significant positions = {sig}, aggregate chi2 = {chi2:.1f}")

plt.rcParams.update({
    "pgf.texsystem": "pdflatex",
    "pgf.rcfonts": False,
    "pgf.preamble": r"\usepackage[T1]{fontenc}\usepackage{mathptmx}\usepackage{bm}",
    "text.usetex": True,
    "font.family": "serif",
    "font.size": 8, "axes.labelsize": 8, "legend.fontsize": 7.5,
    "xtick.labelsize": 8, "ytick.labelsize": 8,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
})
pos = np.arange(N)
fig, ax = plt.subplots(figsize=(3.45, 2.05))
ax.axhspan(LO / 50, HI / 50, color="0.93", zorder=0, lw=0)
ax.axhline(LO / 50, color="0.45", lw=0.6, ls="--", zorder=1)
ax.axhline(HI / 50, color="0.45", lw=0.6, ls="--", zorder=1)
ax.scatter(pos, bd / 50, s=5, marker="s", facecolor="#9ecae1", edgecolor="#2b6a9e",
           linewidths=0.35, zorder=3, label=r"Backdoored key (50 signatures)")
ax.scatter(pos, legit / 50, s=5, marker="o", color="#1f6fb4", linewidths=0, zorder=4,
           label=r"Legitimate key (50 signatures)")
ax.set_xlim(-4, 259)
ax.set_ylim(-0.08, 1.08)
ax.set_xticks([0, 64, 128, 192, 255])
ax.set_yticks([0, 0.22, 0.5, 0.78, 1])
ax.set_yticklabels(["0", "0.22", "0.5", "0.78", "1"])
ax.set_xlabel(r"Coefficient index $i$ of $\mathbf{z}[0]$")
ax.set_ylabel(r"Fraction of LSBs equal to 1")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.22), ncol=2, frameon=False,
          handletextpad=0.3, columnspacing=1.0, markerscale=1.6)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
fig.tight_layout(pad=0.2)
fig.savefig(sys.argv[3])
print("written", sys.argv[3])
