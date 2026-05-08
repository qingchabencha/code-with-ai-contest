"""signal_processing 模块单元测试。"""

from pathlib import Path

import pandas as pd
import pytest

from signal_processing import (
    RSRP_STRONG_DB,
    RSRP_WEAK_DB,
    add_visual_columns,
    band_cell_counts,
    filter_signals,
    load_signal_data,
    rsrp_to_rgba,
    terminal_type_ratio,
)

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "data"
SAMPLE_CSV = FIXTURE_DIR / "signal_samples.csv"


def test_load_signal_data_reads_csv():
    df = load_signal_data(SAMPLE_CSV)
    assert len(df) > 0
    assert "RSRP_dBm" in df.columns
    assert "Download_Mbps" in df.columns


def test_load_signal_data_missing_file():
    with pytest.raises(FileNotFoundError):
        load_signal_data(Path("/nonexistent/signal_samples.csv"))


def test_rsrp_to_rgba_strong_is_green():
    c = rsrp_to_rgba(RSRP_STRONG_DB + 1)
    assert c[1] > c[0]  # 绿色分量占主导


def test_rsrp_to_rgba_weak_is_red():
    c = rsrp_to_rgba(RSRP_WEAK_DB - 1)
    assert c[0] > c[1]


def test_rsrp_to_rgba_midpoint_interpolates():
    mid = (RSRP_STRONG_DB + RSRP_WEAK_DB) / 2
    c = rsrp_to_rgba(mid)
    assert len(c) == 4 and c[3] == 220


def test_filter_signals_by_band_and_rsrp():
    df = load_signal_data(SAMPLE_CSV)
    sub = filter_signals(df, band="n28", rsrp_min=-100, rsrp_max=-80)
    assert (sub["Band"] == "n28").all()
    assert sub["RSRP_dBm"].between(-100, -80).all()


def test_filter_signals_all_bands():
    df = load_signal_data(SAMPLE_CSV)
    sub = filter_signals(df, band="全部", rsrp_min=-130, rsrp_max=-50)
    assert len(sub) == len(df)


def test_add_visual_columns():
    df = load_signal_data(SAMPLE_CSV).head(10)
    v = add_visual_columns(df, elevation_scale=2.0)
    assert "color_r" in v.columns
    assert "bar_elevation" in v.columns
    assert (v["bar_elevation"] == v["Download_Mbps"] * 2.0).all()


def test_band_cell_counts_and_terminal_ratio():
    df = load_signal_data(SAMPLE_CSV)
    bc = band_cell_counts(df)
    assert bc.sum() >= len(bc)
    tr = terminal_type_ratio(df)
    assert pytest.approx(tr.sum(), rel=1e-9) == 1.0
