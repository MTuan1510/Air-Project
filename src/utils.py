# src/utils.py
import os
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
    Phát hiện outliers bằng phương pháp IQR, tính ngưỡng trên TOÀN BỘ khoảng
    thời gian (không tách theo tháng).
    Trả về: DataFrame chứa các outliers, ngưỡng dưới, ngưỡng trên.

    LƯU Ý: với dữ liệu ô nhiễm theo ngày (có mùa vụ rõ rệt), hàm này dễ gắn
    nhầm những tháng ô nhiễm cao theo mùa (đốt rơm rạ, Diwali) thành outlier.
    Nên dùng `flag_outliers_iqr()` (tính riêng theo từng tháng) thay vì hàm
    này cho bước Outliers chính thức của project — hàm này giữ lại chỉ để
    tham khảo/dùng nhanh cho việc khác.
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

    # 1) flatline zeros -> NaN (làm trước để không bỏ sót khi đếm missing)
    df, flat_changed = flag_flatline_zeros(df, cols=cols, min_run=flatline_min_run)

    # 2) đánh dấu missing gốc (sau khi đã lộ flatline, để phản ánh đúng thực tế)
    flag_cols = [c for c in cols + ['AQI'] if c in df.columns]
    for col in flag_cols:
        df[f'{col}_was_missing'] = df[col].isna()

    # 3) drop cột đã thống nhất với nhóm
    dropped = [c for c in drop_cols if c in df.columns]
    df = df.drop(columns=dropped)

    # 4) nội suy CHỈ gap ngắn (AQI không nằm trong `cols` nên không bị đụng vào)
    df = df.set_index('Date')
    interp_cols = [c for c in cols if c in df.columns]
    df[interp_cols] = df[interp_cols].interpolate(method='time', limit=max_short_gap,
                                                    limit_area='inside')
    df = df.reset_index()

    # 5) suy AQI_Bucket từ AQI thật (AQI chưa từng bị đụng vào ở bước 4)
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


AQI_BINS = [0, 50, 100, 200, 300, 400, 10_000]
AQI_LABELS = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]


def flag_outliers_iqr(city_df, cols=POLLUTANT_COLS, k=1.5, min_group_n=10):
    """
    Đánh dấu outlier bằng phương pháp IQR, nhưng tính ngưỡng Q1/Q3 RIÊNG cho
    từng THÁNG (gộp tất cả các năm lại theo tháng dương lịch 1-12) thay vì
    tính chung cả năm — tránh gắn nhầm ô nhiễm mùa vụ (mùa đốt rơm rạ
    tháng 10-11, Diwali) thành outlier, vì baseline mỗi tháng vốn khác nhau.

    CHỈ ĐÁNH DẤU (thêm cột <col>_is_outlier = True/False), KHÔNG xoá hay sửa
    giá trị gốc — quyết định giữ/xoá để lại cho bước sau, khi có đủ dữ liệu
    cả 8 thành phố để đối chiếu xem outlier là lỗi cảm biến hay sự kiện thật.

    min_group_n: nếu 1 tháng có ít hơn số quan sát này (do missing nhiều),
    bỏ qua không đánh giá tháng đó (IQR tính trên quá ít điểm sẽ không đáng tin).
    """
    df = city_df.copy()
    month = df['Date'].dt.month
    for col in cols:
        if col not in df.columns:
            continue
        q1 = df.groupby(month)[col].transform(lambda x: x.quantile(0.25))
        q3 = df.groupby(month)[col].transform(lambda x: x.quantile(0.75))
        iqr = q3 - q1
        lower, upper = q1 - k * iqr, q3 + k * iqr
        n_per_month = df.groupby(month)[col].transform('count')
        is_outlier = ((df[col] < lower) | (df[col] > upper)) & (n_per_month >= min_group_n)
        df[f'{col}_is_outlier'] = is_outlier.fillna(False)
    return df


def validity_checks(df, cols=POLLUTANT_COLS):
    """
    Kiểm tra các luật hợp lệ cơ bản (đúng tinh thần "assert what must be true"):
      - Nồng độ khí / AQI không âm
      - Ngày không nằm trong tương lai
      - AQI_Bucket khớp với AQI (theo thang CPCB) ở những dòng có cả 2 giá trị
    NaN được coi là "chưa vi phạm" (missing đã xử lý & theo dõi riêng ở bước trước).
    Trả về DataFrame: rule | n_violations.
    """
    checks = {}
    for col in cols + ['AQI']:
        if col in df.columns:
            checks[f'{col} không âm'] = df[col].isna() | (df[col] >= 0)
    if 'Date' in df.columns:
        checks['Date không ở tương lai'] = df['Date'] <= pd.Timestamp.today()
    if 'AQI_Bucket' in df.columns and 'AQI' in df.columns:
        both = df['AQI'].notna() & df['AQI_Bucket'].notna()
        expected = pd.cut(df.loc[both, 'AQI'], bins=AQI_BINS, labels=AQI_LABELS)
        match = pd.Series(True, index=df.index)
        match.loc[both] = (df.loc[both, 'AQI_Bucket'].astype(str) == expected.astype(str))
        checks['AQI_Bucket khớp với AQI'] = match
    rows = [(name, int((~ok).sum())) for name, ok in checks.items()]
    return pd.DataFrame(rows, columns=['rule', 'n_violations'])


def check_consistency(df):
    """
    Kiểm tra tính nhất quán cơ bản (Consistency - W4):
      - Tên City có biến thể trùng nhau do khoảng trắng thừa / hoa-thường không
      - AQI_Bucket có nhãn lạ ngoài 6 nhãn chuẩn (Good...Severe) không
    Trả về dict {tên_kiểm_tra: mô tả vi phạm}; dict rỗng nghĩa là không có vấn đề.
    """
    issues = {}
    if 'City' in df.columns:
        raw = sorted(df['City'].dropna().unique())
        normalized = sorted(df['City'].dropna().str.strip().str.lower().unique())
        if len(raw) != len(normalized):
            issues['City'] = f"Nghi ngờ có biến thể trùng nhau (khoảng trắng/hoa-thường): {raw}"
    if 'AQI_Bucket' in df.columns:
        extra = set(df['AQI_Bucket'].dropna().unique()) - set(AQI_LABELS)
        if extra:
            issues['AQI_Bucket'] = f"Có nhãn lạ ngoài chuẩn {AQI_LABELS}: {extra}"
    return issues


def check_duplicates(df, subset=('City', 'Date')):
    """Đếm số dòng trùng theo business key (mặc định City+Date)."""
    return int(df.duplicated(subset=list(subset)).sum())


DEFAULT_DROP_COLS = ["Xylene"]  # bằng chứng: 4/8 thành phố thiếu Xylene 100%, xem cleaning log


def clean_city_pipeline(city_name, raw_path="../data/raw/city_day.csv",
                         drop_cols=None, save_dir="../data/processed", verbose=True):
    """
    Pipeline 1 lệnh: raw -> đã làm sạch, cho 1 thành phố.
    Gộp load -> xử lý missing (flatline + nội suy gap ngắn) -> đánh dấu outlier
    -> kiểm tra consistency/dedup -> lưu ra save_dir.

    drop_cols mặc định = DEFAULT_DROP_COLS (["Xylene"]) nếu không truyền gì —
    đây là quyết định đã có bằng chứng cụ thể trên cả 8 thành phố (4/8 thành
    phố thiếu Xylene 100%). Muốn KHÔNG drop gì, truyền drop_cols=[] rõ ràng.

    KHÔNG scale/encode ở đây — nếu sau này cần cho mô hình, làm riêng lúc đó
    trên tập train để tránh rò rỉ dữ liệu (đúng nguyên tắc leakage ở W5).
    File lưu ra vẫn giữ nguyên đơn vị gốc, dùng chung được cho cả EDA lẫn model.
    """
    city_df = load_and_split_city(city_name, raw_path=raw_path)
    drop_cols = DEFAULT_DROP_COLS if drop_cols is None else drop_cols
    clean_df, _ = impute_time_series(city_df, city_name, drop_cols=drop_cols, verbose=verbose)
    clean_df = flag_outliers_iqr(clean_df)

    issues = check_consistency(clean_df)
    n_dup = check_duplicates(clean_df)
    if verbose:
        print(f"  - Consistency: {issues if issues else 'không có vấn đề'}")
        print(f"  - Dòng trùng (City+Date): {n_dup}")

    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        out_path = f"{save_dir}/{city_name.lower()}_clean.csv"
        clean_df.to_csv(out_path, index=False)
        if verbose:
            print(f"  -> Đã lưu {out_path}")
    return clean_df