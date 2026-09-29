# src/gap_utils.py  (Lucknow + Jaipur - bổ sung cho utils.py của nhóm, KHÔNG sửa utils.py)
import numpy as np
import pandas as pd

AQI_BINS = [0, 50, 100, 200, 300, 400, 10_000]
AQI_LABELS = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]


def gap_runs(s):
    """Độ dài của từng khoảng thiếu liên tiếp trong 1 Series (index là ngày liên tục)."""
    m = s.isna()
    grp = (~m).cumsum()
    runs = m.groupby(grp).sum()
    return runs[runs > 0]


def interpolate_short_gaps(s, max_gap=14):
    """
    Nội suy theo thời gian CHỈ những khoảng thiếu có độ dài <= max_gap ngày
    và nằm giữa 2 giá trị thật. Khoảng dài hơn được giữ NGUYÊN là NaN (toàn bộ khoảng).

    Khác với interpolate(limit=...) của pandas: hàm đó điền `limit` ngày đầu của
    khoảng dài rồi mới dừng, tức là vẫn bịa số bằng đường thẳng nối sang đầu bên kia.
    """
    filled = s.interpolate(method="time", limit_area="inside")
    m = s.isna()
    grp = (~m).cumsum()
    run_len = m.groupby(grp).transform("sum")
    too_long = m & (run_len > max_gap)
    filled[too_long] = np.nan
    return filled


def outlier_flags(s, z_thr=3.0, modz_thr=3.5, iqr_k=1.5):
    """Ba phương pháp toàn cục: Z-score, Modified Z-score (MAD), IQR. Trả về DataFrame bool."""
    x = s.dropna()
    z = (x - x.mean()) / x.std(ddof=0)
    med = x.median()
    mad = (x - med).abs().median()
    modz = 0.6745 * (x - med) / mad if mad > 0 else x * 0
    q1, q3 = x.quantile([0.25, 0.75])
    iqr = q3 - q1
    out = pd.DataFrame(index=s.index)
    out["z"] = (z.abs() > z_thr).reindex(s.index, fill_value=False)
    out["modz"] = (modz.abs() > modz_thr).reindex(s.index, fill_value=False)
    out["iqr"] = ((x < q1 - iqr_k * iqr) | (x > q3 + iqr_k * iqr)).reindex(s.index, fill_value=False)
    return out


def contextual_ratio(s, window=15, min_periods=5):
    """Giá trị / trung vị của các ngày xung quanh (cửa sổ trượt căn giữa, KHÔNG gồm chính nó).
    Phát hiện ngoại lai theo NGỮ CẢNH: cao bất thường so với lân cận, dù chưa cao so với cả chuỗi."""
    neigh = s.rolling(window, center=True, min_periods=min_periods)
    med_incl = neigh.median()
    # bỏ chính điểm đó: tính lại trung vị bằng cách che điểm đó
    vals = s.to_numpy(dtype=float)
    out = np.full(len(s), np.nan)
    half = window // 2
    for i in range(len(s)):
        lo, hi = max(0, i - half), min(len(s), i + half + 1)
        w = np.concatenate([vals[lo:i], vals[i + 1:hi]])
        w = w[~np.isnan(w)]
        if len(w) >= min_periods - 1 and not np.isnan(vals[i]):
            out[i] = vals[i] / np.median(w) if np.median(w) > 0 else np.nan
    return pd.Series(out, index=s.index)


def aqi_bucket(aqi):
    return pd.cut(aqi, bins=AQI_BINS, labels=AQI_LABELS).astype(object)
