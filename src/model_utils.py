"""Hàm và hằng số dùng chung cho notebook dự đoán AQI ngày mai (`notebooks/06_predict_aqi.ipynb`).

Dùng lại quy ước của `eda_utils.py` (khoảng chung, ngưỡng 201, mùa, màu) và `corr_utils.py` (6 biến thời tiết chính);
KHÔNG sửa hai file đó.

Nguyên tắc của phần này (W10, W11):
  * Một dòng = một (thành phố, ngày hôm nay t). Mục tiêu = AQI của ngày t+1. Mọi đặc trưng chỉ dùng thông tin đến hết ngày t.
  * Chia theo THỜI GIAN (theo ngày được dự đoán), không chia ngẫu nhiên. Test chỉ mở một lần, ở cuối.
  * Mọi thứ có học tham số (imputer, scaler, encoder, mô hình) nằm trong Pipeline và chỉ fit trên train.
  * Ô chất ô nhiễm đã NỘI SUY ở bước làm sạch bị đặt lại thành NaN khi làm đặc trưng: nội suy dùng giá trị của các ngày SAU,
    nên đưa vào đặc trưng của ngày t là để tương lai lọt vào quá khứ (rò rỉ nhẹ). Có kiểm tra độ nhạy ở notebook.
"""
import textwrap

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from eda_utils import (CITIES, POOR_AQI, USABLE, ACCENT, NEUTRAL, ROOT, FIGS, vn, load, provenance, set_style)  # noqa: F401
from corr_utils import WX, WX_SHORT, WX_LABEL, WX_UNIT, WEATHER_FILE, block_id, add_anomalies  # noqa: F401

# ----------------------------------------------------------------------------- quy ước chia dữ liệu
# Chia theo NGÀY ĐƯỢC DỰ ĐOÁN (t+1). Khoảng chung của 8 thành phố bắt đầu 14/06/2017 (Jaipur).
TRAIN_END = pd.Timestamp("2019-06-30")           # train: ngày được dự đoán đến hết 30/06/2019
TEST_START = pd.Timestamp("2019-07-01")          # test:  01/07/2019 - 29/02/2020 (trọn một mùa đông)
TEST_END = pd.Timestamp("2020-02-29")
LOCK_START = pd.Timestamp("2020-03-01")          # 03-07/2020: phong toả COVID-19, tách riêng, không dùng để chọn gì
TS_SPLITS = 4                                    # số lần chia TimeSeriesSplit bên trong train
GAP_ROWS = 16                                    # bỏ 16 dòng (~2 ngày x 8 thành phố) giữa train và validation trong mỗi lần chia

# ----------------------------------------------------------------------------- nhóm đặc trưng
CAL_FEATS = ["doy_sin", "doy_cos"]                                        # ngày trong năm của NGÀY ĐƯỢC DỰ ĐOÁN (biết trước)
AQI_FEATS = ["aqi_0", "aqi_1", "aqi_2", "aqi_wk"]                         # log AQI hôm nay, hôm qua, hôm kia, trung bình 7 ngày trước
POLL_FEATS = ["pm25_0", "no2_0", "co_0", "so2_0", "o3_0"]                 # log(1 + nồng độ) hôm nay
WEATHER_FEATS = ["temp_mean", "humidity_mean", "pressure_dev", "d_pressure", "wind_speed_mean", "wind_u", "wind_v",
                 "blh_mean", "precip_log"]                               # thời tiết đến hết hôm nay
NEXT_FEATS = [f + "_next" for f in WEATHER_FEATS]                         # thời tiết NGÀY MAI: chỉ cho kịch bản cận trên
LEVELS = {
    "L1": AQI_FEATS + CAL_FEATS,
    "L2": AQI_FEATS + CAL_FEATS + POLL_FEATS,
    "L3": AQI_FEATS + CAL_FEATS + POLL_FEATS + WEATHER_FEATS,
    "L4": AQI_FEATS + CAL_FEATS + POLL_FEATS + WEATHER_FEATS + NEXT_FEATS,
}
LEVEL_NAME = {"L1": "Mức 1: chỉ AQI các ngày trước", "L2": "Mức 2: + chất ô nhiễm hôm nay", "L3": "Mức 3: + thời tiết đến hôm nay",
              "L4": "Cận trên: + thời tiết ngày mai (dự báo hoàn hảo)"}
FEAT_LABEL = {
    "aqi_0": "log AQI hôm nay", "aqi_1": "log AQI hôm qua", "aqi_2": "log AQI hôm kia", "aqi_wk": "log AQI trung bình 7 ngày trước",
    "doy_sin": "mùa (sin)", "doy_cos": "mùa (cos)",
    "pm25_0": "log(1+PM2.5) hôm nay", "no2_0": "log(1+NO2) hôm nay", "co_0": "log(1+CO) hôm nay",
    "so2_0": "log(1+SO2) hôm nay", "o3_0": "log(1+O3) hôm nay",
    "temp_mean": "nhiệt độ TB (°C)", "humidity_mean": "độ ẩm TB (%)", "pressure_dev": "áp suất lệch so với TB 30 ngày trước (hPa)",
    "d_pressure": "đổi áp suất so với hôm qua (hPa)", "wind_speed_mean": "tốc độ gió TB (m/s)",
    "wind_u": "gió hướng Đông (m/s)", "wind_v": "gió hướng Bắc (m/s)", "blh_mean": "lớp biên TB (m)", "precip_log": "log(1+mưa mm)",
}
FEAT_UNIT = {"temp_mean": "°C", "humidity_mean": "điểm %", "pressure_dev": "hPa", "d_pressure": "hPa", "wind_speed_mean": "m/s",
             "wind_u": "m/s", "wind_v": "m/s", "blh_mean": "100 m"}


# ----------------------------------------------------------------------------- dựng bảng dữ liệu
def make_features(mask_interp=True, as_of=None):
    """Toàn bộ đặc trưng và mục tiêu, MỌI dòng (chưa lọc). Dùng `build_dataset` để có bảng sẵn sàng cho mô hình.

    as_of: nếu cho một ngày, mọi dữ liệu SAU ngày đó bị bỏ trước khi tính đặc trưng. So đặc trưng của ngày as_of giữa bản
    cắt và bản đầy đủ là phép thử rò rỉ trực tiếp: đặc trưng hợp lệ thì hai bản phải giống hệt nhau.
    mask_interp=True: ô chất ô nhiễm đã nội suy ở bước làm sạch bị đặt lại NaN (xem docstring đầu file), rồi điền lùi theo thời gian
    tối đa 2 ngày (chỉ dùng quá khứ). Phần còn thiếu được điền trung vị của TRAIN bên trong Pipeline, kèm cột báo thiếu.
    """
    eda, _, _, _ = load(verbose=False)
    w = pd.read_csv(WEATHER_FILE, parse_dates=["Date"])
    if as_of is not None:
        eda, w = eda[eda.Date <= as_of], w[w.Date <= as_of]
    d = eda.merge(w.drop(columns=["wind_dir_8", "rain_day", "blh_min", "temp_min", "temp_max", "wind_speed_max"]),
                  on=["City", "Date"], how="left", validate="m:1")
    d["City"] = d.City.astype(str)
    d = d.sort_values(["City", "Date"]).reset_index(drop=True)
    assert (d.groupby("City").Date.diff().dropna() == pd.Timedelta("1D")).all(), "chuỗi ngày bị đứt: shift theo dòng sẽ sai"
    assert d.AQI.dropna().gt(0).all()
    g = d.groupby("City", sort=False)

    d["aqi_next"] = g.AQI.shift(-1)
    la = np.log(d.AQI)
    d["aqi_0"] = la
    d["aqi_1"] = la.groupby(d.City).shift(1)
    d["aqi_2"] = la.groupby(d.City).shift(2)
    wk = g.AQI.transform(lambda s: s.shift(1).rolling(7, min_periods=3).mean())      # trung bình 7 ngày TRƯỚC hôm nay
    d["aqi_wk"] = np.log(wk)

    for p, name in zip(USABLE, ["pm25_0", "no2_0", "co_0", "so2_0", "o3_0"]):
        x = d[p]
        if mask_interp:
            x = x.where(~(d[f"{p}_was_missing"] & d[p].notna()))
            x = x.groupby(d.City).ffill(limit=2)                                       # chỉ nhìn về quá khứ
        d[name] = np.log1p(x)

    d["d_pressure"] = d.pressure_mean - d.groupby("City").pressure_mean.shift(1)
    # áp suất tuyệt đối gần như là "tên thành phố" (Bengaluru cao 914 m nên thấp hơn hẳn) và có chu kỳ mùa riêng:
    # dùng độ lệch so với trung bình 30 ngày TRƯỚC hôm nay của chính thành phố (chỉ nhìn quá khứ, không học tham số nào)
    d["pressure_dev"] = d.pressure_mean - d.groupby("City").pressure_mean.transform(lambda s: s.shift(1).rolling(30, min_periods=10).mean())
    d["precip_log"] = np.log1p(d.precip_sum)
    for f in WEATHER_FEATS:
        d[f + "_next"] = d.groupby("City")[f].shift(-1)

    d["Date_target"] = d.Date + pd.Timedelta(days=1)
    doy = d.Date_target.dt.dayofyear
    d["doy_sin"], d["doy_cos"] = np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)

    d["y"] = d.aqi_next
    d["y_log"] = np.log(d.y)
    d["y_poor"] = d.y >= POOR_AQI
    d["today_poor"] = d.AQI >= POOR_AQI
    d["split"] = np.select([d.Date_target <= TRAIN_END, (d.Date_target >= TEST_START) & (d.Date_target <= TEST_END),
                            d.Date_target >= LOCK_START], ["train", "test", "lockdown"], default="other")
    return d


def build_dataset(mask_interp=True, verbose=True):
    """Bảng (thành phố, ngày hôm nay t) -> AQI ngày t+1, kèm đặc trưng. Chỉ giữ dòng có CẢ AQI(t) và AQI(t+1), trong khoảng chung
    của 8 thành phố, sắp theo ngày được dự đoán (thứ tự thời gian: bắt buộc cho TimeSeriesSplit)."""
    _, _, start, end = load(verbose=False)
    d = make_features(mask_interp=mask_interp)
    keep = d.AQI.notna() & d.y.notna() & (d.Date >= start) & (d.Date_target <= end)
    out = d[keep].sort_values(["Date_target", "City"]).reset_index(drop=True)
    out["City"] = pd.Categorical(out.City, categories=CITIES, ordered=True)
    if verbose:
        print(out.groupby("split").agg(dong=("y", "size"), ngay_nang=("y_poor", "sum"), tu=("Date_target", "min"), den=("Date_target", "max")))
    return out


# ----------------------------------------------------------------------------- mô hình
def make_pipe(feats, model="ridge", alpha=1.0, seed=42, **kw):
    """Pipeline hoàn chỉnh: điền thiếu (trung vị train, kèm cột báo thiếu) -> scale -> mã hoá thành phố -> mô hình."""
    num = Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)), ("sc", StandardScaler())])
    cat = OneHotEncoder(categories=[CITIES], drop="first", handle_unknown="ignore", sparse_output=False)   # Delhi là mức tham chiếu
    prep = ColumnTransformer([("num", num, list(feats)), ("city", cat, ["City"])], verbose_feature_names_out=False)
    if model == "ridge":
        m = Ridge(alpha=alpha)
    elif model == "hgb":
        m = HistGradientBoostingRegressor(random_state=seed, **kw)
    else:
        raise ValueError(model)
    return Pipeline([("prep", prep), ("model", m)])


def time_cv(n):
    return TimeSeriesSplit(n_splits=TS_SPLITS, gap=GAP_ROWS)


def mae(y, p):
    return float(np.mean(np.abs(np.asarray(y) - np.asarray(p))))


def rmse(y, p):
    return float(np.sqrt(np.mean((np.asarray(y) - np.asarray(p)) ** 2)))


def cv_score(tr, feats, make, target="y_log", back=np.exp):
    """MAE (điểm AQI) trung bình qua các lần chia TimeSeriesSplit trong train. `make()` trả về một Pipeline mới."""
    errs = []
    for a, b in time_cv(len(tr)).split(tr):
        m = make().fit(tr.iloc[a][feats + ["City"]], tr.iloc[a][target])
        errs.append(mae(tr.iloc[b].y, back(m.predict(tr.iloc[b][feats + ["City"]]))))
    return float(np.mean(errs)), float(np.std(errs))


def oof_predict(tr, feats, make, target="y_log", back=np.exp):
    """Dự đoán 'ngoài mẫu' cho các dòng validation của TimeSeriesSplit (dùng chọn ngưỡng, không đụng tới test).
    Trả về (chỉ số dòng, dự đoán theo điểm AQI)."""
    idx, pred = [], []
    for a, b in time_cv(len(tr)).split(tr):
        m = make().fit(tr.iloc[a][feats + ["City"]], tr.iloc[a][target])
        idx.append(b); pred.append(back(m.predict(tr.iloc[b][feats + ["City"]])))
    return np.concatenate(idx), np.concatenate(pred)


def r2(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    return float(1 - ((y - p) ** 2).sum() / ((y - y.mean()) ** 2).sum())


def baseline_preds(fit, new):
    """Ba baseline đơn giản, học trên `fit` (train hoặc phần train của một lần chia), dự đoán cho `new`:
    trung bình theo thành phố; trung vị cùng thành phố và cùng tháng của NGÀY ĐƯỢC DỰ ĐOÁN (khí hậu); 'ngày mai = hôm nay'."""
    c_fit, c_new = fit.City.astype(str), new.City.astype(str)
    mean_city = fit.groupby(c_fit).y.mean()
    med_city = fit.groupby(c_fit).y.median()
    clim = fit.groupby([c_fit, fit.Date_target.dt.month]).y.median()
    p_clim = [clim.get((c, m), med_city[c]) for c, m in zip(c_new, new.Date_target.dt.month)]
    return {"Trung bình theo thành phố": c_new.map(mean_city).to_numpy(float),
            "Trung vị cùng tháng (khí hậu)": np.array(p_clim, float),
            "Ngày mai = hôm nay": new.AQI.to_numpy(float)}


def design_matrix(d, feats):
    """Ma trận thiết kế cho statsmodels: đặc trưng + biến giả thành phố (Delhi là mức tham chiếu) + hằng số."""
    dummies = pd.get_dummies(d.City.astype(str)).reindex(columns=CITIES[1:], fill_value=0).astype(float)
    return sm.add_constant(pd.concat([d[list(feats)].reset_index(drop=True), dummies.reset_index(drop=True)], axis=1))


# ----------------------------------------------------------------------------- diễn giải hệ số (W10: mỗi hệ số một câu)
FEAT_PLAIN = {"aqi_0": "AQI hôm nay", "aqi_1": "AQI hôm qua", "aqi_2": "AQI hôm kia", "aqi_wk": "AQI trung bình 7 ngày trước",
              "pm25_0": "PM2.5 hôm nay", "no2_0": "NO2 hôm nay", "co_0": "CO hôm nay", "so2_0": "SO2 hôm nay", "o3_0": "O3 hôm nay",
              "temp_mean": "nhiệt độ trung bình", "humidity_mean": "độ ẩm trung bình", "pressure_dev": "áp suất (lệch so với trung bình 30 ngày trước)",
              "d_pressure": "mức đổi áp suất so với hôm qua", "wind_speed_mean": "tốc độ gió trung bình",
              "wind_u": "thành phần gió hướng Đông", "wind_v": "thành phần gió hướng Bắc", "blh_mean": "chiều cao lớp biên khí quyển"}
POLL_UNIT = {"pm25_0": "µg/m³", "no2_0": "µg/m³", "co_0": "mg/m³", "so2_0": "µg/m³", "o3_0": "µg/m³"}
STEP = {"temp_mean": (1, "°C"), "humidity_mean": (10, "điểm %"), "pressure_dev": (5, "hPa"), "d_pressure": (1, "hPa"),
        "wind_speed_mean": (1, "m/s"), "wind_u": (1, "m/s"), "wind_v": (1, "m/s"), "blh_mean": (100, "m")}


def _pct(x, nd=1):
    if round(x, nd) == 0:
        return vn(0, nd) + "%"
    return ("+" if x > 0 else "−") + vn(abs(x), nd) + "%"


def _n(x, nd=1):
    """Số kiểu Việt Nam, dấu trừ là '−'."""
    return vn(x, nd).replace("-", "−")


def coef_table(res, d, feats):
    """Bảng hệ số và MỘT CÂU diễn giải cho mỗi hệ số (đúng mẫu W10: 'đi cùng với', giữ các biến khác, đơn vị, khoảng đã quan sát).
    `res`: kết quả OLS trên log AQI ngày mai (nên dùng sai số chuẩn bền); `d`: dữ liệu đã dùng để fit, để lấy khoảng quan sát."""
    ci = res.conf_int()
    rows = []
    hold = "giữ các biến còn lại trong mô hình không đổi"
    for f in feats:
        b, lo, hi = res.params[f], ci.loc[f, 0], ci.loc[f, 1]
        mn, mx = d[f].min(), d[f].max()
        if f in ("doy_sin", "doy_cos"):
            continue
        if f.startswith("aqi_"):
            fx = lambda v: (1.1 ** v - 1) * 100
            s = (f"Khi {FEAT_PLAIN[f]} cao hơn 10%, AQI ngày mai đi cùng với {_pct(fx(b))} ({_pct(fx(lo))} đến {_pct(fx(hi))}, KTC 95%), {hold}; "
                 f"chỉ trong khoảng AQI đã quan sát {vn(np.exp(mn))} đến {vn(np.exp(mx))}.")
        elif f in POLL_UNIT:
            fx = lambda v: (1.1 ** v - 1) * 100
            s = (f"Khi {FEAT_PLAIN[f]} cao hơn 10% (tính trên 1 + nồng độ), AQI ngày mai đi cùng với {_pct(fx(b))} ({_pct(fx(lo))} đến {_pct(fx(hi))}, KTC 95%), "
                 f"{hold}; chỉ trong khoảng đã quan sát {vn(np.expm1(mn), 1)} đến {vn(np.expm1(mx), 1)} {POLL_UNIT[f]}.")
        elif f == "precip_log":
            k = np.log1p(10)
            fx = lambda v: (np.exp(v * k) - 1) * 100
            s = (f"Ngày có 10 mm mưa so với ngày không mưa, AQI ngày mai đi cùng với {_pct(fx(b))} ({_pct(fx(lo))} đến {_pct(fx(hi))}, KTC 95%), {hold}; "
                 f"chỉ trong khoảng mưa đã quan sát 0 đến {vn(np.expm1(mx), 0)} mm.")
        else:
            k, u = STEP[f]
            fx = lambda v: (np.exp(v * k) - 1) * 100
            s = (f"Mỗi tăng {k} {u} của {FEAT_PLAIN[f]}, AQI ngày mai đi cùng với {_pct(fx(b))} ({_pct(fx(lo))} đến {_pct(fx(hi))}, KTC 95%), {hold}; "
                 f"chỉ trong khoảng đã quan sát {_n(mn, 1)} đến {_n(mx, 1)} {u}.")
        rows.append({"biến": f, "β (log AQI)": b, "KTC 95% thấp": lo, "KTC 95% cao": hi, "p (khối)": res.pvalues[f], "diễn giải": s})
    if "doy_sin" in feats:
        a = float(np.hypot(res.params["doy_sin"], res.params["doy_cos"]))
        pj = float(res.wald_test("doy_sin = 0, doy_cos = 0", scalar=True).pvalue)
        rows.append({"biến": "mùa (sin, cos)", "β (log AQI)": a, "KTC 95% thấp": np.nan, "KTC 95% cao": np.nan, "p (khối)": pj,
                     "diễn giải": f"Sau khi giữ các biến còn lại không đổi, hai biến mùa còn cho AQI ngày mai dao động theo mùa với biên độ ±{vn((np.exp(a) - 1) * 100, 1)}% "
                                  f"(đọc hai hệ số sin và cos CHUNG; kiểm định chung hai hệ số {('p < 0,001' if pj < 0.001 else 'p = ' + vn(pj, 3))})."})
    for c in CITIES[1:]:
        b, lo, hi = res.params[c], ci.loc[c, 0], ci.loc[c, 1]
        fx = lambda v: (np.exp(v) - 1) * 100
        word = "thấp hơn" if b < 0 else "cao hơn"
        rows.append({"biến": c, "β (log AQI)": b, "KTC 95% thấp": lo, "KTC 95% cao": hi, "p (khối)": res.pvalues[c],
                     "diễn giải": f"So với Delhi (mức tham chiếu), {c} đi cùng với AQI ngày mai {word} khoảng {vn(abs(fx(b)), 1)}% ({_pct(fx(lo))} đến {_pct(fx(hi))}, KTC 95%), {hold}."})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- cảnh báo (W11)
def alert_counts(y_true, flag):
    y_true, flag = np.asarray(y_true, bool), np.asarray(flag, bool)
    tp, fp, fn, tn = int((y_true & flag).sum()), int((~y_true & flag).sum()), int((y_true & ~flag).sum()), int((~y_true & ~flag).sum())
    return tp, fp, fn, tn


def alert_metrics(y_true, flag):
    tp, fp, fn, tn = alert_counts(y_true, flag)
    rec = tp / (tp + fn) if tp + fn else np.nan
    pre = tp / (tp + fp) if tp + fp else np.nan
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else np.nan
    return {"recall": rec, "precision": pre, "F1": f1, "TP": tp, "FP": fp, "FN": fn, "TN": tn, "n_canh_bao": tp + fp}


def f_beta(y_true, flag, beta=2.0):
    tp, fp, fn, _ = alert_counts(y_true, flag)
    den = (1 + beta ** 2) * tp + beta ** 2 * fn + fp
    return (1 + beta ** 2) * tp / den if den else 0.0


def best_threshold(y_true, score, beta=2.0, grid=None):
    """Ngưỡng trên giá trị dự đoán làm F-beta lớn nhất (chọn trên validation, KHÔNG phải test)."""
    grid = np.arange(80, 301, 1) if grid is None else grid
    vals = np.array([f_beta(y_true, score >= t, beta) for t in grid])
    return float(grid[int(np.argmax(vals))]), float(vals.max())


# ----------------------------------------------------------------------------- bootstrap theo khối
def calendar_blocks(dates, days=14):
    """Khối 14 ngày LỊCH (dùng chung cho mọi thành phố): ngày kề nhau và các thành phố cùng ngày đều không độc lập."""
    return ((pd.Series(dates).reset_index(drop=True) - pd.Series(dates).min()).dt.days // days).to_numpy()


def block_boot(blocks, S, stat, B=4000, seed=0):
    """Bootstrap theo khối. S: ma trận (n_dòng, k) các đại lượng CỘNG ĐƯỢC theo dòng (ví dụ |sai số|, TP, FP, FN, 1).
    stat: hàm nhận (B, k) tổng theo khối đã lấy mẫu lại và trả (B,) giá trị thống kê. Trả về (ước lượng gốc, lo, hi) 95%."""
    S = np.asarray(S, float)
    ub, inv = np.unique(np.asarray(blocks), return_inverse=True)
    nb = len(ub)
    agg = np.zeros((nb, S.shape[1]))
    np.add.at(agg, inv, S)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, nb, (B, nb))
    cnt = np.zeros((B, nb))
    np.add.at(cnt, (np.arange(B)[:, None], idx), 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        boot = stat(cnt @ agg)
        point = stat(agg.sum(0, keepdims=True))[0]
    boot = boot[np.isfinite(boot)]
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return float(point), float(lo), float(hi)


def boot_mae_diff(blocks, err_a, err_b, B=4000, seed=0):
    """MAE(a) - MAE(b) với khoảng tin cậy 95% theo khối. Âm = a tốt hơn b."""
    S = np.column_stack([err_a, err_b, np.ones(len(err_a))])
    return block_boot(blocks, S, lambda s: (s[:, 0] - s[:, 1]) / s[:, 2], B=B, seed=seed)


def boot_alert_diff(blocks, y_true, flag_a, flag_b, metric="recall", B=4000, seed=0):
    """metric(a) - metric(b) cho recall / precision / F1, khoảng tin cậy 95% theo khối. Dương = a tốt hơn b."""
    y = np.asarray(y_true, bool)
    cols = []
    for f in (np.asarray(flag_a, bool), np.asarray(flag_b, bool)):
        cols += [y & f, ~y & f, y & ~f]
    S = np.column_stack(cols).astype(float)

    def one(tp, fp, fn):
        if metric == "recall":
            return tp / (tp + fn)
        if metric == "precision":
            return tp / (tp + fp)
        return 2 * tp / (2 * tp + fp + fn)
    return block_boot(blocks, S, lambda s: one(s[:, 0], s[:, 1], s[:, 2]) - one(s[:, 3], s[:, 4], s[:, 5]), B=B, seed=seed)


def boot_alert_ci(blocks, y_true, flag, metric="recall", B=4000, seed=0):
    y = np.asarray(y_true, bool); f = np.asarray(flag, bool)
    S = np.column_stack([y & f, ~y & f, y & ~f]).astype(float)

    def one(s):
        tp, fp, fn = s[:, 0], s[:, 1], s[:, 2]
        return tp / (tp + fn) if metric == "recall" else tp / (tp + fp) if metric == "precision" else 2 * tp / (2 * tp + fp + fn)
    return block_boot(blocks, S, one, B=B, seed=seed)


# ----------------------------------------------------------------------------- biểu đồ
def finish_chart(fig, ax, title, d, note=""):
    """Tiêu đề kết luận + nguồn (CPCB và Open-Meteo), cỡ mẫu, ngày dữ liệu (W7, W8). `d` có cột Date_target (bảng mô hình) hoặc Date."""
    col, what = ("Date_target", "ngày được dự đoán") if "Date_target" in d.columns else ("Date", "ngày")
    ax.set_title("\n".join(textwrap.wrap(title, 80)), loc="left", fontsize=11, fontweight="bold")
    src = (f"Nguồn: CPCB qua Kaggle (city_day.csv) và Open-Meteo (ERA5, dữ liệu mô hình). n = {vn(len(d))} cặp (thành phố, ngày), "
           f"{what} {d[col].min():%d/%m/%Y} - {d[col].max():%d/%m/%Y}.")
    fig.text(0.01, 0.01, "\n".join(textwrap.wrap(src + (" " + note if note else ""), 150)), fontsize=8, color="gray")
    fig.tight_layout(rect=(0, 0.06, 1, 1))


def save_fig(fig, name):
    FIGS.mkdir(parents=True, exist_ok=True)
    path = FIGS / f"model_{name}.png"
    fig.savefig(path, dpi=150)
    print("Đã lưu", path.relative_to(ROOT))
