# src/pipeline.py — pipeline làm sạch dùng chung cho cả 8 thành phố (raw -> air_quality_8cities.csv)
#
# Gom lại logic trước đây nằm rải ở notebook 01-07:
#   missing  : utils.impute_time_series (flatline 0 -> NaN, nội suy khoảng <= 14 ngày, giữ cờ *_was_missing)
#   nghi lỗi : luật điều tra điểm lớn nhất của PM2.5 và AQI (trước đây ở notebook 02, EX4.2, và 07 bước 3)
#   outlier  : utils.flag_outliers_iqr (IQR theo từng tháng, chỉ đánh dấu)
#   gộp      : cùng một bộ cột cho 8 thành phố
import numpy as np
import pandas as pd

from utils import (impute_time_series, flag_outliers_iqr, load_and_split_city)
from gap_utils import contextual_ratio

CITIES = ["Delhi", "Gurugram", "Lucknow", "Jaipur",
          "Bengaluru", "Amritsar", "Chennai", "Hyderabad"]

# 11 chất sau khi bỏ Xylene (quyết định chung: Xylene thiếu 100% ở 4/8 thành phố)
POLLUTANTS = ["PM2.5", "PM10", "NO", "NO2", "NOx", "NH3",
              "CO", "SO2", "O3", "Benzene", "Toluene"]
GASES = ["PM10", "NO", "NO2", "NOx", "CO", "SO2", "O3", "Benzene", "Toluene", "NH3"]

PM_RATIO = 1.2          # PM2.5 > 1,2 x PM10 thì coi là vô lý (PM10 đã gồm cả PM2.5)
MISSING_MAX_PCT = 60    # cột (trong 1 thành phố) thiếu < 60% thì còn dùng được làm biến
MAX_GAP = 14            # chỉ nội suy khoảng thiếu <= 14 ngày
CTX_THR = 2.5           # ngưỡng "ngữ cảnh"
WINTER = {10, 11, 12, 1, 2}


# ---------------------------------------------------------------- điểm nghi lỗi cảm biến
def investigate(d, col, top=5, skip_pm25=(), extra_dates=()):
    """Điều tra các điểm lớn nhất của `col` bằng 4 bằng chứng. d: DataFrame có index là Date.
    Trả về bảng bằng chứng kèm cột `suggestion` ("NGHI LOI ..." / "that ..." / "chua ro ...")."""
    ratio = contextual_ratio(d[col])
    others = [g for g in GASES if g in d.columns and d[g].notna().any()]
    R = pd.DataFrame({g: contextual_ratio(d[g]) for g in others})
    has10 = "PM10" in d.columns and d["PM10"].notna().any()
    pm25_r = contextual_ratio(d["PM2.5"])
    pm10_r = contextual_ratio(d["PM10"]) if has10 else pd.Series(np.nan, index=d.index)
    skip = set(skip_pm25)
    for t in skip:
        pm25_r[t] = np.nan                      # điểm PM2.5 đã nghi lỗi thì không dùng làm bằng chứng
    dates = list(d[col].nlargest(top).index)
    dates += [t for t in extra_dates if t in d.index and d.loc[t, col] == d.loc[t, col] and t not in dates]
    rows = []
    for t in dates:
        co = [g for g in others if R.loc[t, g] >= 1.5]
        pm10_ok = has10 and pm10_r[t] == pm10_r[t] and pm10_r[t] >= 1.5
        expl = (col == "AQI") and (pm10_ok or (np.nan_to_num(pm25_r[t], nan=-1) >= 1.5))
        p_ratio = d.loc[t, "PM2.5"] / d.loc[t, "PM10"] if has10 and d.loc[t, "PM10"] > 0 else np.nan
        winter = t.month in WINTER
        if col == "AQI" and t in skip and not pm10_ok:                  goi_y = "NGHI LOI (theo PM2.5 nghi loi cung ngay)"
        elif col == "PM2.5" and p_ratio == p_ratio and p_ratio > 1.5:   goi_y = "NGHI LOI (PM2.5 > 1,5 x PM10)"
        elif winter and ratio[t] < 3:                                   goi_y = "that (mua cao diem)"
        elif expl or len(co) >= 3:                                      goi_y = "that (chat khac cung tang)"
        elif (not winter) and ratio[t] >= 4:                            goi_y = "NGHI LOI (co lap, trai mua)"
        else:                                                           goi_y = "chua ro -> giu + co"
        rows.append(dict(date=t, column=col, value_original=round(d.loc[t, col], 1),
                         gap_vs_neighbors=round(ratio[t], 1), month=t.month,
                         pm25_div_pm10=round(p_ratio, 2) if p_ratio == p_ratio else np.nan,
                         other_gases_up=f"{len(co)}/{R.loc[t].notna().sum()}", suggestion=goi_y))
    return pd.DataFrame(rows)


def run_rule(d):
    """PM2.5 trước, rồi AQI (kèm các ngày PM2.5 nghi lỗi). Trả về bảng bằng chứng."""
    r25 = investigate(d, "PM2.5")
    sus = [t for t in r25.loc[r25.suggestion.str.startswith("NGHI"), "date"]]
    rq = investigate(d, "AQI", skip_pm25=sus, extra_dates=sus)
    return pd.concat([r25, rq], ignore_index=True)


def apply_suspect_rule(df):
    """Áp luật nghi lỗi: điểm 'NGHI LOI' -> NaN (không nội suy), gắn `suspect_sensor_error`.
    df có cột Date. Trả về (df mới, bảng bằng chứng với cột `action`)."""
    d = df.set_index("Date").copy()
    res = run_rule(d)
    is_sus = res.suggestion.str.startswith("NGHI")
    d["suspect_sensor_error"] = False
    for _, r in res[is_sus].iterrows():
        d.loc[r.date, r.column] = np.nan
        d.loc[r.date, "suspect_sensor_error"] = True
        if r.column == "AQI":
            d.loc[r.date, "AQI_Bucket"] = np.nan
    res = res.assign(action=np.where(is_sus, "đặt NaN", "giữ nguyên"))
    return d.reset_index(), res


# ---------------------------------------------------------------- 1 thành phố
def clean_city(city, raw_path):
    """raw -> đã xử lý missing + điểm nghi lỗi + cờ outlier, 1 thành phố.
    Trả về (df, bảng điểm nghi lỗi)."""
    d = load_and_split_city(city, raw_path=raw_path)
    d, _ = impute_time_series(d, city, drop_cols=["Xylene"], verbose=False)
    d = d.drop(columns=[c for c in d.columns if c.startswith("Xylene")])
    d, evidence = apply_suspect_rule(d)
    d = flag_outliers_iqr(d, cols=POLLUTANTS)           # tính SAU khi đã đặt NaN các điểm nghi lỗi
    evidence.insert(0, "city", city)
    return d, evidence


# ---------------------------------------------------------------- gộp 8 thành phố
def merge_cities(frames):
    """Gộp các bảng của từng thành phố thành 1 bảng, cùng bộ cột. Chỉ đánh dấu, không sửa giá trị."""
    merged = pd.concat(frames, ignore_index=True, sort=False)
    for p in POLLUTANTS:
        merged[f"{p}_is_outlier"] = merged[f"{p}_is_outlier"].fillna(False).astype(bool)
    for p in POLLUTANTS + ["AQI"]:
        merged[f"{p}_was_missing"] = merged[f"{p}_was_missing"].fillna(True).astype(bool)
    merged["suspect_sensor_error"] = merged["suspect_sensor_error"].astype(bool)

    both = merged["PM2.5"].notna() & merged["PM10"].notna()
    flag = (merged["PM2.5"] > PM_RATIO * merged["PM10"]).astype("boolean")
    flag[~both] = pd.NA
    merged["pm25_gt_pm10_flag"] = flag

    order = (["Date", "City"] + POLLUTANTS + ["AQI", "AQI_Bucket"]
             + [f"{p}_was_missing" for p in POLLUTANTS + ["AQI"]]
             + [f"{p}_is_outlier" for p in POLLUTANTS]
             + ["pm25_gt_pm10_flag", "suspect_sensor_error"])
    merged = merged[order]
    merged["City"] = pd.Categorical(merged["City"], categories=CITIES, ordered=True)
    merged = merged.sort_values(["City", "Date"]).reset_index(drop=True)
    merged["City"] = merged["City"].astype(str)
    return merged
