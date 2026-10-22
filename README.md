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
data/processed/    air_quality_8cities.csv: bảng gộp 8 thành phố, dùng cho phân tích (do 01_cleaning tạo ra)
notebooks/         01_cleaning, 02_cleaning_evidence, 03_eda; archive/ là các notebook cũ (xem archive/README.md)
src/               pipeline.py (pipeline làm sạch 8 thành phố), utils.py, gap_utils.py (hàm làm sạch), eda_utils.py (hàm EDA)
reports/           cleaning_log_8cities.md (nhật ký làm sạch), cleaning_summary_8cities.csv, suspect_points_8cities.csv, figures/
```
`data/interim/` và các file `data/processed/<thành phố>_clean.csv` là sản phẩm trung gian của các notebook cũ, **không còn được dùng**; có thể xoá.

## 4. Hướng dẫn cài đặt và chạy
```bash
git clone https://github.com/MTuan1510/Air-Project.git
cd Air-Project
pip install -r Requirements.txt
cd notebooks
jupyter notebook
```
Chạy lần lượt, mỗi notebook bằng *Kernel -> Restart & Run All*:

| Thứ tự | Notebook | Việc làm | Đầu ra chính |
|---|---|---|---|
| 1 | `01_cleaning.ipynb` | từ `city_day.csv` gốc: làm sạch 8 thành phố bằng một pipeline, gộp, kiểm tra bằng `assert` | `data/processed/air_quality_8cities.csv`, `reports/cleaning_summary_8cities.csv`, `reports/suspect_points_8cities.csv` |
| 2 | `02_cleaning_evidence.ipynb` | bằng chứng đằng sau các quyết định làm sạch (ví dụ chi tiết Lucknow, Jaipur; đối chiếu và bằng chứng cho cả 8 thành phố) | `reports/cleaning_log_lucknow_jaipur.csv`, hình trong `reports/figures/` |
| 3 | `03_eda.ipynb` | EDA: Phần A (ở đâu), B (khi nào), C (chất nào), kiểm tra độ nhạy, tổng hợp | `reports/figures/eda_00_*` đến `eda_05_*` |

`02` và `03` đọc kết quả của `01`, nên chạy `01` trước. `01` không phụ thuộc file nào ngoài `data/raw/city_day.csv`. Kết quả từ raw trùng từng ô với bảng gộp mà các notebook cũ tạo ra.

> Trên Colab, ô đầu của `01_cleaning` tự clone repo nếu chưa có. `02` và `03` cần mở từ thư mục `notebooks/` của repo.
