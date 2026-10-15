# Data dictionary — `data/raw/city_day.csv`

**Dataset:** Air Quality Data in India (2015–2020), Kaggle
**Nguồn gốc:** Central Pollution Control Board (CPCB), Chính phủ Ấn Độ
**Quy mô:** 29.531 dòng, 26 thành phố, theo ngày, 1/1/2015 → 1/7/2020

## 1. Bảng từ điển dữ liệu

| Column name | Type | Unit | Description | Missing values | Source |
|---|---|---|---|---|---|
| City | text | — | Tên thành phố quan trắc | None | Kaggle (CPCB) |
| Date | date | — | Ngày quan trắc | None | Kaggle (CPCB) |
| PM2.5 | float | µg/m³ * | Bụi mịn đường kính ≤2.5 micromet | 15.6% → để trống (NaN) | Kaggle (CPCB) |
| PM10 | float | µg/m³ * | Bụi đường kính ≤10 micromet | 37.7% → NaN | Kaggle (CPCB) |
| NO | float | µg/m³ * | Nitric oxide | 12.1% → NaN | Kaggle (CPCB) |
| NO2 | float | µg/m³ * | Nitrogen dioxide | 12.1% → NaN | Kaggle (CPCB) |
| NOx | float | ppb * | Tổng hợp các oxit nitơ | 14.2% → NaN | Kaggle (CPCB) |
| NH3 | float | µg/m³ * | Ammonia | 35.0% → NaN | Kaggle (CPCB) |
| CO | float | mg/m³ * | Carbon monoxide | 7.0% → NaN | Kaggle (CPCB) |
| SO2 | float | µg/m³ * | Sulphur dioxide | 13.1% → NaN | Kaggle (CPCB) |
| O3 | float | µg/m³ * | Ozone tầng mặt đất | 13.6% → NaN | Kaggle (CPCB) |
| Benzene | float | µg/m³ * | Benzene | 19.0% → NaN | Kaggle (CPCB) |
| Toluene | float | µg/m³ * | Toluene | 27.2% → NaN | Kaggle (CPCB) |
| Xylene | float | µg/m³ * | Xylene | 61.3% → NaN | Kaggle (CPCB) |
| AQI | float | — (chỉ số) | Chỉ số chất lượng không khí, tính từ các chất trên | 15.9% → NaN | Kaggle (CPCB) |
| AQI_Bucket | text | — | Phân loại: Good / Satisfactory / Moderate / Poor / Very Poor / Severe | 15.9% → NaN | Kaggle (CPCB) |

---

## 2. Từ điển dữ liệu sau làm sạch — `data/processed/air_quality_8cities.csv`

**Quy mô:** 14.056 dòng × 40 cột, 8 thành phố, theo ngày. Mỗi dòng là một cặp (`City`, `Date`), không trùng khoá, không thiếu ngày giữa chuỗi của từng thành phố.

| Nhóm cột | Cột | Ý nghĩa |
|---|---|---|
| Khoá | `Date`, `City` | Ngày và thành phố |
| Nồng độ (11) | `PM2.5`, `PM10`, `NO`, `NO2`, `NOx`, `NH3`, `CO`, `SO2`, `O3`, `Benzene`, `Toluene` | Giá trị sau làm sạch. Giữ nguyên đơn vị gốc, **chưa scale/encode**. Đã bỏ `Xylene`. |
| Kết quả | `AQI`, `AQI_Bucket` | Lấy từ dữ liệu gốc, **không nội suy**. `AQI_Bucket` khớp thang CPCB. |
| Theo vết missing (12) | `<cột>_was_missing` | `True` nếu ô đó thiếu ở dữ liệu gốc hoặc là chuỗi số 0 treo (flatline, ≥ 3 ngày) đã bị chuyển thành NaN. Dùng để biết ô nào là giá trị nội suy: `was_missing = True` và giá trị khác NaN. |
| Outlier (11) | `<cột>_is_outlier` | `True` nếu giá trị vượt ngưỡng IQR×1,5 **tính riêng theo tháng dương lịch**. Chỉ đánh dấu, **không** sửa hay xoá giá trị. Không áp dụng cho `AQI`. |
| Kiểm tra logic | `pm25_gt_pm10_flag` | `True` nếu PM2.5 > 1,2 × PM10 (vô lý vì PM10 gồm cả PM2.5). Để trống khi thiếu PM2.5 hoặc PM10 (Lucknow luôn trống). Chỉ đánh dấu. |
| Nghi lỗi cảm biến | `suspect_sensor_error` | `True` nếu ngày đó bị đặt NaN cho PM2.5 và/hoặc AQI vì **nghi lỗi cảm biến** (đỉnh cô lập, trái mùa, chất khác không tăng theo; hoặc PM2.5 > 1,5 × PM10). Cả 8 thành phố dùng cùng một luật, chỉ xét top 5 điểm lớn nhất của PM2.5 và của AQI. Tổng 24 ngày; danh sách và giá trị gốc nằm trong `reports/suspect_points_8cities.csv`. Gọi là "nghi lỗi", chưa đối chiếu được nguồn CPCB. |

**Quy tắc làm sạch chung:** chuỗi số 0 liên tiếp ≥ 3 ngày → NaN; nội suy theo thời gian chỉ cho khoảng thiếu ≤ 14 ngày; khoảng dài hơn giữ nguyên NaN. Điểm nghi lỗi cảm biến → NaN, không nội suy.

**Quy ước dùng cột làm biến:** một cột (trong một thành phố) thiếu **dưới 60%** thì còn dùng được; từ 60% trở lên thì không dùng. Theo quy ước này, các cột không dùng được là PM10 ở Lucknow (100%) và Chennai (83%), NH3 ở Gurugram (93%). Xem cột `dung_lam_bien_mo_hinh` trong `reports/cleaning_summary_8cities.csv`.

**Giới hạn cần nhớ khi phân tích:**
- `PM10` thiếu 100% ở Lucknow, 83% ở Chennai, 52% ở Gurugram; `NH3` thiếu 93% ở Gurugram, 50% ở Lucknow.
- Độ dài chuỗi mỗi thành phố khác nhau (Delhi, Bengaluru, Chennai, Lucknow từ 01/2015; Gurugram từ 11/2015; Amritsar từ 02/2017; Jaipur từ 06/2017).
- Dữ liệu kết thúc 01/07/2020 nên có chứa giai đoạn phong toả COVID-19.

Bảng thống kê chi tiết từng thành phố × từng cột (số ô thiếu trước/sau, số ô flatline, số ô nội suy): `reports/cleaning_summary_8cities.csv`.
