"""
5G 路测信号数据处理：加载 CSV、筛选与 RSRP 配色。
供看板与单元测试复用。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

# 数据集相对仓库根目录的路径
DEFAULT_CSV_PATH = Path(__file__).resolve().parent / "data" / "signal_samples.csv"

# RSRP 配色规则：> -90 dBm 偏绿，< -110 dBm 偏红，中间线性过渡
RSRP_STRONG_DB = -90.0
RSRP_WEAK_DB = -110.0


def load_signal_data(csv_path: Optional[Path] = None) -> pd.DataFrame:
    """
    使用 pandas 读取标准 5G 模拟数据集。

    Args:
        csv_path: CSV 文件路径；默认读取仓库 data/signal_samples.csv。

    Returns:
        包含 Latitude, Longitude, CellID, Band, RSRP_dBm 等列的 DataFrame。
    """
    path = Path(csv_path) if csv_path is not None else DEFAULT_CSV_PATH
    df = pd.read_csv(path)
    expected = {
        "Latitude",
        "Longitude",
        "CellID",
        "Band",
        "RSRP_dBm",
        "SINR_dB",
        "TerminalType",
        "Download_Mbps",
    }
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"CSV 缺少列: {missing}")
    return df


def rsrp_to_rgba(rsrp: float) -> list[int]:
    """
    将 RSRP (dBm) 映射为 RGBA，用于地图散点/柱体填色。

    规则：强于 -90 dBm 为绿色；弱于 -110 dBm 为红色；其间线性插值。
    """
    strong = RSRP_STRONG_DB
    weak = RSRP_WEAK_DB
    alpha = 220

    if rsrp >= strong:
        return [0, 220, 120, alpha]
    if rsrp <= weak:
        return [255, 55, 65, alpha]

    t = (rsrp - weak) / (strong - weak)
    r = int(255 * (1 - t) + 0 * t)
    g = int(55 * (1 - t) + 220 * t)
    b = int(65 * (1 - t) + 120 * t)
    return [r, g, b, alpha]


def filter_signals(
    df: pd.DataFrame,
    band: Optional[str] = None,
    rsrp_min: float = -130.0,
    rsrp_max: float = -60.0,
) -> pd.DataFrame:
    """
    按频段与 RSRP 范围筛选；band 为 None 或 \"全部\" 时不按频段过滤。
    """
    out = df.copy()
    if band and band != "全部":
        out = out[out["Band"] == band]
    out = out[(out["RSRP_dBm"] >= rsrp_min) & (out["RSRP_dBm"] <= rsrp_max)]
    return out.reset_index(drop=True)


def add_visual_columns(df: pd.DataFrame, elevation_scale: float = 2.5) -> pd.DataFrame:
    """
    为 PyDeck 增加 RGBA 分量列与 3D 柱高（与 Download_Mbps 成正比）。
    """
    vis = df.copy()
    rgba = vis["RSRP_dBm"].astype(float).apply(rsrp_to_rgba)
    vis["color_r"] = rgba.apply(lambda c: c[0])
    vis["color_g"] = rgba.apply(lambda c: c[1])
    vis["color_b"] = rgba.apply(lambda c: c[2])
    vis["color_a"] = rgba.apply(lambda c: c[3])
    # ColumnLayer 的柱高：用下载速率缩放，便于在地图上可见
    vis["bar_elevation"] = vis["Download_Mbps"].astype(float) * elevation_scale
    return vis


def band_cell_counts(df: pd.DataFrame) -> pd.Series:
    """各频段唯一小区数量（按 CellID 去重）。"""
    return df.groupby("Band")["CellID"].nunique()


def terminal_type_ratio(df: pd.DataFrame) -> pd.Series:
    """各终端类型样本占比（行数比例）。"""
    counts = df["TerminalType"].value_counts()
    return counts / counts.sum()
