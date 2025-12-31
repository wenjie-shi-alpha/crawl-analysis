#!/usr/bin/env python3
"""
基于结构化抽取结果的量化分析与可视化脚本。

输入: medium_scale_crawler 生成的 structured JSON 或 JSONL 扁平表
输出: data/output/analysis 下的若干统计图
"""

from __future__ import annotations

import argparse
import json
import warnings
import shutil
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import Counter

# ===== 字体初始化：必须在 matplotlib 加载前执行 =====
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd
import seaborn as sns
import numpy as np

try:
    import networkx as nx  # type: ignore

    NETWORKX_AVAILABLE = True
except Exception:
    NETWORKX_AVAILABLE = False

# 压制所有警告
warnings.filterwarnings('ignore')

# ===== 全局字体设置 =====
# 清除 matplotlib 字体缓存以确保新字体被识别
_cache_dir = Path.home() / '.cache' / 'matplotlib'
if _cache_dir.exists():
    shutil.rmtree(_cache_dir, ignore_errors=True)
_cache_dir.mkdir(parents=True, exist_ok=True)

# 重新构建字体管理器
fm._load_fontmanager(try_read_cache=False)

# 查找并设置中文字体
FONT_PATH = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
if not Path(FONT_PATH).exists():
    # 备选字体
    for alt in ['/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
                '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf']:
        if Path(alt).exists():
            FONT_PATH = alt
            break

# 创建全局 FontProperties 对象
CHINESE_FONT = fm.FontProperties(fname=FONT_PATH) if Path(FONT_PATH).exists() else None

if CHINESE_FONT:
    # 注册字体
    fm.fontManager.addfont(FONT_PATH)


def get_font():
    """获取中文字体属性对象。"""
    return CHINESE_FONT


# 统一风格
sns.set_theme(style="whitegrid", context="talk")
BASE_BG = "#f7f7f5"
plt.rcParams["figure.facecolor"] = BASE_BG
plt.rcParams["axes.facecolor"] = BASE_BG
plt.rcParams["savefig.facecolor"] = BASE_BG


def _wrap_label(text: Any, width: int = 16) -> str:
    """Wrap long labels to reduce重叠。"""

    if text is None:
        return ""
    s = str(text)
    if len(s) <= width:
        return s
    # 简单按宽度插入换行符
    parts = [s[i : i + width] for i in range(0, len(s), width)]
    return "\n".join(parts)


def _as_year(value: Any) -> Optional[int]:
    """将年份字段转换为int，非数字返回None。"""
    if value is None:
        return None
    try:
        year_int = int(str(value)[:4])
        if 1990 <= year_int <= 2100:
            return year_int
    except Exception:
        return None
    return None


def _to_float(value: Any) -> Optional[float]:
    """从字符串或数字中提取首个浮点数，失败返回None。"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    if match:
        try:
            return float(match.group())
        except Exception:
            return None
    return None


def _as_list_of_dict(value: Any) -> List[Dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [v for v in value if isinstance(v, dict)]
    return []


def _as_list_of_str(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value if isinstance(v, (str, int, float)) and str(v).strip()]
    return []


def load_records(path: Path) -> List[Dict[str, Any]]:
    """支持JSON(list)或JSONL读取。"""
    if not path.exists():
        raise FileNotFoundError(f"未找到输入文件: {path}")
    if path.suffix.lower() == ".jsonl":
        with path.open("r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("results") if isinstance(data, dict) and "results" in data else data


def _ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _save_figure(output_dir: Path, basename: str, dpi: int = 300) -> None:
    """Save current matplotlib figure as both PNG and PDF.

    PDF is preferred for publication (vector). PNG is convenient for quick preview.
    """
    _ensure_output_dir(output_dir)
    plt.savefig(output_dir / f"{basename}.png", dpi=dpi, bbox_inches="tight")
    plt.savefig(output_dir / f"{basename}.pdf", dpi=dpi, bbox_inches="tight")


def _bootstrap_ci(values: np.ndarray, n_boot: int = 2000, ci: float = 0.95, seed: int = 42) -> Tuple[float, float]:
    """Simple bootstrap CI for mean."""
    values = values[~np.isnan(values)]
    if values.size == 0:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    boots = rng.choice(values, size=(n_boot, values.size), replace=True).mean(axis=1)
    alpha = (1 - ci) / 2
    return (float(np.quantile(boots, alpha)), float(np.quantile(boots, 1 - alpha)))


def build_driver_df(records: List[Dict[str, Any]]) -> pd.DataFrame:
    data = []
    for idx, rec in enumerate(records):
        for driver in _as_list_of_dict(rec.get("drivers")):
            data.append(
                {
                    "record_id": rec.get("id") or rec.get("doc_id") or rec.get("source_id") or idx,
                    "factor": driver.get("factor"),
                    "category": driver.get("category"),
                    "strength_score": driver.get("strength_score"),
                    "year": _as_year(rec.get("year")),
                    "geography": rec.get("geography"),
                }
            )
    return pd.DataFrame(data)


def build_barrier_df(records: List[Dict[str, Any]]) -> pd.DataFrame:
    data = []
    for idx, rec in enumerate(records):
        for barrier in _as_list_of_dict(rec.get("barriers")):
            data.append(
                {
                    "record_id": rec.get("id") or rec.get("doc_id") or rec.get("source_id") or idx,
                    "factor": barrier.get("factor"),
                    "category": barrier.get("category"),
                    "severity_score": barrier.get("severity_score"),
                    "year": _as_year(rec.get("year")),
                    "geography": rec.get("geography"),
                }
            )
    return pd.DataFrame(data)


def build_stakeholder_df(records: List[Dict[str, Any]]) -> pd.DataFrame:
    data = []
    for rec in records:
        overall_stance_raw = rec.get("stance_score")
        if overall_stance_raw is None:
            overall_stance_raw = rec.get("overall_sentiment")
        overall_stance = pd.to_numeric(overall_stance_raw, errors="coerce")

        stakeholders_value = rec.get("stakeholders")
        if isinstance(stakeholders_value, list) and stakeholders_value and all(isinstance(s, dict) for s in stakeholders_value):
            for s in stakeholders_value:
                label = (s.get("type") or s.get("name") or "").strip() if isinstance(s, dict) else ""
                if not label:
                    continue
                stance = pd.to_numeric(s.get("stance"), errors="coerce") if isinstance(s, dict) else overall_stance
                if pd.isna(stance):
                    stance = overall_stance
                data.append({"stakeholder": label, "stance_score": stance})
        else:
            for stakeholder in _as_list_of_str(stakeholders_value):
                data.append({"stakeholder": stakeholder, "stance_score": overall_stance})
    return pd.DataFrame(data)


def build_metric_df(records: List[Dict[str, Any]]) -> pd.DataFrame:
    data = []
    for rec in records:
        year = _as_year(rec.get("year"))
        for metric in _as_list_of_dict(rec.get("metrics")):
            data.append(
                {
                    "name": metric.get("name"),
                    "value": metric.get("value"),
                    "unit": metric.get("unit"),
                    "year": _as_year(metric.get("year") or year),
                }
            )
    return pd.DataFrame(data)


def plot_driver_strength(df: pd.DataFrame, output_dir: Path, dpi: int = 300) -> None:
    if df.empty:
        print("跳过驱动因素图：无数据")
        return
    df = df.copy()
    df["category"] = df["category"].apply(_wrap_label)
    grouped = (
        df.groupby("category")["strength_score"]
        .mean()
        .reset_index()
        .sort_values(by="strength_score", ascending=False)
    )
    height = max(4, 0.6 * len(grouped))
    plt.figure(figsize=(8, height))
    sns.barplot(
        data=grouped,
        x="strength_score",
        y="category",
        hue="category",
        palette="crest",
        legend=False,
        edgecolor="white",
    )
    font = get_font()
    plt.xlabel("平均驱动强度 (0-5)", fontproperties=font)
    plt.ylabel("PESTEL维度", fontproperties=font)
    plt.title("驱动因素强度分布（分维度）", fontsize=14, fontweight="bold", fontproperties=font)
    for label in plt.gca().get_yticklabels():
        label.set_fontproperties(font)
    plt.tight_layout()
    _save_figure(output_dir, "driver_strength", dpi=dpi)
    plt.close()


def plot_category_score_distributions(
    driver_df: pd.DataFrame,
    barrier_df: pd.DataFrame,
    output_dir: Path,
    dpi: int = 300,
) -> None:
    """Publication-friendly distribution plot showing scale and uncertainty.

    - Left: driver strength distributions by category
    - Right: barrier severity distributions by category
    Includes bootstrap 95% CI for mean and sample size annotation.
    """
    if driver_df.empty and barrier_df.empty:
        print("跳过分布图：无数据")
        return

    font = get_font()
    fig, axes = plt.subplots(1, 2, figsize=(16, 7), sharey=False)

    def _plot_one(ax, df: pd.DataFrame, score_col: str, title: str, palette: str):
        if df.empty:
            ax.set_axis_off()
            ax.set_title(f"{title}\n（无数据）", fontproperties=font)
            return
        d = df.copy()
        d["category"] = d["category"].apply(_wrap_label)
        d[score_col] = pd.to_numeric(d[score_col], errors="coerce")
        d = d.dropna(subset=["category", score_col])
        if d.empty:
            ax.set_axis_off()
            ax.set_title(f"{title}\n（无有效分值）", fontproperties=font)
            return

        order = (
            d.groupby("category")[score_col]
            .mean(numeric_only=True)
            .sort_values(ascending=False)
            .index.tolist()
        )

        sns.violinplot(
            data=d,
            y="category",
            x=score_col,
            order=order,
            inner=None,
            linewidth=0.8,
            palette=palette,
            ax=ax,
        )
        sns.stripplot(
            data=d,
            y="category",
            x=score_col,
            order=order,
            color="#222",
            alpha=0.25,
            size=2,
            jitter=0.25,
            ax=ax,
        )

        # Add mean + bootstrap CI
        y_positions = np.arange(len(order))
        means, lows, highs, ns = [], [], [], []
        for cat in order:
            vals = d.loc[d["category"] == cat, score_col].astype(float).to_numpy()
            ns.append(int(vals.size))
            means.append(float(np.nanmean(vals)))
            lo, hi = _bootstrap_ci(vals)
            lows.append(lo)
            highs.append(hi)
        ax.errorbar(
            x=means,
            y=y_positions,
            xerr=[np.array(means) - np.array(lows), np.array(highs) - np.array(means)],
            fmt="o",
            color="#111",
            markersize=4,
            capsize=3,
            linewidth=1,
            zorder=5,
        )

        for y, n in zip(y_positions, ns):
            ax.text(
                5.05,
                y,
                f"n={n}",
                va="center",
                ha="left",
                fontsize=9,
                fontproperties=font,
                color="#333",
            )

        ax.set_xlim(-0.1, 5.8)
        ax.set_title(title, fontsize=13, fontweight="bold", fontproperties=font)
        ax.set_xlabel("分值（0–5）", fontproperties=font)
        ax.set_ylabel("" , fontproperties=font)
        for label in ax.get_yticklabels():
            label.set_fontproperties(font)

    _plot_one(axes[0], driver_df, "strength_score", "驱动因素强度分布（含95%CI与样本量）", "crest")
    _plot_one(axes[1], barrier_df, "severity_score", "阻碍因素严重度分布（含95%CI与样本量）", "flare")

    fig.suptitle("PESTEL维度分布与不确定性（条目级）", fontsize=14, fontweight="bold", fontproperties=font)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    _save_figure(output_dir, "pestel_distribution_ci", dpi=dpi)
    plt.close(fig)


def plot_barrier_severity(df: pd.DataFrame, output_dir: Path, dpi: int = 300) -> None:
    if df.empty:
        print("跳过阻碍因素图：无数据")
        return
    df = df.copy()
    df["category"] = df["category"].apply(_wrap_label)
    grouped = (
        df.groupby("category")["severity_score"]
        .mean()
        .reset_index()
        .sort_values(by="severity_score", ascending=False)
    )
    height = max(4, 0.6 * len(grouped))
    plt.figure(figsize=(8, height))
    sns.barplot(
        data=grouped,
        x="severity_score",
        y="category",
        hue="category",
        palette="flare",
        legend=False,
        edgecolor="white",
    )
    font = get_font()
    plt.xlabel("平均阻碍严重度 (0-5)", fontproperties=font)
    plt.ylabel("障碍维度", fontproperties=font)
    plt.title("阻碍因素严重度分布（分维度）", fontsize=14, fontweight="bold", fontproperties=font)
    for label in plt.gca().get_yticklabels():
        label.set_fontproperties(font)
    plt.tight_layout()
    _save_figure(output_dir, "barrier_severity", dpi=dpi)
    plt.close()


def plot_yearly_trend(records: List[Dict[str, Any]], output_dir: Path, dpi: int = 300) -> None:
    years = [_as_year(r.get("year")) for r in records if _as_year(r.get("year"))]
    if not years:
        print("跳过时间序列图：缺少年份")
        return
    df = pd.DataFrame({"year": years})
    counts = df["year"].value_counts().sort_index()
    plt.figure(figsize=(10, 5))
    sns.lineplot(x=counts.index, y=counts.values, marker="o", color="#3b7ea1", linewidth=2)
    plt.fill_between(counts.index, counts.values, color="#3b7ea1", alpha=0.15)
    font = get_font()
    plt.xlabel("年份", fontproperties=font)
    plt.ylabel("文档数量", fontproperties=font)
    plt.title("绿电相关文档时间演化（面积折线）", fontsize=14, fontweight="bold", fontproperties=font)
    plt.tight_layout()
    _save_figure(output_dir, "yearly_trend", dpi=dpi)
    plt.close()


def plot_stakeholder_stance(df: pd.DataFrame, output_dir: Path, dpi: int = 300) -> None:
    if df.empty:
        print("跳过利益相关方情感图：缺少数据")
        return
    df["stance_score"] = pd.to_numeric(df["stance_score"], errors="coerce")
    df = df.dropna(subset=["stance_score"])
    if df.empty:
        print("跳过利益相关方情感图：缺少可用数值")
        return
    df = df.copy()
    df["stakeholder"] = df["stakeholder"].apply(_wrap_label)
    grouped = df.groupby("stakeholder")["stance_score"].mean(numeric_only=True).reset_index()
    grouped = grouped.sort_values("stance_score")
    height = max(4, 0.5 * len(grouped))
    plt.figure(figsize=(10, height))
    colors = grouped["stance_score"].apply(lambda v: "#4c9a2a" if v >= 0 else "#d94a4a")
    plt.axvline(0, color="#888", linewidth=1, linestyle="--")
    plt.hlines(y=grouped["stakeholder"], xmin=0, xmax=grouped["stance_score"], color=colors, linewidth=4)
    plt.plot(grouped["stance_score"], grouped["stakeholder"], "o", color="#444")
    font = get_font()
    plt.xlabel("平均立场/情感分数 (-2~2)", fontproperties=font)
    plt.ylabel("利益相关方", fontproperties=font)
    plt.title("利益相关方情感/立场分布（正负对称）", fontsize=14, fontweight="bold", fontproperties=font)
    for label in plt.gca().get_yticklabels():
        label.set_fontproperties(font)
    plt.tight_layout()
    _save_figure(output_dir, "stakeholder_stance", dpi=dpi)
    plt.close()


def plot_metric_counts(df: pd.DataFrame, output_dir: Path, dpi: int = 300) -> None:
    if df.empty:
        print("跳过量化指标图：无数据")
        return
    counts = df["name"].value_counts().reset_index()
    counts.columns = ["name", "count"]
    counts["name"] = counts["name"].apply(_wrap_label)
    counts = counts.head(30)  # 限制顶级指标，避免坐标轴过长
    height = max(5, 0.35 * len(counts))
    plt.figure(figsize=(12, height))
    y = counts["name"]
    x = counts["count"]
    palette = sns.color_palette("rocket", len(counts))
    plt.hlines(y=y, xmin=0, xmax=x, color=palette, linewidth=3)
    plt.plot(x, y, "o", color="#2e2e2e")
    font = get_font()
    plt.xlabel("出现次数", fontproperties=font)
    plt.ylabel("指标名称", fontproperties=font)
    plt.title("量化指标覆盖情况（Lollipop）", fontsize=14, fontweight="bold", fontproperties=font)
    for label in plt.gca().get_yticklabels():
        label.set_fontproperties(font)
    plt.tight_layout()
    _save_figure(output_dir, "metrics_coverage", dpi=dpi)
    plt.close()


def plot_driver_barrier_heatmap(driver_df: pd.DataFrame, barrier_df: pd.DataFrame, output_dir: Path, dpi: int = 300) -> None:
    """高阶：PESTEL 驱动 vs. 障碍平均得分热力图。"""
    if driver_df.empty and barrier_df.empty:
        print("跳过驱动/阻碍热力图：无数据")
        return
    driver_df = driver_df.copy()
    barrier_df = barrier_df.copy()
    driver_df["category"] = driver_df["category"].apply(_wrap_label)
    barrier_df["category"] = barrier_df["category"].apply(_wrap_label)
    drivers = (
        driver_df.groupby("category")["strength_score"]
        .mean()
        .rename("driver_strength")
        if not driver_df.empty
        else pd.Series(dtype=float)
    )
    barriers = (
        barrier_df.groupby("category")["severity_score"]
        .mean()
        .rename("barrier_severity")
        if not barrier_df.empty
        else pd.Series(dtype=float)
    )
    combined = pd.concat([drivers, barriers], axis=1)
    combined = combined.reindex(sorted(combined.index))
    height = max(4, 0.5 * len(combined.index))
    fig, ax = plt.subplots(figsize=(8, height))
    font = get_font()
    sns.heatmap(
        combined,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        cbar_kws={"label": "强度 / 严重度", "shrink": 0.8},
        linewidths=0.5,
        linecolor="white",
        annot_kws={"size": 10},
        ax=ax,
    )
    ax.set_title("PESTEL 维度：驱动强度 vs. 阻碍严重度", fontsize=14, fontweight="bold", fontproperties=font)
    ax.set_xlabel("指标", fontproperties=font)
    ax.set_ylabel("PESTEL维度", fontproperties=font)
    for label in ax.get_yticklabels():
        label.set_fontproperties(font)
    for label in ax.get_xticklabels():
        label.set_fontproperties(font)
    # 设置 colorbar 标签字体
    cbar = ax.collections[0].colorbar
    if cbar:
        cbar.ax.set_ylabel("强度 / 严重度", fontproperties=font)
    ax.tick_params(axis="x", rotation=0)
    ax.tick_params(axis="y", rotation=0)
    fig.tight_layout()
    _save_figure(output_dir, "pestel_heatmap", dpi=dpi)
    plt.close()


def plot_driver_barrier_timeline(
    driver_df: pd.DataFrame,
    barrier_df: pd.DataFrame,
    output_dir: Path,
    year_range: Optional[Tuple[int, int]] = None,
    dpi: int = 300,
    count_mode: str = "document",
) -> None:
    """按年份展示驱动/阻碍数量时间演化。

    count_mode:
      - "document": 以记录/文献为单位计数（按 record_id 去重）
      - "instance": 以抽取条目为单位计数（driver/barrier 实例数）
    """

    if driver_df.empty and barrier_df.empty:
        print("跳过驱动/阻碍时间线：无数据")
        return

    def _count_by_year(df: pd.DataFrame, kind: str) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(columns=["year", "kind", "count"])
        d = df.dropna(subset=["year"]).copy()
        if d.empty:
            return pd.DataFrame(columns=["year", "kind", "count"])
        if year_range:
            start, end = year_range
            d = d[(d["year"] >= start) & (d["year"] <= end)]
        if d.empty:
            return pd.DataFrame(columns=["year", "kind", "count"])
        if count_mode == "document":
            counts = d.drop_duplicates(subset=["record_id", "year"]).groupby("year").size()
        else:
            counts = d.groupby("year").size()
        out = counts.reset_index(name="count")
        out["kind"] = kind
        return out

    driver_counts = _count_by_year(driver_df, "驱动")
    barrier_counts = _count_by_year(barrier_df, "阻碍")
    combined = pd.concat([driver_counts, barrier_counts], ignore_index=True)
    if combined.empty:
        print("跳过驱动/阻碍时间线：无有效年份数据")
        return

    pivoted = combined.pivot(index="year", columns="kind", values="count").fillna(0).sort_index()
    for col in ["驱动", "阻碍"]:
        if col not in pivoted.columns:
            pivoted[col] = 0

    fig, ax = plt.subplots(figsize=(10, 6))
    pivoted[["驱动", "阻碍"]].plot(
        kind="area",
        stacked=True,
        alpha=0.75,
        color=["#2a9d8f", "#e76f51"],
        linewidth=1.5,
        ax=ax,
    )
    font = get_font()
    ax.set_xlabel("年份", fontproperties=font)
    ylabel = "文档数量" if count_mode == "document" else "抽取条目数量"
    ax.set_ylabel(ylabel, fontproperties=font)
    title_suffix = "（文献级去重）" if count_mode == "document" else "（条目级计数）"
    ax.set_title(f"驱动 vs. 阻碍 时间演化{title_suffix}", fontsize=14, fontweight="bold", fontproperties=font)
    ax.set_xticks(pivoted.index)
    ax.set_xticklabels([str(int(y)) for y in pivoted.index], fontproperties=font, fontsize=9)
    ax.tick_params(axis="x", rotation=45)
    for label in ax.get_yticklabels():
        label.set_fontproperties(font)
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, labels, prop=font)
    plt.tight_layout()
    _save_figure(output_dir, "driver_barrier_timeline", dpi=dpi)
    plt.close()


def plot_stakeholder_heatmap(stakeholder_df: pd.DataFrame, output_dir: Path, dpi: int = 300) -> None:
    """利益相关方情感热力图（均值）。"""
    if stakeholder_df.empty:
        print("跳过利益相关方热力图：无数据")
        return
    df = stakeholder_df.copy()
    df["stance_score"] = pd.to_numeric(df["stance_score"], errors="coerce")
    df = df.dropna(subset=["stance_score", "stakeholder"])
    if df.empty:
        print("跳过利益相关方热力图：无有效数据")
        return
    pivoted = df.pivot_table(index="stakeholder", values="stance_score", aggfunc="mean")
    pivoted = pivoted.sort_values(by="stance_score", ascending=False)
    plt.figure(figsize=(6, max(3, 0.5 * len(pivoted))))
    font = get_font()
    ax = sns.heatmap(
        pivoted,
        annot=True,
        fmt=".2f",
        cmap="PiYG",
        center=0,
        cbar_kws={"label": "平均情感 (-2~2)", "shrink": 0.8},
    )
    ax.set_title("利益相关方情感热力图", fontsize=14, fontweight="bold", fontproperties=font)
    ax.set_xlabel("")
    ax.set_ylabel("", fontproperties=font)
    ax.tick_params(axis="x", rotation=0)
    for label in ax.get_yticklabels():
        label.set_fontproperties(font)
    cbar = ax.collections[0].colorbar
    if cbar:
        cbar.ax.set_ylabel("平均情感 (-2~2)", fontproperties=font)
    plt.tight_layout()
    _save_figure(output_dir, "stakeholder_heatmap", dpi=dpi)
    plt.close()


def plot_metric_trends(metric_df: pd.DataFrame, output_dir: Path, year_range: Optional[Tuple[int, int]] = None, dpi: int = 300) -> None:
    """量化指标按年份的趋势折线（仅数值型）。"""
    if metric_df.empty:
        print("跳过量化指标趋势：无数据")
        return
    df = metric_df.copy()
    df["numeric_value"] = df["value"].apply(_to_float)
    df["year"] = df["year"].apply(_as_year)
    df = df.dropna(subset=["numeric_value", "year", "name"])
    if year_range:
        start, end = year_range
        df = df[(df["year"] >= start) & (df["year"] <= end)]
    if df.empty:
        print("跳过量化指标趋势：无可解析数值或有效年份")
        return
    top_metrics = df["name"].value_counts().head(6).index.tolist()
    df = df[df["name"].isin(top_metrics)]
    fig, ax = plt.subplots(figsize=(10, 6))
    font = get_font()
    sns.lineplot(data=df, x="year", y="numeric_value", hue="name", marker="o", ax=ax)
    ax.set_xlabel("年份", fontproperties=font)
    ax.set_ylabel("指标数值", fontproperties=font)
    ax.set_title("主要量化指标趋势（前6项）", fontsize=14, fontweight="bold", fontproperties=font)
    # 设置x轴范围和刻度
    if year_range:
        start, end = year_range
        ax.set_xlim(start, end)
        ax.set_xticks(range(start, end + 1))
        ax.set_xticklabels([str(y) for y in range(start, end + 1)], fontproperties=font, fontsize=9)
    ax.tick_params(axis="x", rotation=45)
    for label in ax.get_yticklabels():
        label.set_fontproperties(font)
    # 设置图例中文
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, labels, title="指标", prop=font, title_fontproperties=font)
    plt.tight_layout()
    _save_figure(output_dir, "metric_trends", dpi=dpi)
    plt.close()


def plot_sector_driver_heatmap(records: List[Dict[str, Any]], output_dir: Path, dpi: int = 300) -> None:
    """行业/场景与驱动类别的共现热力图。"""
    rows = []
    for rec in records:
        sectors = _as_list_of_str(rec.get("sectors"))
        drivers = _as_list_of_dict(rec.get("drivers"))
        for sector in sectors:
            if not str(sector).strip():
                continue
            for driver in drivers:
                rows.append({"sector": sector, "category": driver.get("category")})
    df = pd.DataFrame(rows)
    if df.empty:
        print("跳过行业-驱动热力图：无数据")
        return
    # 统计行业出现次数，只保留前20个高频行业
    sector_counts = df["sector"].value_counts()
    top_sectors = sector_counts.head(20).index.tolist()
    df = df[df["sector"].isin(top_sectors)]
    if df.empty:
        print("跳过行业-驱动热力图：筛选后无数据")
        return
    pivoted = df.pivot_table(index="sector", columns="category", aggfunc="size", fill_value=0)
    pivoted = pivoted.loc[:, sorted(pivoted.columns)]
    # 按行业总数排序
    pivoted["_total"] = pivoted.sum(axis=1)
    pivoted = pivoted.sort_values("_total", ascending=False).drop(columns=["_total"])
    # 调整图片大小
    fig_height = max(6, 0.35 * len(pivoted))
    fig, ax = plt.subplots(figsize=(10, fig_height))
    font = get_font()
    sns.heatmap(
        pivoted,
        cmap="YlGnBu",
        annot=True,
        fmt="d",
        linewidths=0.5,
        linecolor="white",
        cbar_kws={"label": "共现次数", "shrink": 0.8},
        ax=ax,
        annot_kws={"size": 8},
    )
    ax.set_title("行业/场景 × 驱动类别 共现热力图（前20行业）", fontsize=14, fontweight="bold", fontproperties=font)
    ax.set_xlabel("驱动类别", fontproperties=font)
    ax.set_ylabel("行业/场景", fontproperties=font)
    ax.tick_params(axis="x", rotation=45)
    for label in ax.get_yticklabels():
        label.set_fontproperties(font)
        label.set_fontsize(9)
    for label in ax.get_xticklabels():
        label.set_fontproperties(font)
        label.set_fontsize(9)
        label.set_ha('right')
    cbar = ax.collections[0].colorbar
    if cbar:
        cbar.ax.set_ylabel("共现次数", fontproperties=font)
    plt.tight_layout()
    _save_figure(output_dir, "sector_driver_heatmap", dpi=dpi)
    plt.close()


def plot_sector_driver_heatmap_normalized(records: List[Dict[str, Any]], output_dir: Path, dpi: int = 300) -> None:
    """行业/场景 × 驱动类别（行内归一化占比），更适合跨行业对比。"""
    rows = []
    for rec in records:
        sectors = _as_list_of_str(rec.get("sectors"))
        drivers = _as_list_of_dict(rec.get("drivers"))
        for sector in sectors:
            if not str(sector).strip():
                continue
            for driver in drivers:
                rows.append({"sector": sector, "category": driver.get("category")})
    df = pd.DataFrame(rows)
    if df.empty:
        print("跳过行业-驱动归一化热力图：无数据")
        return
    sector_counts = df["sector"].value_counts()
    top_sectors = sector_counts.head(20).index.tolist()
    df = df[df["sector"].isin(top_sectors)]
    if df.empty:
        print("跳过行业-驱动归一化热力图：筛选后无数据")
        return
    pivoted = df.pivot_table(index="sector", columns="category", aggfunc="size", fill_value=0)
    pivoted = pivoted.loc[:, sorted(pivoted.columns)]
    # Row-normalize
    row_sum = pivoted.sum(axis=1).replace(0, np.nan)
    normalized = pivoted.div(row_sum, axis=0).fillna(0)
    normalized["_total"] = pivoted.sum(axis=1)
    normalized = normalized.sort_values("_total", ascending=False).drop(columns=["_total"])

    fig_height = max(6, 0.35 * len(normalized))
    fig, ax = plt.subplots(figsize=(10, fig_height))
    font = get_font()
    sns.heatmap(
        normalized,
        cmap="YlGnBu",
        annot=False,
        linewidths=0.5,
        linecolor="white",
        cbar_kws={"label": "行业内占比", "shrink": 0.8},
        ax=ax,
    )
    ax.set_title("行业/场景 × 驱动类别（行内归一化占比，前20行业）", fontsize=14, fontweight="bold", fontproperties=font)
    ax.set_xlabel("驱动类别", fontproperties=font)
    ax.set_ylabel("行业/场景", fontproperties=font)
    ax.tick_params(axis="x", rotation=45)
    for label in ax.get_yticklabels():
        label.set_fontproperties(font)
        label.set_fontsize(9)
    for label in ax.get_xticklabels():
        label.set_fontproperties(font)
        label.set_fontsize(9)
        label.set_ha("right")
    cbar = ax.collections[0].colorbar
    if cbar:
        cbar.ax.set_ylabel("行业内占比", fontproperties=font)
    plt.tight_layout()
    _save_figure(output_dir, "sector_driver_heatmap_normalized", dpi=dpi)
    plt.close()


def plot_factor_cooccurrence_network(
    records: List[Dict[str, Any]],
    output_dir: Path,
    dpi: int = 300,
    top_factors: int = 30,
    min_edge_weight: int = 3,
) -> None:
    """Factor co-occurrence network (drivers+barriers) to show structural relationships.

    Defensible: edges reflect co-mention within the same record.
    """
    if not NETWORKX_AVAILABLE:
        print("跳过共现网络图：networkx 未安装")
        return

    # Collect factor lists per record
    factor_lists: List[List[str]] = []
    factor_counter: Counter = Counter()
    for rec in records:
        factors = []
        for d in _as_list_of_dict(rec.get("drivers")):
            f = d.get("factor")
            if f:
                factors.append(str(f).strip())
        for b in _as_list_of_dict(rec.get("barriers")):
            f = b.get("factor")
            if f:
                factors.append(str(f).strip())
        factors = [f for f in factors if f]
        if not factors:
            continue
        # Deduplicate within record
        factors = sorted(set(factors))
        factor_lists.append(factors)
        factor_counter.update(factors)

    if not factor_lists:
        print("跳过共现网络图：无因素数据")
        return

    # Focus on top factors for readability
    keep = set([f for f, _ in factor_counter.most_common(top_factors)])
    edge_counter: Counter = Counter()
    for factors in factor_lists:
        kept = [f for f in factors if f in keep]
        if len(kept) < 2:
            continue
        for i in range(len(kept)):
            for j in range(i + 1, len(kept)):
                edge_counter[(kept[i], kept[j])] += 1

    # Build graph
    G = nx.Graph()
    for node, cnt in factor_counter.items():
        if node in keep:
            G.add_node(node, count=int(cnt))
    for (a, b), w in edge_counter.items():
        if w >= min_edge_weight:
            G.add_edge(a, b, weight=int(w))

    if G.number_of_edges() == 0:
        print("跳过共现网络图：边太稀疏（可降低 min_edge_weight）")
        return

    font = get_font()
    plt.figure(figsize=(14, 10))
    # Layout
    pos = nx.spring_layout(G, seed=42, k=0.8)

    counts = np.array([G.nodes[n]["count"] for n in G.nodes])
    counts_ptp = float(np.ptp(counts)) if counts.size else 0.0
    node_sizes = 200 + 1200 * (counts - counts.min()) / (counts_ptp if counts_ptp else 1.0)
    weights = np.array([G.edges[e]["weight"] for e in G.edges])
    weights_ptp = float(np.ptp(weights)) if weights.size else 0.0
    edge_widths = 0.5 + 3.5 * (weights - weights.min()) / (weights_ptp if weights_ptp else 1.0)

    nx.draw_networkx_edges(G, pos, alpha=0.25, width=edge_widths, edge_color="#1f2937")
    nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color="#3b82f6", alpha=0.85, linewidths=0.8, edgecolors="white")

    # Labels: only for top 12 nodes to avoid clutter
    top_label_nodes = [n for n, _ in factor_counter.most_common(12) if n in G.nodes]
    labels = {n: _wrap_label(n, width=10) for n in top_label_nodes}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=9, font_color="#111")

    plt.title(
        f"驱动+阻碍因素共现网络（Top{top_factors}因素；边权≥{min_edge_weight}）",
        fontsize=14,
        fontweight="bold",
        fontproperties=font,
    )
    plt.axis("off")
    _save_figure(output_dir, "factor_cooccurrence_network", dpi=dpi)
    plt.close()


def plot_causal_flow(records: List[Dict[str, Any]], output_dir: Path, dpi: int = 300) -> None:
    """因果链条共现热力图（基于 `A -> B -> C` 的有向边统计），只显示高频边。"""
    edges: Counter = Counter()
    for rec in records:
        chains_value = rec.get("causal_links") or rec.get("causal_chains")
        if not isinstance(chains_value, list):
            continue
        for chain in chains_value:
            nodes: List[str] = []

            if isinstance(chain, str):
                nodes = [p.strip() for p in chain.split("->") if p.strip()]
            elif isinstance(chain, dict):
                chain_val = chain.get("chain")
                if isinstance(chain_val, list):
                    nodes = [str(x).strip() for x in chain_val if str(x).strip()]
                elif isinstance(chain_val, str):
                    nodes = [p.strip() for p in chain_val.split("->") if p.strip()]
                else:
                    # Back-compat: sometimes a dict may have a single string field
                    txt = chain.get("text") or chain.get("causal")
                    if isinstance(txt, str):
                        nodes = [p.strip() for p in txt.split("->") if p.strip()]

            if len(nodes) < 2:
                continue

            for a, b in zip(nodes, nodes[1:]):
                a_short = a[:15] + "..." if len(a) > 15 else a
                b_short = b[:15] + "..." if len(b) > 15 else b
                edges[(a_short, b_short)] += 1
    if not edges:
        print("跳过因果链矩阵：无可用因果链")
        return
    # 只保留出现次数>=2的边，最多显示前30条边
    filtered_edges = {k: v for k, v in edges.items() if v >= 2}
    if not filtered_edges:
        # 如果没有>=2的，取前20条最高频的
        filtered_edges = dict(edges.most_common(20))
    else:
        filtered_edges = dict(Counter(filtered_edges).most_common(30))
    
    if not filtered_edges:
        print("跳过因果链矩阵：无足够高频因果链")
        return
    
    # 收集涉及的节点
    nodes: Set[str] = set()
    for (a, b) in filtered_edges.keys():
        nodes.add(a)
        nodes.add(b)
    nodes_sorted = sorted(nodes)
    
    # 构建矩阵
    index_map = {n: i for i, n in enumerate(nodes_sorted)}
    matrix = np.zeros((len(nodes_sorted), len(nodes_sorted)), dtype=int)
    for (a, b), cnt in filtered_edges.items():
        matrix[index_map[a], index_map[b]] = cnt
    
    # 动态调整图片大小
    n = len(nodes_sorted)
    fig_size = max(8, n * 0.5)
    fig, ax = plt.subplots(figsize=(fig_size, fig_size * 0.8))
    font = get_font()
    
    # 使用更清晰的配色
    sns.heatmap(
        matrix,
        xticklabels=nodes_sorted,
        yticklabels=nodes_sorted,
        cmap="YlOrRd",
        annot=True,
        fmt="d",
        cbar_kws={"label": "因果共现次数", "shrink": 0.6},
        linewidths=0.5,
        linecolor="white",
        ax=ax,
        annot_kws={"size": 8},
        square=True,
    )
    ax.set_title("因果链条共现热力图（高频边）", fontsize=14, fontweight="bold", fontproperties=font)
    ax.set_xlabel("结果节点", fontproperties=font)
    ax.set_ylabel("原因节点", fontproperties=font)
    ax.tick_params(axis="x", rotation=45)
    for label in ax.get_yticklabels():
        label.set_fontproperties(font)
        label.set_fontsize(8)
    for label in ax.get_xticklabels():
        label.set_fontproperties(font)
        label.set_fontsize(8)
        label.set_ha('right')
    cbar = ax.collections[0].colorbar
    if cbar:
        cbar.ax.set_ylabel("因果共现次数", fontproperties=font)
    plt.tight_layout()
    _save_figure(output_dir, "causal_flow_matrix", dpi=dpi)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="基于结构化抽取结果的量化分析与可视化")
    parser.add_argument(
        "--input",
        required=True,
        help="medium_scale_crawler 生成的 structured JSON 或 JSONL 分析表",
    )
    parser.add_argument(
        "--output-dir",
        default="data/output/analysis",
        help="输出目录（默认: data/output/analysis）",
    )
    parser.add_argument("--dpi", type=int, default=300, help="输出图像 DPI（同时输出 PNG + PDF）")
    parser.add_argument(
        "--year-start",
        type=int,
        default=2005,
        help="年份过滤起始（默认与论文口径一致：2005）",
    )
    parser.add_argument(
        "--year-end",
        type=int,
        default=2024,
        help="年份过滤结束（默认与论文口径一致：2024）",
    )
    parser.add_argument(
        "--timeline-count-mode",
        choices=["document", "instance"],
        default="document",
        help="时间线计数口径：document=文献级去重；instance=条目级计数",
    )
    parser.add_argument("--advanced", action="store_true", help="额外输出高级深度图（分布/归一化/网络）")
    parser.add_argument("--network-top", type=int, default=30, help="共现网络保留的 top 因素数")
    parser.add_argument("--network-min-edge", type=int, default=3, help="共现网络最小边权阈值")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(str(args.output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)

    records = load_records(input_path)
    if not records:
        raise SystemExit("未加载到任何记录，请检查输入文件。")

    driver_df = build_driver_df(records)
    barrier_df = build_barrier_df(records)
    stakeholder_df = build_stakeholder_df(records)
    metric_df = build_metric_df(records)

    dpi = int(args.dpi)
    year_range: Tuple[int, int] = (int(args.year_start), int(args.year_end))

    plot_driver_strength(driver_df, output_dir, dpi=dpi)
    plot_barrier_severity(barrier_df, output_dir, dpi=dpi)
    plot_yearly_trend(records, output_dir, dpi=dpi)
    plot_stakeholder_stance(stakeholder_df, output_dir, dpi=dpi)
    plot_metric_counts(metric_df, output_dir, dpi=dpi)
    plot_driver_barrier_heatmap(driver_df, barrier_df, output_dir, dpi=dpi)
    plot_driver_barrier_timeline(
        driver_df,
        barrier_df,
        output_dir,
        year_range=year_range,
        dpi=dpi,
        count_mode=str(args.timeline_count_mode),
    )
    plot_stakeholder_heatmap(stakeholder_df, output_dir, dpi=dpi)
    plot_metric_trends(metric_df, output_dir, year_range=year_range, dpi=dpi)
    plot_sector_driver_heatmap(records, output_dir, dpi=dpi)
    plot_causal_flow(records, output_dir, dpi=dpi)

    if bool(args.advanced):
        plot_category_score_distributions(driver_df, barrier_df, output_dir, dpi=dpi)
        plot_sector_driver_heatmap_normalized(records, output_dir, dpi=dpi)
        plot_factor_cooccurrence_network(
            records,
            output_dir,
            dpi=dpi,
            top_factors=int(args.network_top),
            min_edge_weight=int(args.network_min_edge),
        )

    print(f"✅ 可视化完成，输出目录: {output_dir}")


if __name__ == "__main__":
    main()
