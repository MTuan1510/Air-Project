# 🇮🇳 Air Pollution Analysis and Temporal Trends in India

Môn học: **Khoa học Dữ liệu** · Nhóm thực hiện: **4 thành viên**

---

## 1. Giới thiệu đề tài
Ô nhiễm không khí tại Ấn Độ là một vấn đề môi trường cấp thiết ảnh hưởng trực tiếp đến sức khỏe cộng đồng. Đồ án dùng tập dữ liệu chuỗi thời gian về chất lượng không khí (`city_day.csv`) để tiền xử lý, phân tích khám phá (EDA) và trực quan hóa xu hướng ô nhiễm theo thời gian và không gian, trên **8 thành phố**: Delhi, Gurugram, Lucknow, Jaipur, Bengaluru, Amritsar, Chennai, Hyderabad.

## 2. Dữ liệu sử dụng
* **Nguồn:** [Air Quality Data in India](https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india) (Kaggle; nguồn gốc Central Pollution Control Board — CPCB).
* **Nội dung:** nồng độ theo ngày của PM2.5, PM10, NO, NO2, NOx, NH3, CO, SO2, O3, Benzene, Toluene, Xylene, cùng chỉ số `AQI` và nhãn `AQI_Bucket`.
* **Khoảng thời gian:** 01/01/2015 – 01/07/2020 (từng thành phố bắt đầu ở thời điểm khác nhau, xem `Data_dictionary.md`).

## 3. Cấu trúc thư mục
```
data/raw/          city_day.csv gốc (không sửa)
data/interim/      các bước trung gian của từng thành phố
data/processed/    <thành phố>_clean.csv và air_quality_8cities.csv (bảng gộp, dùng cho phân tích)
notebooks/         01-06: làm sạch theo từng cặp thành phố; 07: chuẩn hoá và gộp 8 thành phố; 07b: nhật ký làm sạch
src/               utils.py, gap_utils.py (hàm dùng chung)
reports/           cleaning_log_8cities.csv (nhật ký đầy đủ, 36 dòng), cleaning_log_report_8cities.csv (bản rút gọn 13 dòng cho báo cáo), cleaning_summary_8cities.csv, suspect_points_8cities.csv, figures/
```

## 4. Hướng dẫn cài đặt và chạy
```bash
git clone https://github.com/MTuan1510/Air-Project.git
cd Air-Project
pip install -r Requirements.txt
cd notebooks
jupyter notebook
```
Thứ tự chạy: `01` → `02` → `03` → `04` → `05` → `06` → `07_merge_8_cities` → `07b_cleaning_log_8cities`.
Mỗi notebook chạy bằng *Kernel → Restart & Run All*. Đã kiểm tra: chạy lần lượt 01 → 07b từ file gốc cho ra đúng cùng bảng gộp, so từng ô. Notebook 07 và 07b cũng chạy lại độc lập được, kết quả giống hệt mỗi lần chạy.
`07b` chỉ là code sinh ra nhật ký; **nhật ký nằm ở `reports/cleaning_log_8cities.csv`**.

> Notebook 03 và 06 tự nhận Colab hay máy cá nhân (trên Colab thì clone repo, trên máy cá nhân dùng đường dẫn tương đối `../data/...`; bước tải file về chỉ chạy trên Colab). Notebook 02 cũng tự tìm thư mục gốc của repo.
