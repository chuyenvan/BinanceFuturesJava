# PREREG_EDGE_ATTR — Edge của K24+skipFull đến từ đâu, và chịu được chi phí thanh khoản tới mức nào

Ngày 2026-10-18 (viết 10-17 tối, owner duyệt hướng "ok"; commit 10-18 sau khi máy owner kết nối lại). Chỉ ĐO: không đổi chiến lược, không đổi 242/shadow, không chạy sim Java mới,
không Binance REST (chỉ dữ liệu Vision đã có trên Oracle). Pre-reg này commit TRƯỚC khi chạy bất kỳ phép join/đo nào ở §3–§5.

## 0. Câu hỏi

- Q1 (attribution): ΣPnL của K24+skipFull phân bố thế nào theo (a) thanh khoản symbol lúc vào, (b) cỡ đợt vào lệnh cùng phút, (c) năm;
  phần nào là beta thị trường alt/BTC trong thời gian giữ lệnh?
- Q2 (chi phí theo thanh khoản): nếu chi phí khớp thực tăng theo mức tham gia thanh khoản (impact), edge còn bao nhiêu ở quy mô
  vốn sim (35k), pilot (10k) và gấp 10 (350k)? Chi phí cộng thêm hoà vốn là bao nhiêu bps cho nhóm kém thanh khoản?

## 1. Dữ liệu (cố định)

- Lệnh: `printDone.csv` của ECMEAS bucket DEV (mô hình chi phí vào đã hiệu chuẩn — số kỳ vọng release v1):
  `ec-s-s42`, `ecm-d-s{7,13,21,99,123,777,2024}` (8 seed). Ghi md5 từng file vào result.
- Phụ (chỉ mô tả, không dùng để kết luận): HO4 W9 `ecm-h-s{42,7,13,21,99,123,777,2024}` (2026-01→09, đã dùng làm holdout ⇒ chỉ đo lại).
- Giá/khối lượng: kline1m Vision (`~/claude_master/gvz/k2021/kline1m-2021-*.parquet`, `~/vz_e1/raw/kline1m-*.parquet`), cột
  close, quote_volume.
- Múi giờ: cột `start`/`end` của sim là UTC+7; nến M = nến có open time = start − 7h (đã kiểm ở P2-D).
- Cửa sổ chính: lệnh có `start` ∈ [2021-07-01, 2026-01-01) +07 (DFULL của ECMEAS).

## 2. Định nghĩa (cố định)

- Đã khảo sát cấu trúc (chỉ đọc header/5 dòng, không đo): cột `margin` = quantity × entry (notional lúc vào, khớp 1e-7);
  `profit` = % giá; mỗi dòng printDone là một chân (dòng DCA_LEVEL1 là chân riêng). Symbol sim không có hậu tố ⇒ ghép Vision
  bằng `sym + "USDT"`.
- Notional N_i = cột `margin`. PnL_i = cột `pnl`. ROI_i = PnL_i / N_i.
- L24_i = Σ quote_volume của các nến 1m có open ∈ [M−1439, M] (đến hết nến quyết định). "Đủ dữ liệu" = ≥ 1368 nến (95 %).
  Bucket L: `<5M`, `5–20M`, `20–100M`, `≥100M` USD.
- σd_i = độ lệch chuẩn log-return 1m trên cùng cửa sổ × √1440.
- Đợt: các lệnh cùng seed có cùng `start`. Cỡ đợt b_i = số lệnh trong đợt. Bucket: `1–5`, `6–12`, `13–24` (như BURST_RISK_1016).
- Chỉ số thị trường:
  - ALT_EW: mỗi phút, trung bình log-return 1m của mọi symbol USDT-M (trừ BTCUSDT, ETHUSDT) có quote_volume > 0 ở cả hai nến;
    log-return bị cắt ở ±0,5 để chặn bất thường dữ liệu. Log-return tính trong từng file tháng (phút đầu mỗi tháng mỗi symbol bị bỏ —
    chấp nhận).
  - BTC: log-return close BTCUSDT.
  - m_i = exp(Σ log-return từ nến M đến nến E) − 1, với E = end − 7h (giữ lệnh từ close(M) đến close(E)).

## 3. Kiểm hợp lệ (phải PASS trước khi đọc kết quả; FAIL ⇒ dừng, báo, sửa pipeline, không đổi định nghĩa §2)

- V1: |entry_i / close(M) − 1| ≤ 0,0035 cho ≥ 99 % lệnh (bucket cost tối đa 0,0032).
- V2: ΣPnL DEV mỗi seed tính lại khớp ECMEAS (`ecm_score.py`, cùng cách lọc theo `end`) với sai lệch ≤ 1 USD.
- V3: ≥ 98 % lệnh "đủ dữ liệu" cho L24, σd; ≥ 98 % có nến M và nến E trong chỉ số ALT_EW. Lệnh thiếu bị loại khỏi Q1/Q2
  và báo số lượng + ΣPnL của phần bị loại.
- V4: tổng theo các bucket = tổng chung (đóng kín kế toán, sai lệch ≤ 1e-6 tương đối).

## 4. Q1 — Attribution (mô tả + 3 luật kết luận)

Bảng (mỗi ô: mean ± sd qua 8 seed): n, ΣPnL, tỉ trọng ΣPnL, PnL/lệnh, ROI trung vị, tỉ lệ thắng; theo L × b, theo năm × L.
Beta: OLS gộp mỗi seed, ROI_i = α + β_alt·m_alt,i + ε (và riêng với m_btc); báo β, α/lệnh, và tỉ trọng alpha
A = Σ N_i(ROI_i − β·m_i) / Σ N_i·ROI_i.

Luật (chốt trước):
- R1 "edge rộng" nếu tập S0 = {b ≤ 12} ∩ {L24 ≥ 20M} có ΣPnL > 0 với CI95 qua seed (t, df 7) không chứa 0
  VÀ PnL/lệnh của S0 ≥ 50 % PnL/lệnh toàn bộ. Ngược lại "edge tập trung".
- R2 "phần lớn không phải beta" nếu A (theo ALT_EW) ≥ 50 % ở ≥ 6/8 seed. Ngược lại "chủ yếu beta alt".
- R3 báo riêng nhóm L24 < 20M: tỉ trọng ΣPnL và PnL/lệnh (không có ngưỡng; dùng cho Q2).

## 5. Q2 — Stress chi phí theo thanh khoản (hậu kiểm PnL, bậc 1)

- Impact mỗi chân (vào và ra, cùng notional xấp xỉ N_i): c_i = Y · σd_i · √(N_i·s / L24_i), s = hệ số quy mô vốn.
- Lưới cố định: Y ∈ {0,5; 1,0} × s ∈ {10/35 (pilot 10k), 1 (sim 35k), 10 (350k)}. Mọi PnL báo ở thang sim:
  PnL'_i = PnL_i − 2·c_i(s)·N_i (impact tính theo notional đã nhân s, rồi quy về thang sim).
- Lưới phẳng cho nhóm L24 < 20M: chi phí cộng thêm khứ hồi ∈ {25, 50, 100, 200} bps; báo bps hoà vốn của nhóm này và
  bps (chỉ áp cho nhóm L24 < 20M) làm ΣPnL toàn bộ giảm 50 %.
- Chỉ số: ΣPnL', ΔΣPnL %, PnL'/lệnh theo bucket L. KHÔNG tính lại MTM/Calmar (sizing phụ thuộc equity ⇒ hậu kiểm chỉ là bậc 1);
  có tính equity realized + maxDD realized để tham khảo.
- Luật: "nhạy chi phí" nếu kịch bản Y=1, s=1 làm ΣPnL giảm > 30 % (mean qua seed) HOẶC làm nhóm L24 < 20M âm.

## 6. Ngoài phạm vi / cấm

- Không chọn ngưỡng lọc, không đề xuất bỏ nhóm nào dựa trên kết quả này ⇒ mọi ý tưởng cải tiến từ đây cần pre-reg mới,
  đo DEV rồi xác nhận kho backcast 2020; không dùng 2026 để chọn.
- Giới hạn đã biết: impact √ là mô hình ngoại suy, chưa hiệu chuẩn cho crypto alt; phút vào lệnh thường là phút sập (thanh khoản
  khác trung bình 24h). Kết quả Q2 là độ nhạy, không phải dự báo chi phí thật — chỉ pilot tiền thật đo được.

## 7. Sản phẩm

`research/edge_attr/` (script), `docs/result/EDGE_ATTR.md` + `docs/result/edge_attr/*.json`, dòng ledger trong
`docs/research/VZ_EXPLORE_LEDGER.md`.
