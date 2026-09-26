# 🇮🇳 Air Pollution Analysis and Temporal Trends in India

Môn học: **Khoa học Dữ liệu**  
Nhóm thực hiện: **Nhóm 4 thành viên**

---

## 1. Giới thiệu đề tài 
Ô nhiễm không khí tại Ấn Độ là một vấn đề môi trường cấp thiết ảnh hưởng trực tiếp đến sức khỏe cộng đồng. Đồ án này sử dụng tập dữ liệu chuỗi thời gian về chất lượng không khí (`city_day.csv`)[cite: 2] nhằm thực hiện tiền xử lý, phân tích khám phá (EDA) và trực quan hóa xu hướng biến động ô nhiễm theo thời gian và không gian.

## 2. Dữ liệu sử dụng 
* **Nguồn dữ liệu:** File `city_day.csv` chứa các bản ghi đo lường chất lượng không khí theo ngày tại nhiều thành phố lớn của Ấn Độ. [Air Quality Data in India](https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india) (Kaggle, nguồn gốc: Central Pollution Control Board — CPCB).
* **Nội dung chính:** Ghi nhận các chỉ số về nồng độ các chất ô nhiễm phổ biến (như PM2.5, PM10, NO2, SO2, CO, O3...) cùng với chỉ số chất lượng không khí tổng hợp (`AQI`) và nhãn đánh giá mức độ ô nhiễm (`AQI_Bucket`).

## 3. Hướng dẫn cài đặt và Chạy 
1. Clone repository về máy:
   ```bash
   git clone https://github.com/MTuan1510/Air-Project.git
   cd Air-Project