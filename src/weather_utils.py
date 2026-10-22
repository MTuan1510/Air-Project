"""Hàm và hằng số dùng chung cho notebook thời tiết (`notebooks/04_weather_merge.ipynb`).

Việc làm: tải thời tiết theo giờ từ Open-Meteo (dữ liệu tái phân tích ERA5) cho 8 thành phố,
kiểm tra, gộp theo ngày, rồi ghép vào `data/processed/air_quality_8cities.csv`.

Quy ước:
  * Không sửa `air_quality_8cities.csv`; bảng ghép được lưu ra file mới `air_quality_8cities_weather.csv`.
  * Dữ liệu tải về (theo giờ) được lưu ở `data/raw/weather/` và không sửa; lần chạy sau đọc lại từ đó.
  * Chưa scale, chưa tạo biến trễ (lag): để bước dựng mô hình, sau khi chia train/test theo thời gian.
"""
from pathlib import Path
import time

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW_WEATHER = ROOT / "data" / "raw" / "weather"
AQ_FILE = ROOT / "data" / "processed" / "air_quality_8cities.csv"
OUT_MERGED = ROOT / "data" / "processed" / "air_quality_8cities_weather.csv"
OUT_DAILY = ROOT / "data" / "processed" / "weather_daily_8cities.csv"

API_URL = "https://archive-api.open-meteo.com/v1/archive"
MODEL = "era5"                    # một mô hình duy nhất cho cả 8 thành phố; đặt None nếu API báo lỗi tham số `models`
TIMEZONE = "Asia/Kolkata"         # phải trùng múi giờ của "ngày" trong dữ liệu CPCB (UTC+5:30)
START, END = "2014-12-25", "2020-07-01"   # lấy dư vài ngày đầu để sau này tạo biến trễ mà không mất ngày đầu
ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0), dữ liệu tái phân tích ERA5 (ECMWF / Copernicus)"

CITIES = ["Delhi", "Gurugram", "Lucknow", "Jaipur", "Bengaluru", "Amritsar", "Chennai", "Hyderabad"]
KEYS = ["City", "Date"]

# toạ độ trung tâm thành phố (gần đúng); API sẽ trả về toạ độ ô lưới thật sự được dùng
CITY_COORDS = {
    "Delhi":     (28.61, 77.21),
    "Gurugram":  (28.46, 77.03),
    "Lucknow":   (26.85, 80.95),
    "Jaipur":    (26.91, 75.79),
    "Bengaluru": (12.97, 77.59),
    "Amritsar":  (31.63, 74.87),
    "Chennai":   (13.08, 80.27),
    "Hyderabad": (17.39, 78.49),
}

HOURLY_CORE = ["temperature_2m", "relative_humidity_2m", "surface_pressure",
               "wind_speed_10m", "wind_direction_10m", "precipitation"]
HOURLY_EXTRA = ["boundary_layer_height"]      # chỉ dùng nếu API trả về được (notebook có bước thử)
RAIN_DAY_MM = 1.0                              # ngày mưa = tổng mưa >= 1 mm (ngưỡng thường dùng trong khí tượng)
DIRS8 = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

# (cột, kiểu, đơn vị, ý nghĩa, cách tính từ dữ liệu theo giờ)
WEATHER_DICT = [
    ("temp_mean", "float", "°C", "Nhiệt độ không khí ở độ cao 2 m, trung bình ngày", "mean của 24 giá trị giờ"),
    ("temp_min", "float", "°C", "Nhiệt độ thấp nhất trong ngày", "min của 24 giá trị giờ"),
    ("temp_max", "float", "°C", "Nhiệt độ cao nhất trong ngày", "max của 24 giá trị giờ"),
    ("humidity_mean", "float", "%", "Độ ẩm tương đối ở 2 m, trung bình ngày", "mean của 24 giá trị giờ"),
    ("pressure_mean", "float", "hPa", "Áp suất bề mặt, trung bình ngày (phụ thuộc độ cao: Bengaluru thấp hơn các thành phố khác)", "mean của 24 giá trị giờ"),
    ("wind_speed_mean", "float", "m/s", "Tốc độ gió ở 10 m, trung bình ngày", "mean của 24 giá trị giờ"),
    ("wind_speed_max", "float", "m/s", "Tốc độ gió giờ lớn nhất trong ngày", "max của 24 giá trị giờ"),
    ("wind_u", "float", "m/s", "Thành phần gió hướng Đông (dương = gió thổi về phía Đông), trung bình ngày", "u = -tốc độ × sin(hướng), rồi mean theo ngày"),
    ("wind_v", "float", "m/s", "Thành phần gió hướng Bắc (dương = gió thổi về phía Bắc), trung bình ngày", "v = -tốc độ × cos(hướng), rồi mean theo ngày"),
    ("wind_dir_8", "text", "—", "Hướng gió chính trong ngày (gió thổi TỪ hướng nào), 8 hướng. Chỉ để mô tả, không dùng làm biến số", "hướng của vector (wind_u, wind_v), làm tròn 8 hướng"),
    ("precip_sum", "float", "mm", "Tổng lượng mưa trong ngày", "sum của 24 giá trị giờ"),
    ("rain_day", "bool", "—", f"True nếu tổng mưa >= {RAIN_DAY_MM:g} mm", "precip_sum >= ngưỡng"),
]
WEATHER_DICT_BLH = [
    ("blh_mean", "float", "m", "Chiều cao lớp biên khí quyển, trung bình ngày (thấp = chất ô nhiễm bị nén sát mặt đất)", "mean của 24 giá trị giờ"),
    ("blh_min", "float", "m", "Chiều cao lớp biên thấp nhất trong ngày", "min của 24 giá trị giờ"),
]

# giới hạn vật lý: ngoài khoảng này là lỗi dữ liệu hoặc lỗi đơn vị, không phải thời tiết thật
RANGES = {
    "temp_mean": (-10, 50), "temp_min": (-10, 50), "temp_max": (-10, 55),
    "humidity_mean": (0, 100), "pressure_mean": (800, 1100),
    "wind_speed_mean": (0, 25), "wind_speed_max": (0, 40),
    "precip_sum": (0, 500),
    "blh_mean": (0, 4500), "blh_min": (0, 4500),      # chỉ kiểm khi cột có trong bảng
}


# ----------------------------------------------------------------------------- tải dữ liệu
def _request(params, retries=5):
    """Gọi API, tự thử lại khi bị giới hạn tần suất (429) hoặc lỗi máy chủ (5xx)."""
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(API_URL, params=params, timeout=120)
        except requests.RequestException as e:
            if attempt == retries:
                raise
            print(f"  lỗi mạng ({e.__class__.__name__}), thử lại sau {5 * attempt}s")
            time.sleep(5 * attempt)
            continue
        if r.status_code == 200:
            return r.json()
        if r.status_code == 429:
            print("  bị giới hạn tần suất (429), chờ 65s rồi thử lại")
            time.sleep(65)
            continue
        if r.status_code >= 500:
            time.sleep(5 * attempt)
            continue
        try:
            reason = r.json().get("reason", r.text)
        except ValueError:
            reason = r.text
        raise RuntimeError(f"Open-Meteo trả lỗi {r.status_code}: {reason}")
    raise RuntimeError("Hết số lần thử mà API vẫn không trả dữ liệu")


def _params(city, variables, start, end):
    lat, lon = CITY_COORDS[city]
    p = {"latitude": lat, "longitude": lon, "start_date": start, "end_date": end,
         "hourly": ",".join(variables), "timezone": TIMEZONE, "wind_speed_unit": "ms"}
    if MODEL:
        p["models"] = MODEL
    return p


def _to_frame(data, variables):
    h = pd.DataFrame({"time": data["hourly"]["time"], **{v: data["hourly"][v] for v in variables}})
    h["grid_lat"], h["grid_lon"], h["grid_elev"] = data["latitude"], data["longitude"], data.get("elevation", np.nan)
    return h


def cache_path(city):
    return RAW_WEATHER / f"openmeteo_{city.lower()}_hourly.csv.gz"


def fetch_city(city, variables, start=START, end=END, use_cache=True):
    """Dữ liệu theo giờ của một thành phố. Có sẵn bản lưu đủ biến và đủ khoảng thời gian thì đọc lại, không gọi API."""
    path = cache_path(city)
    if use_cache and path.exists():
        h = pd.read_csv(path)
        if set(variables) <= set(h.columns) and h["time"].iloc[0][:10] <= start and h["time"].iloc[-1][:10] >= end:
            h.attrs["from_cache"] = True
            return h
    data = _request(_params(city, variables, start, end))
    h = _to_frame(data, variables)
    h.attrs["from_cache"] = False
    if use_cache:
        RAW_WEATHER.mkdir(parents=True, exist_ok=True)
        h.to_csv(path, index=False, compression="gzip")
    return h


def fetch_all(variables, cities=CITIES, pause=3):
    """Tải 8 thành phố, trả về dict {thành phố: bảng theo giờ}. Nghỉ vài giây giữa các lần gọi thật."""
    out = {}
    for i, c in enumerate(cities):
        out[c] = fetch_city(c, variables)
        cached = out[c].attrs.get("from_cache", False)
        print(f"{c}: {len(out[c]):,} dòng giờ" + (" (đọc từ bản lưu)" if cached else " (vừa tải)"))
        if not cached and i < len(cities) - 1:
            time.sleep(pause)
    return out


def smoke_test():
    """Tải thử 7 ngày của Delhi, không lưu. Chạy trước khi tải thật để biết API và tham số còn chạy."""
    h = fetch_city("Delhi", HOURLY_CORE, "2019-01-01", "2019-01-07", use_cache=False)
    print(f"OK: {len(h)} dòng giờ (mong đợi 168), ô lưới dùng: lat {h.grid_lat[0]}, lon {h.grid_lon[0]}, cao {h.grid_elev[0]} m")
    return h


def probe_variable(var):
    """True nếu API trả được biến `var` (có giá trị thật) cho Delhi."""
    try:
        data = _request(_params("Delhi", [var], "2019-01-01", "2019-01-07"), retries=2)
        return pd.Series(data["hourly"][var]).notna().any()
    except (RuntimeError, requests.RequestException, KeyError) as e:
        print(f"Không lấy được {var}: {e}")
        return False


# ----------------------------------------------------------------------------- kiểm tra dữ liệu giờ
def check_hourly(h, variables, start=START, end=END):
    """Số liệu kiểm tra cho bảng theo giờ của một thành phố (notebook sẽ assert trên kết quả)."""
    t = pd.to_datetime(h["time"])
    expected_days = (pd.Timestamp(end) - pd.Timestamp(start)).days + 1
    return {
        "so_dong": len(h),
        "mong_doi": expected_days * 24,
        "gio_trung": int(t.duplicated().sum()),
        "o_trong": int(h[variables].isna().sum().sum()),
        "dau": t.min().strftime("%Y-%m-%d %H:%M"),
        "cuoi": t.max().strftime("%Y-%m-%d %H:%M"),
    }


# ----------------------------------------------------------------------------- gộp theo ngày
def _dir8(u, v):
    deg = (np.degrees(np.arctan2(-u, -v)) + 360) % 360          # gió thổi TỪ hướng này
    idx = ((deg + 22.5) // 45).astype(int) % 8
    return pd.Series(np.array(DIRS8)[idx.to_numpy()], index=u.index)


def hourly_to_daily(h):
    """Gộp bảng theo giờ của một thành phố thành bảng theo ngày (theo múi giờ Asia/Kolkata)."""
    h = h.copy()
    h["Date"] = pd.to_datetime(h["time"]).dt.normalize()
    ang = np.deg2rad(h["wind_direction_10m"])
    h["_u"] = -h["wind_speed_10m"] * np.sin(ang)                # hướng gió là hướng gió thổi TỪ đâu, nên có dấu trừ
    h["_v"] = -h["wind_speed_10m"] * np.cos(ang)
    g = h.groupby("Date")
    d = pd.DataFrame({
        "temp_mean": g["temperature_2m"].mean(),
        "temp_min": g["temperature_2m"].min(),
        "temp_max": g["temperature_2m"].max(),
        "humidity_mean": g["relative_humidity_2m"].mean(),
        "pressure_mean": g["surface_pressure"].mean(),
        "wind_speed_mean": g["wind_speed_10m"].mean(),
        "wind_speed_max": g["wind_speed_10m"].max(),
        "wind_u": g["_u"].mean(),
        "wind_v": g["_v"].mean(),
        "precip_sum": g["precipitation"].sum(min_count=1),
    })
    if "boundary_layer_height" in h.columns:
        d["blh_mean"] = g["boundary_layer_height"].mean()
        d["blh_min"] = g["boundary_layer_height"].min()
    num = d.columns
    d[num] = d[num].round(2)
    d["rain_day"] = d["precip_sum"] >= RAIN_DAY_MM
    d["wind_dir_8"] = _dir8(d["wind_u"], d["wind_v"])
    d["n_hours"] = g.size()                                     # cột kiểm tra, bỏ ở bước cuối
    return d.reset_index()


def build_daily(hourly):
    """Ghép các thành phố thành một bảng theo ngày: City, Date, các cột thời tiết (cột kiểm tra n_hours đã được assert rồi bỏ)."""
    parts = []
    for city, h in hourly.items():
        d = hourly_to_daily(h)
        d.insert(0, "City", city)
        parts.append(d)
    daily = pd.concat(parts, ignore_index=True)
    bad = daily[daily["n_hours"] != 24]
    assert bad.empty, f"{len(bad)} ngày không đủ 24 giờ, ví dụ:\n{bad.head()}"
    return daily.drop(columns="n_hours")


def weather_cols(daily):
    return [c for c in daily.columns if c not in KEYS]


# ----------------------------------------------------------------------------- kiểm tra hợp lý
def check_ranges(daily):
    """Các ô nằm ngoài giới hạn vật lý (RANGES) và ngày có nhiệt độ min > mean hoặc mean > max. Mong đợi: bảng rỗng."""
    rows = []
    for col, (lo, hi) in RANGES.items():
        if col not in daily.columns:
            continue
        bad = daily[(daily[col] < lo) | (daily[col] > hi)]
        rows += [bad.assign(vi_pham=f"{col} ngoài [{lo}, {hi}]")[KEYS + [col, "vi_pham"]].rename(columns={col: "gia_tri"})]
    order = daily[(daily["temp_min"] > daily["temp_mean"] + 0.01) | (daily["temp_mean"] > daily["temp_max"] + 0.01)]
    rows += [order.assign(vi_pham="temp_min <= temp_mean <= temp_max bị vi phạm", gia_tri=order["temp_mean"])[KEYS + ["gia_tri", "vi_pham"]]]
    return pd.concat(rows, ignore_index=True)


def soft_checks(daily):
    """Kiểm tra theo kiến thức khí hậu. Chỉ cảnh báo (không dừng), vì ngưỡng là ước lượng thô."""
    d = daily.assign(month=daily["Date"].dt.month, year=daily["Date"].dt.year)
    warns = []
    jan = d[d.month == 1].groupby("City")["temp_mean"].mean()
    may = d[d.month == 5].groupby("City")["temp_mean"].mean()
    if jan["Amritsar"] >= 15:
        warns.append(f"Amritsar tháng 1 trung bình {jan['Amritsar']:.1f}°C, cao bất thường cho mùa đông Punjab (mong đợi dưới 15)")
    if jan["Chennai"] <= 22:
        warns.append(f"Chennai tháng 1 trung bình {jan['Chennai']:.1f}°C, thấp bất thường (mong đợi trên 22)")
    if may["Chennai"] <= 30:
        warns.append(f"Chennai tháng 5 trung bình {may['Chennai']:.1f}°C, thấp bất thường (mong đợi trên 30)")
    full = d[(d.year >= 2016) & (d.year <= 2019)]
    for c in ["Delhi", "Jaipur", "Lucknow"]:
        x = full[full.City == c]
        share = x[x.month.between(6, 9)]["precip_sum"].sum() / x["precip_sum"].sum()
        if share < 0.6:
            warns.append(f"{c}: chỉ {share:.0%} lượng mưa rơi vào tháng 6-9, thấp bất thường cho vùng gió mùa hè (mong đợi trên 60%)")
    return warns


def city_summary(daily):
    """Bảng tóm tắt theo thành phố, dùng cho nhật ký và để mắt thường kiểm tra."""
    d = daily.assign(year=daily["Date"].dt.year)
    full = d[d.year.between(2016, 2019)]
    return pd.DataFrame({
        "so_ngay": d.groupby("City").size(),
        "nhiet_do_tb": d.groupby("City")["temp_mean"].mean().round(1),
        "do_am_tb": d.groupby("City")["humidity_mean"].mean().round(0),
        "gio_tb_m/s": d.groupby("City")["wind_speed_mean"].mean().round(1),
        "mua_mm_moi_nam": (full.groupby("City")["precip_sum"].sum() / 4).round(0),
        "ty_le_ngay_mua": d.groupby("City")["rain_day"].mean().round(2),
    }).loc[CITIES]


# ----------------------------------------------------------------------------- ghép vào bảng chính
def merge_weather(aq, daily):
    """Ghép trái theo (City, Date). Mỗi dòng của bảng chính khớp đúng một dòng thời tiết (validate m:1)."""
    return aq.merge(daily, on=KEYS, how="left", validate="m:1")


def dictionary_markdown(has_blh=False):
    rows = WEATHER_DICT + (WEATHER_DICT_BLH if has_blh else [])
    lines = ["| Cột | Kiểu | Đơn vị | Ý nghĩa | Cách tính |", "|---|---|---|---|---|"]
    lines += [f"| `{c}` | {t} | {u} | {m} | {h} |" for c, t, u, m, h in rows]
    return "\n".join(lines)