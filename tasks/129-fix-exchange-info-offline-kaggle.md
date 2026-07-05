# TASK-129 (stub): exchange_info offline cho Kaggle — diệt geo-block fallback

- **status:** todo (chờ CCD-119 trả tree; phát hiện 2026-07-05 sáng khi truy 2 FAILED replication)
- **Gốc rễ:** `ClientSingleton.EXCHANGE_INFO_PATH` hardcode layout Kaggle CŨ + dataset cũ
  (`/kaggle/input/datasets/chuyendinh/java-run/exchange_info.data`) → Kaggle layout mới không thấy file
  → fallback GỌI API Binance → geo-block (US IP) → exception; sau đó quantity KHÔNG được normalize theo
  stepSize (confound Δ nhỏ so Oracle — Oracle fallback API thành công). 2 job FAILED replication nghi do đây.
- **Việc:**
  1. Tool nhỏ DumpExchangeInfoTool (chạy Oracle — gọi getExchangeInformation() qua client rồi gson.toJson
     ra exchange_info.data — dùng CÙNG Gson class để chắc format đọc lại khớp).
  2. Sửa ClientSingleton: thứ tự tìm file = env EXCHANGE_INFO_PATH → ./exchange_info.data (CWD) →
     layout mới /kaggle/input/java-run-lc/... → layout cũ → fallback API (giữ nguyên cho VPS). REPORT-ONLY
     với hành vi VPS/242 (không đổi đường sống).
  3. Thêm exchange_info.data vào dataset java-run-lc (version mới) + run_worker template copy vào CWD.
  4. Gate build + smoke 1 kernel trước fleet.
