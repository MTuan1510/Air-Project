# Gói bổ sung báo cáo — chuyển chọn lọc từ repo Test sang Git nhóm

Ngày 11/11/2026. Đây là tài liệu diễn giải/biên tập, không thay source code và không chứng nhận bản sửa Dev đã được tích hợp. Repo Test và Git chính của nhóm là hai nơi khác nhau.

## 1. Nội dung có thể dùng trong báo cáo

### Lựa chọn dữ liệu

> Nghiên cứu sử dụng dữ liệu của tám thành phố từ bộ dữ liệu Kaggle. Theo lựa chọn của nhóm, các thành phố này có khoảng thời gian quan sát tương đối đồng nhất và dữ liệu tương đối đầy đủ hơn các phương án khác được cân nhắc. Đây là lựa chọn phục vụ khả năng so sánh trong bộ dữ liệu, không phải bằng chứng rằng tám thành phố đại diện cho toàn bộ Ấn Độ hoặc là tám thành phố ô nhiễm nhất.

Đối chiếu tên/link bộ dữ liệu và khoảng thời gian với bản nhóm thực sự nộp; không tự thêm tên nguồn cụ thể khi chưa có metadata.

### Xử lý thiếu dữ liệu cho phân tích hồi cứu

> Quy tắc nội suy các khoảng thiếu không quá 14 ngày được sử dụng như một quy ước thực hành cho phân tích hồi cứu. Ngưỡng này không được xem là tối ưu duy nhất về mặt khoa học. Nội suy có thể làm trơn biến động và ảnh hưởng các thống kê liên quan, do đó cần thận trọng khi diễn giải các đợt ô nhiễm ngắn hạn. Quy trình hồi cứu không mặc nhiên phù hợp cho dự báo tại thời điểm thực tế, vì có thể sử dụng quan sát xuất hiện sau thời điểm cần dự báo.

Không đổi ngưỡng hoặc chạy tối ưu mới chỉ để hoàn thiện đoạn này.

### Diễn giải tỷ số mùa

Hai cách tổng hợp trả lời hai câu hỏi khác nhau:
- Trung vị tỷ số mùa đông/mùa mưa trên **5 thành phố trong phép tính tương ứng**: **2,82**, khoảng được DA báo **[2,42;3,17]**.
- Tỷ số của số liệu gộp **8 thành phố**: **137,1/42 ≈3,26**.

Không viết “cả8 thành phố có trung vị tỷ số2,82”, không dùng3,26 thay cho trung vị tỷ số. Trước đưa vào bản cuối, kiểm định nghĩa mùa,5 thành phố được chọn, đơn vị và cách tạo khoảng trong bảng V16 của hồ sơ DA. Nếu chưa xác định được loại khoảng, không tự gắn nhãn95% CI.

### Ý nghĩa thống kê

> Các mối liên hệ thời tiết–ô nhiễm được diễn giải theo từng thành phố và nhóm kiểm định đã xác định. Kết quả có ý nghĩa ở mức danh nghĩa không đồng nghĩa còn có ý nghĩa sau hiệu chỉnh đa kiểm định. Tương quan quan sát được không chứng minh quan hệ nhân quả.

Hồ sơ DA ghi32/48 sau BH so với33/48 theo CI danh nghĩa (V18); family15 giả thuyết có3 hỗ trợ,1 ngược chiều,11 chưa đủ bằng chứng (V19). Đây là các family/tiêu chí khác nhau: không cộng, không đổi mẫu số và không gán các count này vào biểu đồ khác nếu chưa đối chiếu. Chỉ đưa count khi có bảng nguồn và mô tả tiêu chí đi kèm.

### Phần mở rộng dự báo AQI

> Bài toán dự báo AQI ngày kế tiếp là phần mở rộng của nghiên cứu. Kết quả được đánh giá theo thời gian và so sánh với mô hình đối chứng. Mức cải thiện trên một giai đoạn kiểm tra không bảo đảm duy trì ở giai đoạn tiếp theo. Ngoài sai số trung bình, số ngày ô nhiễm nặng ít và rủi ro sử dụng thông tin tương lai trong xử lý dữ liệu là những hạn chế cần được xem xét.

Bằng chứng DA vòng trước: test L3 MAE19,52 so persistence23,47; giai đoạn giữ lại cuối L3 MAE13,78 so14,80, chênh−1,02 với khoảng bootstrap[−2,70;0,48], chưa đủ bằng chứng cho mức cải thiện. Các số này thuộc đường phân tích trước sửa, KHÔNG phải kết quả của code Dev mới. Chỉ dùng nếu khớp phiên bản notebook nhóm đang nộp và công khai hạn chế preprocessing; không gọi là ước lượng sạch leakage đã được xác nhận. Nếu không đối chiếu được phiên bản, bỏ số cụ thể và giữ diễn giải giới hạn.

## 2. Không viết nhầm trạng thái triển khai

Không viết “nhóm đã triển khai cache offline/đã loại bỏ hoàn toàn leakage” khi code chính của nhóm chưa nhận bản sửa. Trong repo Test có ứng viên Dev và DA báo kiểm GateA; kiểm chứng F01 chưa hoàn tất trong phạm vi quyết định dừng. F01/F02 chưa được RA đóng. API Open-Meteo thật chưa được kiểm do giới hạn mạng.

Nếu cần nêu hướng phát triển:

> Trên bản sao thử nghiệm, quy trình đọc cache và đường dựng đặc trưng dự báo từ dữ liệu gốc đã được đề xuất cải tiến. Việc xác minh toàn bộ và tích hợp vào phiên bản chính chưa hoàn tất; các cải tiến này được ghi nhận là hướng phát triển, không phải chức năng đã nghiệm thu của bản nộp.

Có thể bỏ hoàn toàn lịch sử AI/kiểm chứng nội bộ khỏi báo cáo; chỉ giữ hạn chế phương pháp có liên quan.

## 3. Nguồn đối chiếu nội bộ (không cần chép cả thư mục sang nhóm)

- DA snapshot `0dfc71568d439b3b2e9dae9a9093f23bcf379969`: bằng chứng vòng trước V16/V18/V19 và đánh giá dự báo; xem bảng nguồn trước trích dẫn.
- DA prep `13e93ae12c483f01a573ee51ef9562a315e45068`: chuẩn bị/reproduction, không là nghiệm thu Dev.
- RA: `reports/ra/final_review_report.md`, `round2/RA_DECISIONS_02.md`, `round2/RA_DECISIONS_03.md`.
- Dev code `a9757af398ddac2f8536e8019e4eb6b5900b4f75`, tài liệu `ce78795227b184d9ab0c9a2d38e9d0185169c501`, PR4: ứng viên riêng, không được merge cùng gói tài liệu này.
- Các báo cáo GateA/pilot DA mới được người dùng chuyển trong hội thoại; tài liệu này không tự nhận đã kiểm độc lập các artifact đó.
