"""
Regenerate the three manuscript figures using the 2010 calibration cutoff
and 2010-2026 analytic window:

  Figure 1: yearly_three_detector_lines.png
  Figure 2: fig_writing_quality_trend.png  (Gartenberg analog of Fig 6)
  Figure 3: fig_writing_quality_forest.png (Gartenberg analog of Fig 8)
"""

import pandas as pd, numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib import patches as mpatches
from scipy.stats import gaussian_kde
from pathlib import Path

ROOT = Path("/Users/beperron/Desktop/AI-SSWR")
OUT  = ROOT / "results" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

mpl.rcParams["font.family"]   = ["Helvetica", "Arial", "DejaVu Sans"]
mpl.rcParams["pdf.fonttype"]  = 42
mpl.rcParams["ps.fonttype"]   = 42
mpl.rcParams["axes.linewidth"] = 0.7

# Palette
TEAL_LINE = "#5BAEA8"
TEAL_FILL = "#BFD9D6"
PRE       = "#7C7C7C"
LOW       = "#E69F00"
MID       = "#5BAEA8"
HIGH      = "#0072B2"
FULL      = "#D55E00"
GRID      = "#ececec"
AXIS_GRAY = "#bbbbbb"

CAL_LO, CAL_HI = 2010, 2017
ANALYTIC_LO    = 2010

# ---- Load detector scores + apply locked P95 thresholds ----------------
edl_r = pd.read_pickle(ROOT/"data"/"scores_editlens_roberta.pkl")[
    ["id","year","score_editlens","bucket_editlens","text_wc"]]
edl_l = pd.read_pickle(ROOT/"data"/"scores_editlens_llama.pkl")[
    ["id","score_editlens_llama","bucket_editlens_llama"]]
desk  = pd.read_pickle(ROOT/"data"/"scores_primary_academic.pkl")[["id","score_primary"]]
# Primary writing-quality source: Gartenberg study reference code outputs (data/scores_hassan.pkl).
# Renamed columns to standard names so downstream code is unchanged.
wq = pd.read_pickle(ROOT/"data"/"scores_hassan.pkl")[
    ["id","hassan_fre","hassan_fk","hassan_fog","hassan_smog",
     "hassan_nom_ratio","hassan_passive_ratio","hassan_hedge_density"]
].rename(columns={
    "hassan_fre":           "flesch_reading_ease",
    "hassan_fk":            "flesch_kincaid_grade",
    "hassan_fog":           "fog_index",
    "hassan_smog":          "smog_index",
    "hassan_nom_ratio":     "nominalization_rate",
    "hassan_passive_ratio": "passive_rate",
    "hassan_hedge_density": "hedge_rate",
})

df = edl_r.merge(edl_l, on="id").merge(desk, on="id").merge(wq, on="id")
for c in ["score_editlens","score_editlens_llama","score_primary"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df["bucket_editlens"] = pd.to_numeric(df["bucket_editlens"], errors="coerce")
df = df[df.year >= ANALYTIC_LO].copy()

cal = df[(df.year>=CAL_LO)&(df.year<=CAL_HI)]
P95_e = float(np.quantile(cal.score_editlens,       0.95))
P95_l = float(np.quantile(cal.score_editlens_llama, 0.95))
P95_d = float(np.quantile(cal.score_primary,        0.95))
print(f"P95 thresholds (2010-2017 baseline):")
print(f"  EditLens RoBERTa-large = {P95_e:.4f}")
print(f"  EditLens Llama-3.2-3B  = {P95_l:.4f}")
print(f"  desklib                = {P95_d:.4f}")

df["bin_e"] = (df.score_editlens       >= P95_e).astype(int)
df["bin_l"] = (df.score_editlens_llama >= P95_l).astype(int)
df["bin_d"] = (df.score_primary        >= P95_d).astype(int)

# Standardize FRE on 2010-2017 baseline
fre_mean = float(cal.flesch_reading_ease.mean())
fre_sd   = float(cal.flesch_reading_ease.std())
df["fre_z"] = (df.flesch_reading_ease - fre_mean) / fre_sd
print(f"FRE 2010-2017 baseline: mean = {fre_mean:.2f}, sd = {fre_sd:.2f}")

# ====================================================================
# Figure 1: yearly_three_detector_lines.png
# Title and footer note are placed in the Word document, not the figure.
# ====================================================================
yearly = df.groupby("year").agg(
    n=("bin_e","count"),
    pct_e=("bin_e", lambda x: x.mean()*100),
    pct_l=("bin_l", lambda x: x.mean()*100),
    pct_d=("bin_d", lambda x: x.mean()*100),
).reset_index()

years = list(yearly.year)
edl_R = list(yearly.pct_e)
edl_L = list(yearly.pct_l)
desk_pct = list(yearly.pct_d)

detectors = [
    ("EditLens RoBERTa-large", edl_R, "#0072B2"),
    ("EditLens Llama-3.2-3B",  edl_L, "#009E73"),
    ("desklib academic",       desk_pct, "#D62728"),
]

# End-of-line label vertical offsets to avoid overlap. Llama is far from the
# others (82.9), so leave it at its actual y; RoBERTa (56.1) and desklib (55.3)
# are very close, so push them apart.
end_label_offset = {
    "EditLens RoBERTa-large":  +5.5,
    "EditLens Llama-3.2-3B":    0.0,
    "desklib academic":        -5.5,
}

fig, ax = plt.subplots(figsize=(13.5, 8.0), dpi=160)

# Era shading
ax.axvspan(2010, 2017, color="#f3f3f3", alpha=0.55, zorder=0)
ax.axvspan(2023.5, 2024.5, color="#FFE8C7", alpha=0.55, zorder=0)
ax.axvspan(2024.5, 2026.5, color="#FFCC8A", alpha=0.55, zorder=0)

# Era legend — only the two exposure bands. The gray calibration window
# is labeled inline (below) rather than in the legend, because gray would
# misleadingly imply the entire no-exposure span (conf 2010–2023) is gray
# when only conf 2010–2017 (the calibration window) is gray; conf 2017–2023
# is unshaded white.
legend_handles = [
    mpatches.Patch(facecolor="#FFE8C7", edgecolor="#bbbbbb",
                   label="Partial exposure  (conf 2024; ChatGPT released Nov 2022)"),
    mpatches.Patch(facecolor="#FFCC8A", edgecolor="#bbbbbb",
                   label="Full exposure  (conf 2025–2026)"),
]
era_legend = ax.legend(handles=legend_handles, loc="upper left",
                       bbox_to_anchor=(0.01, 0.99),
                       fontsize=12, frameon=True, facecolor="white",
                       edgecolor="#cccccc", borderpad=0.7,
                       handlelength=1.6, handleheight=1.1, labelcolor="#222222")
era_legend.get_frame().set_linewidth(0.8)

# Horizontal 5% threshold reference line. No arrows / vertical reference
# lines: the era shading conveys the time-period boundaries, and arrows
# pointing into the chart create false visual cues that suggest specific
# data points.
ax.axhline(5.0, color="#999999", lw=0.9, ls=":", zorder=1)

# Inline label sitting inside the gray band — names what gray means.
# Replaces the legend entry the gray band used to have.
ax.text(2013.5, 65, "Calibration window\n(conf 2010–2017)",
        ha="center", va="center", fontsize=11, color="black", style="italic")

# 5% threshold label, anchored at the right edge directly above the dotted
# line so the line itself acts as the visual leader (no arrow needed).
ax.text(2030.3, 6.5, "5 % P95 threshold",
        ha="right", va="bottom", fontsize=11, color="#666666", style="italic")

# Grammarly freemium launch — vertical reference line placed at the
# calendar-time position of May 2015 on the conference-year axis (rather
# than aligning to a specific SSWR cycle). A filled marker on the line at
# y=20 anchors the inline label, which sits to the left of the line and
# terminates at the marker.
GRAMMARLY_X = 2015.4   # ≈ May 2015 on a year-decimal axis
ax.vlines(GRAMMARLY_X, 0, 78, colors="#404040", linestyles="--",
          linewidth=1.0, alpha=0.85, zorder=2)
ax.plot([GRAMMARLY_X], [20], marker="o", color="#404040", markersize=8,
        markeredgecolor="white", markeredgewidth=1.0, zorder=3,
        linestyle="none")
ax.text(GRAMMARLY_X - 0.08, 20, "Grammarly freemium launch (May 2015)",
        ha="right", va="center", fontsize=11, color="#404040")

# Plot lines
for name, ys, color in detectors:
    ax.plot(years, ys, color=color, lw=2.8, marker="o", markersize=7.0,
            markeredgecolor="white", markeredgewidth=1.2, zorder=3, label=name)

# End-of-line labels — single line, big, bold, with the percent on the same line
for name, ys, color in detectors:
    y_end = ys[-1] + end_label_offset[name]
    ax.text(2026.30, y_end, f"{name}  {ys[-1]:.1f}%",
            ha="left", va="center", fontsize=13,
            color=color, fontweight="bold")

# Axes
ax.set_xticks([y for y in years if y % 2 == 1])
ax.set_xticklabels([str(y) for y in years if y % 2 == 1], fontsize=12)
ax.set_xlim(2009.5, 2030.5)
ax.set_xlabel("Conference year (April year − 1 = submission deadline)",
              fontsize=14, color="#222222", labelpad=12)
ax.set_ylim(0, 100)
ax.set_yticks([0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
ax.set_ylabel("% of abstracts above 2010–2017 calibrated P95",
              fontsize=14, color="#222222")
ax.tick_params(axis="both", labelsize=12, color="#999999", labelcolor="#222222")
ax.grid(axis="y", color=GRID, lw=0.7, zorder=0)
for s in ("top", "right"): ax.spines[s].set_visible(False)
ax.spines["left"].set_color(AXIS_GRAY)
ax.spines["bottom"].set_color(AXIS_GRAY)

plt.subplots_adjust(top=0.96, bottom=0.10, left=0.06, right=0.98)
out_png = OUT / "yearly_three_detector_lines.png"
plt.savefig(out_png, dpi=300, bbox_inches="tight", facecolor="white", pad_inches=0.25)
plt.savefig(OUT / "yearly_three_detector_lines.svg", bbox_inches="tight", facecolor="white", pad_inches=0.25)
plt.close(fig)
print(f"Saved -> {out_png}")

# ====================================================================
# Figure 2: fig_writing_quality_trend.png (Gartenberg Fig 6 analog)
# Truncated x-axis starting at 2017.
# ====================================================================
yearly_fre = df.groupby("year").agg(
    mean=("fre_z","mean"),
    sem =("fre_z", lambda x: x.std()/np.sqrt(len(x))),
).reset_index()
yearly_fre["lo"] = yearly_fre["mean"] - 1.96*yearly_fre["sem"]
yearly_fre["hi"] = yearly_fre["mean"] + 1.96*yearly_fre["sem"]

# Range of omitted (2010-2016) values
hidden = yearly_fre[yearly_fre.year <= 2016]
hid_min = float(hidden["mean"].min())
hid_max = float(hidden["mean"].max())
shown = yearly_fre[yearly_fre.year >= 2017]

fig, ax = plt.subplots(figsize=(12.5, 7.0), dpi=160)

# Era shading — same scheme as Figure 1 (no-exposure / partial / full).
# Bands replace the previous ChatGPT-release dashed reference line.
ax.axvspan(2016.3,  2023.5, color="#f3f3f3", alpha=0.55, zorder=0)
ax.axvspan(2023.5,  2024.5, color="#FFE8C7", alpha=0.55, zorder=0)
ax.axvspan(2024.5,  2026.6, color="#FFCC8A", alpha=0.55, zorder=0)

ax.fill_between(shown.year, shown.lo, shown.hi,
                color=TEAL_FILL, alpha=0.7, zorder=2)
ax.plot(shown.year, shown["mean"], color=TEAL_LINE, lw=2.6,
        marker="o", markersize=7.0, markeredgecolor="white",
        markeredgewidth=1.2, zorder=3)
ax.axhline(0, color="#bbbbbb", lw=0.9, zorder=1)

# Era legend (upper-right, where the data line is high and space is empty)
era_handles = [
    mpatches.Patch(facecolor="#f3f3f3", edgecolor="#bbbbbb",
                   label="No LLM exposure  (conf 2017–2023)"),
    mpatches.Patch(facecolor="#FFE8C7", edgecolor="#bbbbbb",
                   label="Partial exposure  (conf 2024)"),
    mpatches.Patch(facecolor="#FFCC8A", edgecolor="#bbbbbb",
                   label="Full exposure  (conf 2025–2026)"),
]
era_legend = ax.legend(handles=era_handles, loc="upper right",
                       bbox_to_anchor=(0.99, 0.99),
                       fontsize=11, frameon=True, facecolor="white",
                       edgecolor="#cccccc", borderpad=0.7,
                       handlelength=1.6, handleheight=1.1,
                       labelcolor="#222222")
era_legend.get_frame().set_linewidth(0.8)

# Y axis
ax.set_ylabel("Flesch Reading Ease (SD units, 2010–2017 baseline)",
              fontsize=14, color="#222222")
ax.set_ylim(-1.9, 0.55)
ax.set_yticks([-1.5, -1.0, -0.5, 0.0, 0.5])
ax.tick_params(axis="y", labelsize=12, color=AXIS_GRAY, labelcolor="#222222")
ax.grid(axis="y", color=GRID, lw=0.7, zorder=0)

# X axis (truncated)
ax.set_xlim(2016.3, 2026.6)
ax.set_xticks(list(range(2017, 2027)))
ax.set_xticklabels([str(y) for y in range(2017, 2027)],
                   rotation=0, ha="center", fontsize=12)
ax.set_xlabel("Conference year (April year − 1 = submission deadline)",
              fontsize=14, color="#222222", labelpad=10)

# Truncation marker on x-axis
ax.text(2016.50, -1.99, "//", ha="center", va="top",
        fontsize=18, color="#888888", fontweight="bold",
        clip_on=False, zorder=10)

# Truncation note placed in the lower-left corner of the plot area
# (the data line is high there so this region is visually empty)
ax.text(2016.50, 0.40,
        f"Conf 2010–2016 omitted (each cycle\n"
        f"within {hid_min:+.2f} to {hid_max:+.2f} SD of baseline)",
        ha="left", va="top", fontsize=11, color="#444444",
        style="italic",
        bbox=dict(boxstyle="round,pad=0.40", facecolor="#fafafa",
                  edgecolor="#cccccc", lw=0.7))

for s in ("top", "right"): ax.spines[s].set_visible(False)
ax.spines["left"].set_color(AXIS_GRAY)
ax.spines["bottom"].set_color(AXIS_GRAY)

plt.subplots_adjust(top=0.96, bottom=0.13, left=0.08, right=0.97)
out_png = OUT / "fig_writing_quality_trend.png"
plt.savefig(out_png, dpi=300, bbox_inches="tight", facecolor="white", pad_inches=0.25)
plt.savefig(OUT / "fig_writing_quality_trend.svg", bbox_inches="tight", facecolor="white", pad_inches=0.25)
plt.close(fig)
print(f"Saved -> {out_png}")

# ====================================================================
# Figure 3: fig_writing_quality_forest.png (Gartenberg Fig 8 analog)
# Three-bucket dose-response barbell across writing-quality metrics
# ====================================================================
# Restricted to the seven Gartenberg-aligned metrics whose operationalization
# is fully specified in the published paper.
METRICS = [
    ("flesch_reading_ease",  "Flesch Reading Ease",       "better"),
    ("flesch_kincaid_grade", "Grade Level",               "worse"),
    ("fog_index",            "Gunning FOG Index",         "worse"),
    ("smog_index",           "SMOG Index",                "worse"),
    ("nominalization_rate",  "Nominalization rate",       "worse"),
    ("passive_rate",         "Passive Voice rate",        "worse"),
    ("hedge_rate",           "Hedging rate",              "worse"),
]

m_mean = {col: float(cal[col].mean()) for col, _, _ in METRICS}
m_sd   = {col: float(cal[col].std())  for col, _, _ in METRICS}

post = df[df.year >= 2024]
BUCKET_HUMAN = "#666666"
BUCKETS = [(0, "Human (no AI)",      BUCKET_HUMAN),
           (1, "Lightly AI-edited",  LOW),
           (3, "Fully AI-generated", FULL)]

records = []
for col, label, direction in METRICS:
    for bk, blabel, color in BUCKETS:
        sub = post[post.bucket_editlens == bk][col].dropna()
        if len(sub) < 10: continue
        z = (sub - m_mean[col]) / m_sd[col]
        mean_z = z.mean(); sem_z = z.std() / np.sqrt(len(z))
        records.append({"metric": label, "bucket": blabel,
                        "mean_z": mean_z, "lo": mean_z - 1.96*sem_z,
                        "hi": mean_z + 1.96*sem_z, "n": len(z)})
res = pd.DataFrame(records)

better_metrics = [m for m in METRICS if m[2] == "better"]
worse_metrics  = [m for m in METRICS if m[2] == "worse"]
ordered_labels = [m[1] for m in better_metrics] + [m[1] for m in worse_metrics]
n_better = len(better_metrics); n_worse = len(worse_metrics)
n_total  = len(ordered_labels)

fig, ax = plt.subplots(figsize=(13.0, 8.5), dpi=160)

y_positions = {label: i for i, label in enumerate(reversed(ordered_labels))}

ax.axhspan(n_worse - 0.5, n_total - 0.5, color="#E8F5E9", alpha=0.55, zorder=0)
ax.axhspan(-0.5, n_worse - 0.5, color="#FFEBEE", alpha=0.55, zorder=0)
ax.axvline(0, color="#666666", lw=1.1, zorder=1)

res_pivot = res.pivot_table(index="metric", columns="bucket",
                            values="mean_z").reindex(ordered_labels)
res_ci = {(r.metric, r.bucket): (r.lo, r.hi) for _, r in res.iterrows()}

for metric, row in res_pivot.iterrows():
    y = y_positions[metric]
    x_h = row["Human (no AI)"]
    x_l = row["Lightly AI-edited"]
    x_f = row["Fully AI-generated"]
    x0, x1 = min(x_h, x_l, x_f), max(x_h, x_l, x_f)
    ax.plot([x0, x1], [y, y], color="#999999", lw=2.4, alpha=0.55,
            solid_capstyle="round", zorder=2)
    for bk_label, color in [("Human (no AI)", BUCKET_HUMAN),
                            ("Lightly AI-edited", LOW),
                            ("Fully AI-generated", FULL)]:
        lo, hi = res_ci[(metric, bk_label)]
        ax.plot([lo, hi], [y, y], color=color, lw=1.2, alpha=0.6, zorder=3)
    ax.scatter([x_h], [y], s=140, color=BUCKET_HUMAN, edgecolor="white", linewidth=1.6, zorder=5)
    ax.scatter([x_l], [y], s=170, color=LOW,          edgecolor="white", linewidth=1.8, zorder=5)
    ax.scatter([x_f], [y], s=170, color=FULL,         edgecolor="white", linewidth=1.8, zorder=5)
    ax.text(x_f + (0.08 if x_f >= 0 else -0.08), y + 0.30,
            f"{x_f:+.2f}",
            ha="left" if x_f >= 0 else "right",
            va="bottom", fontsize=12, color=FULL, fontweight="bold")

ax.set_yticks(list(y_positions.values()))
ax.set_yticklabels(list(y_positions.keys()), fontsize=13, color="#222222")

# Banner labels in the upper-right corner of each band
xlo = res[["lo"]].min().min() - 0.35
xhi = res[["hi"]].max().max() + 0.55
ax.set_xlim(xlo, xhi)

ax.text(-0.10, n_total - 0.55, "Higher = Better Quality",
        ha="right", va="center", fontsize=12.5, color="#1B5E20",
        fontweight="bold", style="italic",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                  edgecolor="#a5d6a7", lw=0.9))
ax.text(xhi - 0.05, n_worse - 0.55, "Higher = Worse Quality",
        ha="right", va="center", fontsize=12.5, color="#7F1D1D",
        fontweight="bold", style="italic",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                  edgecolor="#ef9a9a", lw=0.9))

ax.set_xlabel("Effect size (SD units relative to 2010–2017 pre-LLM baseline)",
              fontsize=14, color="#222222", labelpad=10)
ax.tick_params(axis="x", labelsize=12, color=AXIS_GRAY, labelcolor="#222222")
ax.grid(axis="x", color=GRID, lw=0.7, zorder=0)
ax.set_ylim(-0.7, n_total - 0.3)
for s in ("top", "right"): ax.spines[s].set_visible(False)
ax.spines["left"].set_color(AXIS_GRAY)
ax.spines["bottom"].set_color(AXIS_GRAY)

legend_handles = [
    plt.Line2D([0],[0], marker="o", color="w", markerfacecolor=BUCKET_HUMAN,
               markersize=11, markeredgecolor="white",
               label="Human / no AI (bucket 0)"),
    plt.Line2D([0],[0], marker="o", color="w", markerfacecolor=LOW,
               markersize=12, markeredgecolor="white",
               label="Lightly AI-edited (bucket 1)"),
    plt.Line2D([0],[0], marker="o", color="w", markerfacecolor=FULL,
               markersize=12, markeredgecolor="white",
               label="Fully AI-generated (bucket 3)"),
]
leg = ax.legend(handles=legend_handles, loc="lower right",
                fontsize=12, frameon=True, facecolor="white",
                edgecolor="#cccccc", borderpad=0.7, labelcolor="#222222",
                handlelength=1.4)
leg.get_frame().set_linewidth(0.8)

plt.subplots_adjust(top=0.96, bottom=0.10, left=0.22, right=0.97)
out_png = OUT / "fig_writing_quality_forest.png"
plt.savefig(out_png, dpi=300, bbox_inches="tight", facecolor="white", pad_inches=0.25)
plt.savefig(OUT / "fig_writing_quality_forest.svg", bbox_inches="tight", facecolor="white", pad_inches=0.25)
plt.close(fig)
print(f"Saved -> {out_png}")

print("\nAll three figures regenerated with 2010 calibration.")
