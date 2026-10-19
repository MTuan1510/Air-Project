# Nhật ký làm sạch dữ liệu — Chất lượng không khí Ấn Độ (8 thành phố)

**Nguồn:** Kaggle *Air Quality Data in India* (CPCB), `city_day.csv` · **Phạm vi:** Delhi, Gurugram, Lucknow, Jaipur, Bengaluru, Amritsar, Chennai, Hyderabad · **Giai đoạn:** 01/01/2015 – 01/07/2020
**Quy trình:** notebook 01 → 07 (`src/utils.py`, `src/gap_utils.py`); file raw không bị sửa, chạy lại từ raw ra đúng cùng bảng gộp.
**Kiểm tra ban đầu (không phát sinh xử lý):** `city_day.csv` 29.531 dòng, 26 thành phố; lấy 8 thành phố = 14.056 dòng; 0 dòng trùng (City, Date), không đứt ngày, 0 giá trị âm, `AQI_Bucket` khớp thang CPCB.
**Quy ước:** **ô** = một giá trị của một cột trong một ngày; **dòng** = một ngày của một thành phố. Ô bị đổi hoặc bị nghi ngờ đều có cờ đi kèm. Chi tiết từng thành phố × cột: `reports/cleaning_summary_8cities.csv`.

---

## 1. Tổng quan kết quả

| Chỉ tiêu | Trước (raw, 8 thành phố) | Sau làm sạch |
|---|---|---|
| Số dòng | 14.056 | 14.056 (không xoá dòng nào) |
| Số cột | 16 | 40 (11 chất + AQI + AQI_Bucket + 12 cờ `_was_missing` + 11 cờ `_is_outlier` + 2 cờ khác + Date, City) |
| Ô thiếu (11 chất + AQI) | 16.953 (10,05%) | 15.832 (9,39%) |

Đối chiếu: 16.953 + 2.169 (số 0 treo → NaN, bước 1) − 3.329 (nội suy, bước 3) + 39 (nghi lỗi → NaN, bước 7) = **15.832**. Tỉ lệ thiếu giảm ít vì bước 1 *thêm* NaN còn bước 3 chỉ lấp được khoảng thiếu ngắn.

---

## 2. Nhật ký xử lý

| STT | Bước | Cột | Phát hiện | Hành động | Ảnh hưởng | Lý do & kiểm chứng |
|---|---|---|---|---|---|---|
| 1 | Số 0 treo | CO, NOx, Benzene, Toluene | Chuỗi số 0 liên tiếp ≥ 3 ngày: Benzene 646, Toluene 615, CO 540, NOx 368 ô. Ví dụ: Bengaluru NOx đứng đúng 0 suốt 207 ngày (09/11/2016 – 03/06/2017), trước đó còn 6,48 | Đổi thành NaN | 2.169 ô | Cảm biến đứng, không phải nồng độ thật; giữ lại kéo trung bình xuống giả. *Kiểm chứng:* đổi ngưỡng 3 ngày sang 2 / 5 / 7 ngày chỉ làm số ô đổi +8% / −11% / −15% |
| 2 | Bỏ cột Xylene, PM10 Lucknow | Xylene, PM10 (Lucknow) | Xylene thiếu 100% ở 4/8 thành phố (Gurugram 93%, Delhi 39%, Amritsar 17%, Hyderabad 6%); PM10 Lucknow thiếu 100% | Bỏ Xylene ở cả 8 thành phố; PM10 Lucknow để NaN | 4.234 ô Xylene thật + 2.009 ô PM10 rỗng | Cột rỗng ở một nửa số thành phố thì không so sánh được; bỏ cho cả 8 để schema đồng nhất. *Kiểm chứng:* không file `*_clean.csv` nào còn cột Xylene |
| 3 | Nội suy khoảng ngắn, sửa lỗi khoảng dài | 11 chất | 3.329 ô thiếu nằm giữa hai giá trị thật, khoảng ≤ 14 ngày. Kiểm tra lại thấy hàm cũ `interpolate(limit=14)` điền nhầm 1.316 ô trong khoảng > 14 ngày ở 6 thành phố (Lucknow, Jaipur không bị) | Nội suy tuyến tính theo thời gian, chỉ khoảng ≤ 14 ngày, giữ cờ `_was_missing`; sửa hàm trong `src/utils.py`, trả 1.316 ô nhầm về NaN | 3.329 ô (1.316 ô sửa không tính vào mục 1) | Khoảng ngắn nên đường thẳng hợp lý; hàm cũ vẫn bịa số cho khoảng dài. *Kiểm chứng:* trung bình trước / sau nội suy lệch trung vị 0,4%; notebook 07 dựng lại từ raw khớp 100% |
| 4 | Giữ NaN khoảng dài | PM10, NOx, NH3, Benzene, Toluene | 9 cặp (thành phố, cột) còn thiếu ≥ 20%, nặng nhất Gurugram NH3 92,9%, Chennai PM10 84,5%, Gurugram PM10 52,4%; 100% ngày thiếu nằm trong khoảng > 14 ngày | Giữ NaN, giữ `_was_missing`; 2 cặp ≥ 60% (Gurugram NH3, Chennai PM10) **không dùng làm biến mô hình** (theo W3) | 7.733 ô | Thiếu theo khối thời gian (cảm biến chưa lắp / ngừng), không phải MCAR mà gần MAR theo thời gian; nội suy qua khối dài là bịa số. *Kiểm chứng:* AQI trung bình ngày thiếu và ngày có lệch từ 0% đến +82% tuỳ cột |
| 5 | AQI thiếu | AQI, AQI_Bucket | AQI thiếu từ 0,5% (Delhi) đến 13,6% (Gurugram) | Không nội suy; `AQI_Bucket` NaN cùng AQI | 836 dòng | AQI nhiều khả năng là biến kết quả, điền là tạo kết quả giả. *Kiểm chứng:* 0 dòng có AQI mà thiếu nhãn và ngược lại |
| 6 | Gắn cờ ngoại lai | 11 chất | IQR tính riêng theo tháng dương lịch (k = 1,5): 6.656 ô bị đánh dấu, PM2.5 có 531 ngày. Lucknow, Jaipur được tính lại theo quy tắc này | Giữ nguyên giá trị, gắn cờ `_is_outlier` | 6.656 ô | Đỉnh mùa đông (đốt rơm rạ, Diwali) là sự kiện thật, xoá sẽ làm lệch đúng chỗ quan trọng nhất. *Kiểm chứng:* AQI trung vị ở ngày PM2.5 bị cờ là 243, ngày khác 120 |
| 7 | Nghi lỗi cảm biến | PM2.5, AQI | Điều tra 93 điểm (top 5 PM2.5 và top 5 AQI mỗi thành phố, thêm 13 điểm AQI cùng ngày): 41 ô nghi lỗi (22 PM2.5 + 19 AQI) trong 24 ngày ở 7/8 thành phố. Ví dụ: Amritsar 08/05/2017 PM2.5 868,7, gấp 7,5 lần PM10, AQI cùng ngày chỉ 110 | Đặt NaN, gắn `suspect_sensor_error` | 41 ô / 24 ngày | Dấu hiệu: cô lập và trái mùa, PM2.5 > 1,5 × PM10, hoặc AQI cùng ngày với PM2.5 nghi lỗi. *Kiểm chứng:* một bộ luật chung cho 8 thành phố; mỗi điểm có một dòng trong `reports/suspect_points_8cities.csv`. Chưa đối chiếu nguồn CPCB nên gọi là *nghi* lỗi |
| 8 | Giữ đỉnh (không xử lý) | PM2.5, AQI | 52 trong 93 điểm là đỉnh mùa cao điểm, có chất khác cùng tăng hoặc "chưa rõ"; 87 ngày AQI > 500, trong đó 68 ngày ở tháng 10–2 | Giữ nguyên; điểm "chưa rõ" gắn cờ | 52 ô + 87 dòng | Xoá nhầm đỉnh thật gây hại hơn giữ nhầm vài điểm. *Kiểm chứng:* ví dụ Delhi 07/11/2016 AQI 716 đúng mùa cao điểm, chỉ gấp 1,4 lần ngày lân cận, PM2.5 và PM10 cùng rất cao. Cụm 14–16/06/2018 xảy ra cùng lúc ở nhiều thành phố nên giống sự kiện chung hơn lỗi riêng |
| 9 | Điểm đáng ngờ chưa quyết (không xử lý) | PM2.5, Benzene, Toluene | Gurugram PM2.5 30/08/2017 = 643,7 (hai ngày cạnh 6,4 và 33,3), không lọt top 5 của luật ở bước 7. Benzene năm 2015 cao gấp nhiều lần các năm sau: Chennai 17,4 → 0,3 (2017), Bengaluru 27,3 → 0,5 (2020). Còn 304 ô số 0 ngắn, chủ yếu ở Chennai | Giữ nguyên, ghi vào Hạn chế | 305 ô + 2 chuỗi | Có thể do đổi thiết bị / hiệu chuẩn hoặc do thực tế, không có nguồn ngoài để quyết; chuỗi 0 ngắn dưới 3 ngày có thể là giá trị thật rất thấp |
| 10 | Nhất quán PM2.5 – PM10 | PM2.5, PM10 | 139 ngày PM2.5 > 1,2 × PM10 (vô lý vì PM10 đã gồm PM2.5); Chennai 9,0% số ngày kiểm tra được, Bengaluru 3,4%, nơi khác dưới 2% | Giữ nguyên, gắn `pm25_gt_pm10_flag` cho cả 8 thành phố | 139 dòng | Không biết cột nào sai nên chưa có cơ sở xoá. *Kiểm chứng:* Jaipur ra đúng 4 ngày như đã tính riêng ở notebook 02 |
| 11 | Gộp bảng | Bảng gộp | Gộp 8 thành phố bằng `pd.concat`, không scale, không mã hoá | Thêm cờ dùng chung, lưu `air_quality_8cities.csv` | 14.056 dòng × 40 cột | Scale / mã hoá phải fit trên tập train lúc làm mô hình. *Kiểm chứng:* 10 phép assert ở notebook 07 (số dòng khớp raw, giá trị giống từng file, dựng lại được từ raw) |

---

## 3. Hạn chế

| Bước | Rủi ro | Kết luận bị ảnh hưởng | Cách xử lý |
|---|---|---|---|
| Chung | Chuỗi các thành phố dài ngắn khác nhau (Gurugram từ 27/11/2015, Amritsar từ 27/02/2017, Jaipur từ 14/06/2017) | So sánh giữa thành phố | Chỉ so sánh trong khoảng chung 14/06/2017 – 01/07/2020 |
| 2 | Mất 4.234 ô Xylene thật; PM10 chỉ còn 7 thành phố | Mọi phân tích dùng PM10 hoặc Xylene | Nếu cần Xylene, đọc lại từ raw, chỉ dùng 4 thành phố có dữ liệu |
| 3 | Ô nội suy dùng giá trị của ngày **sau** (rò rỉ tương lai) | Đánh giá mô hình dự đoán | Loại các dòng `_was_missing = True` khỏi tập test |
| 4 | Không loại trừ được MNAR (thiếu vì giá trị quá cao / thấp) vì không có nguồn ngoài | Mô hình dùng 9 cặp cột thiếu nhiều | Xử lý NaN trong pipeline (chỉ học trên train) hoặc bỏ cột |
| 5 | Dòng thiếu AQI phải bỏ hoặc xử lý riêng; Gurugram thiếu 13,6% | Mô hình dự đoán AQI | Bỏ dòng thiếu AQI khi huấn luyện, báo cáo riêng Gurugram |
| 6 | Ngưỡng IQR tính trên toàn chuỗi, kể cả giai đoạn sẽ làm tập test; mô hình nhạy với ngoại lai | Hệ số, sai số mô hình | Chỉ dùng cờ cho EDA; so kết quả có và không có dòng bị cờ |
| 7 | Chưa đối chiếu CPCB; có thể đã xoá nhầm một đỉnh thật | Đỉnh PM2.5 / AQI của 7 thành phố | Giá trị gốc lưu trong `suspect_points_8cities.csv` để khôi phục |
| 9 | Còn vài điểm lỗi rải rác (Gurugram 30/08/2017; 12/07/2017 có AQI 576 khi PM2.5 chỉ 75,8); xu hướng theo năm của Benzene, Toluene ở Chennai và Bengaluru bị chi phối bởi năm 2015 | Đỉnh giả trên biểu đồ; kết luận xu hướng theo thời gian | Ghi chú trên biểu đồ; dùng trung vị theo năm hoặc loại 2 cột này khỏi so sánh xu hướng |
| 10 | Tỉ lệ PM2.5 / PM10 của Chennai không đáng tin (PM10 chỉ có từ 2019) | Kết luận về cấu thành bụi ở Chennai | Không dùng tỉ lệ này cho Chennai |
