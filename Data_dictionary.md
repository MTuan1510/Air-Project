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