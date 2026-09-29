# src/utils.py
import pandas as pd
import numpy as np

POLLUTANT_COLS = ['PM2.5', 'PM10', 'NO', 'NO2', 'NOx', 'NH3', 'CO',
                   'SO2', 'O3', 'Benzene', 'Toluene', 'Xylene']


def audit(df):
    """
    Báo cáo nhanh chất lượng của một DataFrame.
    Trả về: DataFrame chứa dtype, số lượng missing, % missing, số lượng unique.
    """
    return pd.DataFrame({
        "dtype": df.dtypes,
        "n_missing": df.isna().sum(),
        "pct_missing": (df.isna().mean() * 100).round(1),
        "n_unique": df.nunique(),
    })


def load_and_split_city(city_name, raw_path="../data/raw/city_day.csv"):
    """
    Đọc dữ liệu gốc, chuyển Date sang datetime, và lọc ra 1 thành phố cụ thể.
    """
    df = pd.read_csv(raw_path)
    df["Date"] = pd.to_datetime(df["Date"])
    city_df = df[df["City"] == city_name].sort_values("Date").reset_index(drop=True)
    return city_df


def detect_outliers_iqr(df, column):
    """
    Phát hiện outliers bằng phương pháp IQR.
    Trả về: DataFrame chứa các outliers, ngưỡng dưới, ngưỡng trên.
    (Dùng ở bước Outliers - chưa dùng tới ở bước xử lý missing này.)
    """
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    outliers = df[(df[column] < lower_bound) | (df[column] > upper_bound)]
    return outliers, lower_bound, upper_bound


def flag_flatline_zeros(df, cols=POLLUTANT_COLS, min_run=3):
    """
    Phát hiện các chuỗi giá trị 0 liên tiếp >= min_run ngày trong cùng 1 cột.
    Nồng độ khí thực tế hiếm khi đứng yên ở đúng 0 nhiều ngày liền -> nhiều khả
    năng là cảm biến bị treo/lỗi (flatline), không phải giá trị thật.
    Chuyển các vị trí đó thành NaN.

    Trả về: (df đã sửa, dict {cột: số dòng bị chuyển thành NaN}).
    """
    df = df.copy()
    changed = {}
    for col in cols:
        if col not in df.columns:
            continue
        is_zero = (df[col] == 0)
        grp = (is_zero != is_zero.shift()).cumsum()
        run_len = is_zero.groupby(grp).transform('sum')
        flatline = is_zero & (run_len >= min_run)
        if flatline.any():
            changed[col] = int(flatline.sum())
            df.loc[flatline, col] = np.nan
    return df, changed


def diagnose_missing(city_df, cols=POLLUTANT_COLS, block_ratio_threshold=0.5,
                      drop_threshold=0.9, min_pct_for_block=0.02):
    """
    Với mỗi cột: tính % missing và block_ratio = % số ngày thiếu nằm gọn
    trong 1 khối liên tục dài nhất. Dùng để phân biệt:
      - missing rải rác, ngắn  -> có thể nội suy an toàn
      - missing dồn thành khối lớn (thường do cảm biến chưa lắp/hỏng dài ngày,
        phụ thuộc vào Date -> MAR, không phải MCAR) -> không nên nội suy xuyên qua

    Trả về DataFrame báo cáo + đề xuất hành động cho từng cột.
    """
    sub = city_df.set_index('Date')
    sub = sub.reindex(pd.date_range(sub.index.min(), sub.index.max(), freq='D'))
    rows = []
    for col in cols:
        if col not in sub.columns:
            continue
        miss = sub[col].isna()
        pct = miss.mean()
        if pct == 0:
            rows.append([col, 0.0, np.nan, 'giữ nguyên'])
            continue
        grp = (~miss).cumsum()
        run_lengths = miss.groupby(grp).sum()
        run_lengths = run_lengths[run_lengths > 0]
        block_ratio = run_lengths.max() / miss.sum()
        if pct < min_pct_for_block:
            action = 'nội suy trực tiếp (missing quá ít)'
        elif pct >= drop_threshold and block_ratio >= block_ratio_threshold:
            action = 'ĐỀ XUẤT DROP (gần như không có dữ liệu thật)'
        elif block_ratio >= block_ratio_threshold:
            action = 'có khối lớn — chỉ nội suy phần rải rác, giữ NaN ở khối lớn'
        else:
            action = 'nội suy trực tiếp'
        rows.append([col, round(pct * 100, 1), round(block_ratio * 100), action])
    return pd.DataFrame(rows, columns=['col', 'pct_missing', 'block_ratio_%', 'action']).set_index('col')


def impute_time_series(city_df, city_name, drop_cols=None, cols=POLLUTANT_COLS,
                        max_short_gap=14, flatline_min_run=3,
                        derive_aqi_bucket=True, verbose=True):
    """
    Pipeline xử lý missing cho time series 1 thành phố:
      1) Phát hiện & chuyển chuỗi 0 liên tiếp dài (flatline) -> NaN
      2) Đánh dấu missing GỐC (giữ vết, thêm cột <col>_was_missing)
      3) Drop các cột gần như không có dữ liệu thật (drop_cols - do nhóm quyết)
      4) Nội suy theo thời gian CHỈ cho gap <= max_short_gap ngày liên tiếp;
         gap dài hơn (khối cấu trúc, cảm biến chưa hoạt động) CHỦ Ý để nguyên
         NaN — không bịa số cho hàng trăm/nghìn ngày không có dữ liệu thật.
      5) Suy AQI_Bucket từ AQI THẬT cho các dòng có AQI nhưng thiếu bucket.
         KHÔNG tự điền AQI — đây nhiều khả năng là biến kết quả của phân tích,
         để nguyên missing và xử lý riêng khi nhóm quyết định dùng nó thế nào.

    max_short_gap=14 (mặc định, ~2 tuần) là ngưỡng thận trọng cho nội suy
    tuyến tính trên dữ liệu biến động mạnh theo ngày như nồng độ khí; có thể
    tăng lên (vd 60) nếu nhóm thống nhất chấp nhận nội suy dài hơn, nhưng nên
    ghi rõ lý do trong báo cáo vì nội suy càng dài càng dễ sai lệch xu hướng.
    """
    df = city_df.sort_values('Date').reset_index(drop=True)
    drop_cols = drop_cols or []

    df, flat_changed = flag_flatline_zeros(df, cols=cols, min_run=flatline_min_run)

    flag_cols = [c for c in cols + ['AQI'] if c in df.columns]
    for col in flag_cols:
        df[f'{col}_was_missing'] = df[col].isna()

    dropped = [c for c in drop_cols if c in df.columns]
    df = df.drop(columns=dropped)

    df = df.set_index('Date')
    interp_cols = [c for c in cols if c in df.columns]
    df[interp_cols] = df[interp_cols].interpolate(method='time', limit=max_short_gap,
                                                    limit_area='inside')
    df = df.reset_index()

    if derive_aqi_bucket and 'AQI_Bucket' in df.columns and 'AQI' in df.columns:
        bins = [0, 50, 100, 200, 300, 400, 10_000]
        labels = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]
        need_bucket = df['AQI_Bucket'].isna() & df['AQI'].notna()
        if need_bucket.any():
            df.loc[need_bucket, 'AQI_Bucket'] = pd.cut(
                df.loc[need_bucket, 'AQI'], bins=bins, labels=labels
            )

    if verbose:
        print(f"--- Xử lý Missing Values cho {city_name} ---")
        for col, n in flat_changed.items():
            print(f"  - {col}: phát hiện {n} ngày flatline (0 liên tục >= {flatline_min_run} ngày) -> NaN")
        if dropped:
            print(f"  - Đã xoá cột (đề xuất, cần nhóm đồng ý): {dropped}")
        remaining = df[[c for c in cols if c in df.columns] + ['AQI']].isna().sum().sum()
        print(f"  => Còn {remaining} ô missing SAU xử lý (CHỦ Ý giữ NaN ở khối trống dài, không bịa số)")

    return df, flat_changed