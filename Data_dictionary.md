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

**Quy ước dùng cột làm biến:** một cột (trong một thành phố) thiếu **dưới 60%** thì còn dùng được; từ 60% trở lên thì không dùng. Theo quy ước này, các cột không dùng được là PM10 ở Lucknow (100%) và Chennai (84,5%), NH3 ở Gurugram (92,9%). Xem cột `dung_lam_bien_mo_hinh` trong `reports/cleaning_summary_8cities.csv`.

**Giới hạn cần nhớ khi phân tích:**
- `PM10` thiếu 100% ở Lucknow, 84,5% ở Chennai, 52,4% ở Gurugram; `NH3` thiếu 92,9% ở Gurugram, 49,7% ở Lucknow.
- Độ dài chuỗi mỗi thành phố khác nhau (Delhi, Bengaluru, Chennai, Lucknow từ 01/2015; Gurugram từ 11/2015; Amritsar từ 02/2017; Jaipur từ 06/2017).
- Dữ liệu kết thúc 01/07/2020 nên có chứa giai đoạn phong toả COVID-19.

Bảng thống kê chi tiết từng thành phố × từng cột (số ô thiếu trước/sau, số ô flatline, số ô nội suy): `reports/cleaning_summary_8cities.csv`.

---

## 3. Dữ liệu thời tiết (nguồn thứ hai) — `data/raw/weather/` và `data/processed/air_quality_8cities_weather.csv`

**Nguồn:** Open-Meteo Historical Weather API (https://open-meteo.com), dữ liệu tái phân tích **ERA5** (ECMWF / Copernicus). Giấy phép CC BY 4.0, ghi công: *Weather data by Open-Meteo.com*.
**Cách lấy:** `src/weather_utils.py` và `notebooks/04_weather_merge.ipynb`; mỗi thành phố một điểm toạ độ (bảng dưới), dữ liệu **theo giờ**, 25/12/2014 → 01/07/2020, múi giờ Asia/Kolkata (UTC+5:30), gió m/s. Bản tải về lưu ở `data/raw/weather/openmeteo_<thành phố>_hourly.csv.gz` (48.384 dòng giờ mỗi nơi), không sửa.
**Đây là dữ liệu mô hình, không phải số đo tại trạm.** Mỗi giá trị là trung bình trên một ô lưới 0,25°.

| Thành phố | Toạ độ yêu cầu (lat, lon) | Ô lưới ERA5 thực dùng (lat, lon) | Độ cao ô lưới (m) |
|---|---|---|---|
| Delhi | 28.61, 77.21 | 28.50, 77.25 | 217 |
| Gurugram | 28.46, 77.03 | 28.50, 77.00 | 229 |
| Lucknow | 26.85, 80.95 | 26.75, 81.00 | 117 |
| Jaipur | 26.91, 75.79 | 27.00, 75.75 | 430 |
| Bengaluru | 12.97, 77.59 | 13.00, 77.50 | 914 |
| Amritsar | 31.63, 74.87 | 31.75, 74.75 | 234 |
| Chennai | 13.08, 80.27 | 13.00, 80.25 | 10 |
| Hyderabad | 17.39, 78.49 | 17.50, 78.50 | 502 |

**Các file đầu ra**

| File | Quy mô | Ghi chú |
|---|---|---|
| `data/processed/weather_daily_8cities.csv` | 16.128 dòng (8 thành phố × 2.016 ngày) × 16 cột | Thời tiết theo ngày, có thêm các ngày từ 25/12/2014 để tạo biến trễ về sau |
| `data/processed/air_quality_8cities_weather.csv` | 14.056 dòng × 54 cột | `air_quality_8cities.csv` (40 cột, giữ nguyên) + 14 cột thời tiết, ghép trái theo (`City`, `Date`); 0 dòng thiếu thời tiết |

**Từ điển các cột thời tiết (14 cột)**

| Cột | Kiểu | Đơn vị | Ý nghĩa | Cách tính |
|---|---|---|---|---|
| `temp_mean` | float | °C | Nhiệt độ không khí ở độ cao 2 m, trung bình ngày | mean của 24 giá trị giờ |
| `temp_min` | float | °C | Nhiệt độ thấp nhất trong ngày | min của 24 giá trị giờ |
| `temp_max` | float | °C | Nhiệt độ cao nhất trong ngày | max của 24 giá trị giờ |
| `humidity_mean` | float | % | Độ ẩm tương đối ở 2 m, trung bình ngày | mean của 24 giá trị giờ |
| `pressure_mean` | float | hPa | Áp suất bề mặt, trung bình ngày (phụ thuộc độ cao: Bengaluru thấp hơn các thành phố khác) | mean của 24 giá trị giờ |
| `wind_speed_mean` | float | m/s | Tốc độ gió ở 10 m, trung bình ngày | mean của 24 giá trị giờ |
| `wind_speed_max` | float | m/s | Tốc độ gió giờ lớn nhất trong ngày | max của 24 giá trị giờ |
| `wind_u` | float | m/s | Thành phần gió hướng Đông (dương = gió thổi về phía Đông), trung bình ngày | u = -tốc độ × sin(hướng), rồi mean theo ngày |
| `wind_v` | float | m/s | Thành phần gió hướng Bắc (dương = gió thổi về phía Bắc), trung bình ngày | v = -tốc độ × cos(hướng), rồi mean theo ngày |
| `wind_dir_8` | text | — | Hướng gió chính trong ngày (gió thổi TỪ hướng nào), 8 hướng. Chỉ để mô tả, không dùng làm biến số | hướng của vector (wind_u, wind_v), làm tròn 8 hướng |
| `precip_sum` | float | mm | Tổng lượng mưa trong ngày | sum của 24 giá trị giờ |
| `rain_day` | bool | — | True nếu tổng mưa >= 1 mm | precip_sum >= ngưỡng |
| `blh_mean` | float | m | Chiều cao lớp biên khí quyển, trung bình ngày (thấp = chất ô nhiễm bị nén sát mặt đất) | mean của 24 giá trị giờ |
| `blh_min` | float | m | Chiều cao lớp biên thấp nhất trong ngày | min của 24 giá trị giờ |

**Lưu ý khi dùng:**
- Hướng gió là góc vòng tròn: dùng `wind_u`, `wind_v` làm biến số, `wind_dir_8` chỉ để mô tả.
- `precip_sum` lệch phải rất mạnh (phần lớn ngày gần 0): dùng Spearman hoặc `log1p` khi tính tương quan, hồi quy.
- **Chưa scale, chưa tạo biến trễ**: làm sau khi chia train/test theo thời gian để tránh rò rỉ dữ liệu.
- Thời tiết không có giá trị thiếu và không có cờ `_was_missing`; không có bước nội suy nào áp dụng cho thời tiết.
- Delhi và Gurugram ở hai ô lưới sát nhau, thời tiết gần như trùng nhau (tương quan theo ngày 0,95–0,999): không coi là hai quan sát độc lập.