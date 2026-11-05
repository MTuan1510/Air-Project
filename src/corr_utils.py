"""Hàm và hằng số dùng chung cho notebook tương quan thời tiết - AQI (`notebooks/05_weather_correlation.ipynb`).

Dùng lại quy ước của `eda_utils.py` (khoảng chung, ngưỡng 201, mùa, màu) và KHÔNG sửa file đó.
Ý chính của phần này: AQI và thời tiết đều có chu kỳ mùa rất mạnh, nên tương quan thô chủ yếu phản ánh mùa.
Vì vậy mọi kết luận chính đều tính "trong cùng thành phố, cùng tháng" (so với ngày điển hình của tháng đó).
"""
import textwrap

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

from eda_utils import (CITIES, SEASON_ORDER, ACCENT, NEUTRAL, ROOT, FIGS, vn, load, provenance, set_style)  # noqa: F401

WEATHER_FILE = ROOT / "data" / "processed" / "weather_daily_8cities.csv"
WX = ["temp_mean", "humidity_mean", "wind_speed_mean", "blh_mean", "precip_sum", "pressure_mean"]
WX_LABEL = {"temp_mean": "Nhiệt độ TB", "humidity_mean": "Độ ẩm TB", "wind_speed_mean": "Tốc độ gió TB",
            "blh_mean": "Lớp biên khí quyển TB", "precip_sum": "Lượng mưa", "pressure_mean": "Áp suất"}
WX_SHORT = {"temp_mean": "Nhiệt độ", "humidity_mean": "Độ ẩm", "wind_speed_mean": "Gió",
            "blh_mean": "Lớp biên", "precip_sum": "Mưa", "pressure_mean": "Áp suất"}
WX_UNIT = {"temp_mean": "°C", "humidity_mean": "%", "wind_speed_mean": "m/s", "blh_mean": "m",
           "precip_sum": "mm", "pressure_mean": "hPa"}
MIN_HEAVY = 100          # quy ước C1 của notebook 03: chỉ thành phố có từ 100 ngày AQI >= 201 mới đủ để so


# ----------------------------------------------------------------------------- dữ liệu
def load_with_weather(verbose=True):
    """eda_utils.load() rồi ghép 6 biến thời tiết chính. Trả về (eda, win, START, END), mỗi bảng có thêm cột thời tiết."""
    eda, win, start, end = load(verbose=verbose)
    w = pd.read_csv(WEATHER_FILE, parse_dates=["Date"])
    w["City"] = pd.Categorical(w.City, categories=CITIES, ordered=True)
    keep = ["City", "Date"] + WX + ["rain_day", "blh_min"]
    out = []
    for d in (eda, win):
        m = d.merge(w[keep], on=["City", "Date"], how="left", validate="m:1")
        assert len(m) == len(d) and m[WX].notna().all().all(), "ghép thời tiết bị thiếu hoặc đổi số dòng"
        out.append(m)
    return out[0], out[1], start, end


def core_cities(d, min_heavy=MIN_HEAVY):
    """Thành phố có ít nhất `min_heavy` ngày AQI >= 201 (cùng quy ước C1 của notebook 03)."""
    n = d[d.poor].groupby("City", observed=True).size().reindex(CITIES)
    return [c for c in CITIES if n[c] >= min_heavy], n


# ----------------------------------------------------------------------------- bỏ chu kỳ mùa
def add_anomalies(d, cols, base="month"):
    """Thêm cột `<col>_a` = giá trị trừ trung vị cùng thành phố và cùng `base` ("month" hoặc "week").
    Đây là phần bỏ chu kỳ mùa: `_a` cho biết ngày đó cao hay thấp hơn một ngày điển hình của tháng (tuần) ấy."""
    d = d.copy()
    key = d.Date.dt.month if base == "month" else d.Date.dt.isocalendar().week.clip(upper=52).astype(int)
    for c in cols:
        d[c + "_a"] = d[c] - d.groupby(["City", key], observed=True)[c].transform("median")
    return d


def spearman_by_city(d, y="AQI", cols=WX, suffix=""):
    """Bảng Spearman: hàng = thành phố, cột = biến thời tiết. Với suffix="_a" là tương quan sau khi bỏ chu kỳ mùa."""
    return pd.DataFrame({c: {v: g[y + suffix].corr(g[v + suffix], method="spearman") for v in cols}
                         for c, g in d.groupby("City", observed=True)}).T.loc[[c for c in CITIES if c in d.City.unique()]]


# ----------------------------------------------------------------------------- so sánh nhóm (kiểm định giả thuyết, W9)
def tertile_in_strata(d, var):
    """Nhãn thấp/giữa/cao theo tertile của `var` TRONG TỪNG (thành phố, tháng). Mỗi tháng đóng góp như nhau cho cả
    ba nhóm, nên so sánh giữa các nhóm không bị trộn với chu kỳ mùa."""
    def f(s):
        return pd.qcut(s.rank(method="first"), 3, labels=["thấp", "giữa", "cao"])
    lab = d.groupby(["City", d.Date.dt.month], observed=True)[var].transform(lambda s: f(s).astype(str))
    return lab


def block_id(d, days=14):
    """Khối 14 ngày liên tiếp (theo thành phố và năm). Ngày kề nhau giống nhau nên không độc lập: bootstrap theo khối."""
    return d.City.astype(str) + "_" + d.Date.dt.year.astype(str) + "_" + ((d.Date.dt.dayofyear - 1) // days).astype(str)


def boot_median_diff(x1, b1, x2, b2, B=2000, seed=0):
    """Phân phối bootstrap theo KHỐI của (trung vị nhóm 1 - trung vị nhóm 2)."""
    rng = np.random.default_rng(seed)
    blocks = np.unique(np.concatenate([b1, b2]))
    g1 = [x1[b1 == k] for k in blocks]
    g2 = [x2[b2 == k] for k in blocks]
    out = np.empty(B)
    n = len(blocks)
    for i in range(B):
        idx = rng.integers(0, n, n)
        a = np.concatenate([g1[j] for j in idx]); c = np.concatenate([g2[j] for j in idx])
        out[i] = np.median(a) - np.median(c) if len(a) and len(c) else np.nan
    return out[~np.isnan(out)]


def compare_groups(x1, b1, x2, b2, alpha_total=0.05, m_tests=1, B=2000, seed=0):
    """Nhóm 1 = điều kiện bất lợi (gió yếu / lớp biên thấp / không mưa), nhóm 2 = điều kiện thuận lợi.
    Hiệu ứng = trung vị(x1) - trung vị(x2) (điểm AQI); dương = đúng chiều dự đoán.
    Kèm: xác suất vượt trội P(x1 > x2) (từ Mann-Whitney), khoảng tin cậy bootstrap theo khối đã hiệu chỉnh
    Bonferroni cho m_tests phép thử, và p-value Mann-Whitney (giả định độc lập bị vi phạm nên chỉ để tham khảo)."""
    u, p = stats.mannwhitneyu(x1, x2, alternative="two-sided")
    boot = boot_median_diff(x1, b1, x2, b2, B=B, seed=seed)
    a = alpha_total / m_tests
    lo, hi = np.percentile(boot, [100 * a / 2, 100 * (1 - a / 2)])
    return {"n_batloi": len(x1), "n_thuanloi": len(x2), "hieu_ung": np.median(x1) - np.median(x2),
            "ci_lo": lo, "ci_hi": hi, "p_ps": u / (len(x1) * len(x2)), "p_MW": p, "p_MW_bonf": min(1.0, p * m_tests)}


def bh_adjust(p):
    """p-value hiệu chỉnh Benjamini-Hochberg (kiểm soát tỉ lệ phát hiện sai, FDR)."""
    p = np.asarray(p, float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    ranked = p[order] * len(p) / (np.arange(len(p)) + 1)
    adj[order] = np.minimum.accumulate(ranked[::-1])[::-1].clip(max=1.0)
    return adj


def boot_corr(x, y, blocks, B=4000, seed=0):
    """Spearman và khoảng tin cậy 95% bằng bootstrap THEO KHỐI (ngày kề nhau không độc lập, nên p-value công thức
    của Spearman quá lạc quan). Xếp hạng một lần trên toàn mẫu rồi lấy tương quan Pearson của hạng trong từng lần
    lấy mẫu lại (cách làm gần đúng chuẩn, rất nhanh). p_boot = 2 * min(P(rho <= 0), P(rho >= 0)) trên các lần lấy mẫu."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    rx, ry = stats.rankdata(x), stats.rankdata(y)
    ub, inv = np.unique(np.asarray(blocks), return_inverse=True)
    nb = len(ub)
    S = np.zeros((nb, 6))
    np.add.at(S, inv, np.column_stack([np.ones(len(x)), rx, ry, rx * rx, ry * ry, rx * ry]))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, nb, (B, nb))
    cnt = np.zeros((B, nb))
    np.add.at(cnt, (np.arange(B)[:, None], idx), 1)
    n, sx, sy, sxx, syy, sxy = (cnt @ S).T
    with np.errstate(invalid="ignore", divide="ignore"):
        r = (n * sxy - sx * sy) / np.sqrt((n * sxx - sx ** 2) * (n * syy - sy ** 2))
    r = r[np.isfinite(r)]
    rho = stats.spearmanr(x, y)[0]
    lo, hi = np.percentile(r, [2.5, 97.5])
    p = 2 * min((np.sum(r <= 0) + 1) / (len(r) + 1), (np.sum(r >= 0) + 1) / (len(r) + 1))
    return {"rho": rho, "lo": lo, "hi": hi, "p_boot": min(1.0, p)}


def corr_table(d, y="AQI", cols=WX, suffix="_a", B=4000, fdr=0.05):
    """Spearman sau khi bỏ chu kỳ mùa cho từng (thành phố, biến), kèm khoảng tin cậy bootstrap theo khối và
    p-value đã hiệu chỉnh FDR (Benjamini-Hochberg) trên TOÀN BỘ các phép thử trong bảng."""
    d = d.assign(blk=block_id(d))
    rows = []
    for c in [c for c in CITIES if c in d.City.unique()]:
        g = d[d.City == c]
        for v in cols:
            r = boot_corr(g[y + suffix], g[v + suffix], g.blk, B=B)
            rows.append({"City": c, "var": v, **r, "n": len(g)})
    t = pd.DataFrame(rows)
    t["p_fdr"] = bh_adjust(t.p_boot.to_numpy())
    t["sig"] = t.p_fdr < fdr
    return t


# ----------------------------------------------------------------------------- biểu đồ
def finish_chart(fig, ax, title, d, note=""):
    """Tiêu đề kết luận + nguồn (CPCB và Open-Meteo), cỡ mẫu, ngày dữ liệu (W7, W8)."""
    ax.set_title("\n".join(textwrap.wrap(title, 80)), loc="left", fontsize=11, fontweight="bold")
    src = provenance(d) + " Thời tiết: Open-Meteo (ERA5, dữ liệu mô hình)."
    fig.text(0.01, 0.01, "\n".join(textwrap.wrap(src + (" " + note if note else ""), 150)), fontsize=8, color="gray")
    fig.tight_layout(rect=(0, 0.06, 1, 1))


def save_fig(fig, name):
    FIGS.mkdir(parents=True, exist_ok=True)
    path = FIGS / f"corr_{name}.png"
    fig.savefig(path, dpi=150)
    print("Đã lưu", path.relative_to(ROOT))
