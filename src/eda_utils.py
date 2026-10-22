"""Hàm và hằng số dùng chung cho notebook EDA (`notebooks/03_eda.ipynb`).

Mọi biểu đồ trong báo cáo dựa vào file này để thống nhất quy ước (khoảng chung, ngưỡng AQI, mùa, màu).
Đừng sửa nếu chưa báo cả nhóm: một thay đổi ở đây làm đổi biểu đồ của tất cả mọi người.
"""
from pathlib import Path
import textwrap

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "air_quality_8cities.csv"
FIGS = ROOT / "reports" / "figures"

CITIES = ["Delhi", "Gurugram", "Lucknow", "Jaipur", "Bengaluru", "Amritsar", "Chennai", "Hyderabad"]
POOR_AQI = 201                                            # từ mức Poor trở lên (thang CPCB)
SEASON_ORDER = ["Đông (12-2)", "Hè (3-5)", "Mưa (6-9)", "Sau mưa (10-11)"]
USABLE = ["PM2.5", "NO2", "CO", "SO2", "O3"]              # chất đủ dữ liệu ở cả 8 thành phố
ACCENT, NEUTRAL = "#D55E00", "#B0B5BA"                    # một màu nhấn (an toàn cho mù màu), còn lại trung tính


def set_style():
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": False, "figure.dpi": 100})


def vn(x, nd=0):
    """Số kiểu Việt Nam: 1.234,5"""
    return f"{x:,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def season_of(month):
    return ("Đông (12-2)" if month in (12, 1, 2) else "Hè (3-5)" if month in (3, 4, 5)
            else "Mưa (6-9)" if month in (6, 7, 8, 9) else "Sau mưa (10-11)")


def load(verbose=True):
    """Đọc dữ liệu đã làm sạch, thêm year/month/season/poor.
    Trả về (eda, win, COMMON_START, COMMON_END). `win` là khoảng chung của 8 thành phố."""
    eda = pd.read_csv(DATA, parse_dates=["Date"])
    eda["year"] = eda.Date.dt.year
    eda["month"] = eda.Date.dt.month
    eda["season"] = pd.Categorical(eda.month.map(season_of), categories=SEASON_ORDER, ordered=True)
    eda["poor"] = eda.AQI >= POOR_AQI              # NaN AQI -> False; luôn dropna(AQI) trước khi lấy tỉ lệ (xem poor_share)
    eda["City"] = pd.Categorical(eda.City, categories=CITIES, ordered=True)
    assert eda.duplicated(["City", "Date"]).sum() == 0

    start = eda.groupby("City", observed=True).Date.min().max()    # ngày muộn nhất mà mọi thành phố đều đã có dữ liệu
    end = eda.groupby("City", observed=True).Date.max().min()      # ngày sớm nhất mà có thành phố hết dữ liệu
    win = eda[(eda.Date >= start) & (eda.Date <= end)].copy()
    if verbose:
        print(f"Toàn bộ: {vn(len(eda))} dòng, {eda.Date.min():%d/%m/%Y} - {eda.Date.max():%d/%m/%Y}")
        print(f"Khoảng chung (biến win): {start:%d/%m/%Y} - {end:%d/%m/%Y}, {vn(len(win))} dòng; "
              f"{vn(win.AQI.notna().sum())} ngày có AQI")
    return eda, win, start, end


def poor_share(d, by):
    """% ngày AQI >= 201 (trên số ngày CÓ AQI) và số ngày, theo nhóm `by`."""
    g = d.dropna(subset=["AQI"]).groupby(by, observed=True)
    return pd.DataFrame({"pct_poor": (g.poor.mean() * 100).round(1), "n_days": g.size()})


def four_families(d, col="AQI", by="City"):
    """4 họ thống kê (W6) theo nhóm: vị trí (mean, median), phân tán (std, iqr),
    hình dạng (skew), quan hệ (Spearman với PM2.5)."""
    dd = d.dropna(subset=[col])
    g = dd.groupby(by, observed=True)
    out = pd.DataFrame({
        "n": g[col].size(),
        "mean": g[col].mean(), "median": g[col].median(),                           # vị trí
        "std": g[col].std(), "iqr": g[col].quantile(.75) - g[col].quantile(.25),    # phân tán
        "skew": g[col].skew(),                                                      # hình dạng (>0: lệch phải)
    })
    if col != "PM2.5":                                                              # quan hệ
        out["spearman_PM2.5"] = pd.Series({k: x[col].corr(x["PM2.5"], method="spearman")
                                           for k, x in dd.groupby(by, observed=True)})
    return out.round(2)


def provenance(d):
    dd = d.dropna(subset=["AQI"])
    return (f"Nguồn: CPCB qua Kaggle (city_day.csv). n = {vn(len(dd))} ngày có AQI, "
            f"{dd.Date.min():%d/%m/%Y} - {dd.Date.max():%d/%m/%Y}.")


def finish_chart(fig, ax, title, d, note=""):
    """Tiêu đề kết luận + nguồn, cỡ mẫu, ngày dữ liệu (W7, W8)."""
    ax.set_title("\n".join(textwrap.wrap(title, 75)), loc="left", fontsize=11, fontweight="bold")
    fig.text(0.01, 0.01, provenance(d) + (" " + note if note else ""), fontsize=8, color="gray")
    fig.tight_layout(rect=(0, 0.04, 1, 1))


def save_fig(fig, name):
    """Lưu reports/figures/eda_<name>.png"""
    FIGS.mkdir(parents=True, exist_ok=True)
    path = FIGS / f"eda_{name}.png"
    fig.savefig(path, dpi=150)
    print("Đã lưu", path.relative_to(ROOT))
