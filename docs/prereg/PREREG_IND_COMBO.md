# PREREG_IND_COMBO — thư viện indicator đa khung + gate/S1 linh hoạt (cảm hứng HKUDS/AI-Trader)

Ngày: 2026-11-14 · Tác giả: MASTER · Thực thi: agent Opus (mới) · Trạng thái: Pha 0 (chỉ đo). Pha 1 (sim) CHỈ chạy khi MASTER duyệt.

## §0 Bối cảnh + khai báo rủi ro (đọc trước)
- AI-Trader (HKUDS, arXiv 2512.10971) là benchmark/nền tảng LLM-agent (MCP tools: giá, search, news, trade). KHÔNG có indicator/alpha tái dùng. Crypto: 10 coin, nến ngày, 2 tuần (01–14/11/2025), MỌI model lỗ (−12…−19 %), chỉ DeepSeek thắng benchmark nhờ giữ tiền mặt. ⇒ Không port. LLM-agent KHÔNG backtest được trung thực trên 2022–2025 (kiến thức huấn luyện của LLM rò rỉ tương lai, không tất định, tốn phí) ⇒ LOẠI khỏi prereg này.
- Thứ lấy từ AI-Trader chỉ là Ý TƯỞNG "kết hợp nhiều công cụ/chỉ báo + bỏ phiếu". Hệ hiện có ĐÃ làm điều này: S1 = XGB 45 feature (có rsi1H, basketRsi14, wick, funding, OI, LS, taker), gate = XGB 33 feature. Các nhánh ĐÃ ĐÓNG liên quan: F4 (mô hình tổ hợp thua biến đơn), GATEFEAT (IC tốt hơn nhưng sim không cải thiện), GATE_VZ 13 feature NO-GO, SCREEN_WIDE 24 anomaly NO-GO, ENTRY_CONFIRM/MKT_UP/MKT_UP2 (top-K/S1/alpha)/UP_TRIG NO-GO, GKF (K không điều kiện) NO-GO, R5P2 MAX15 futility (Y72 tốt KHÔNG chuyển thành PnL).
- Prior thấp. Prereg này chỉ hợp lệ vì: (a) thư viện = indicator ĐA KHUNG (1h/4h/1d) chưa có trong 45/33 feature, (b) đo trực tiếp trên PnL LEG thật (đã qua exit/DCA — sửa bài học R5), (c) kill rẻ ở Pha 0.
- HARKing: viết sau khi biết các nhánh trên đóng; không xem dữ liệu Y nào của prereg này trước khi khoá hash.

## §1 Baseline + dữ liệu
- B0 = cấu hình v1.2 hiện tại (nt-x14, K24 + skipFull, gate p15 pct 90 ngày). Đơn vị Pha 0: LEG vào lệnh của B0 trong dump sim DEV (8 seed) — tái dùng dump đã có (GATE_SMART Pha 0 / EDGE_ATTR). KHÔNG chạy sim mới ở Pha 0.
- Cần ở mỗi leg: symbol, ts vào (phút, ghi rõ UTC hay +07 — sim printDone `start` là UTC+7), PnL ròng % của leg (có phí, DCA, exit), hạng S1 trong phút, điểm S1 nếu có, id seed.
- Near-miss (track G): phút có r/q ∈ [0,70; 1,0) + phút pass; Y72 theo đúng định nghĩa R5 Pha 1 (prereg 200a29a3).
- Chia thời gian: EXPLORE 2022-01-01..2023-12-31 · CONFIRM 2024-01-01..2025-12-31 · HO 2026-01..06 CHỈ MÔ TẢ.
- Thiếu bất kỳ trường bắt buộc ⇒ DỪNG, báo MASTER, không tự chế thay thế.

## §2 Thư viện indicator (CỐ ĐỊNH — không thêm/bớt sau khi xem Y)
Mọi indicator tính CAUSAL trên nến ĐÃ ĐÓNG trước phút vào (nến 1h/4h/1d resample từ kline1m, nến đang chạy KHÔNG dùng).
Coin-level (C1–C20):
1–3 RSI14 trên 1h / 4h / 1d · 4–5 Stoch %K14 1h / 4h · 6–7 Bollinger %b(20,2) 1h / 4h · 8 BB width(20) 1d dạng phân vị 180 ngày của chính coin (squeeze) · 9–10 MACD hist(12,26,9)/ATR14 trên 1h / 4h · 11–12 ADX14 4h / 1d · 13 (+DI − −DI) 1d · 14 (close − Donchian20d high)/ATR14d · 15 drawdown từ đỉnh 30 ngày · 16–17 close/SMA50 − 1 và close/SMA200 − 1 (1d; coin < 200 ngày ⇒ NaN) · 18 realized vol 1h / realized vol 24h (std log-ret 1m) · 19 volume z 1h so với 7 ngày · 20 số nến 4h đỏ liên tiếp.
Market-level (M1–M6): BTC RSI14 4h · BTC RSI14 1d · BTC close/SMA200 − 1 · breadth = % coin universe có close > SMA50 1d · ALT_EW drawdown 30 ngày · vol ALT_EW 24h / 30 ngày.
Bước khử trùng (CHỈ dùng X, trước khi đọc Y): bỏ indicator có |Spearman| > 0,80 với bất kỳ feature nào trong 45 feature S1 (nếu có bảng feature trong dump) hoặc với indicator đứng trước trong danh sách. Ghi danh sách cuối vào commit khoá.
Tổ hợp ("thuật toán" kiểu bỏ phiếu):
- C_ALL = trung bình phân vị có dấu của mọi indicator coin-level còn lại (cutpoint + dấu từ EXPLORE).
- C_TOP5 = như trên nhưng chỉ 5 indicator |IC| EXPLORE lớn nhất.
- ML = XGBoost depth 3, 200 cây, lr 0,05, subsample 0,8, seed 20261114; mục tiêu = rank(Y_leg) đã khử theo hạng S1 + năm; feature = thư viện + hạng/điểm S1; train CHỈ EXPLORE; KHÔNG tune.

## §3 Thống kê Pha 0
- Cụm = đợt (phút pass cách nhau ≤ 60′); bootstrap theo cụm 2 000 lần, seed 20261114, CI90. Gộp 8 seed (cụm hấp thụ tương quan giữa seed); seed 42 báo riêng để mô tả.
- Chỉ số track S (selector overlay): partial Spearman IC giữa X và Y_leg, khử tuyến tính theo rank(hạng S1), rank(điểm S1 nếu có), dummy năm.
- Power: TRƯỚC khi đọc Y CONFIRM, tính MDE80 của IC từ số cụm CONFIRM (dùng phương sai cụm EXPLORE). Ghi vào SELECTION.md. MDE > 0,08 ⇒ ghi cảnh báo "khả năng không có power", vẫn chạy.
- EXPLORE: kiểm hai phía mọi indicator + C_ALL + C_TOP5 + ML (C_TOP5/ML trên EXPLORE chỉ báo, không dùng làm kiểm). BH-FDR q = 0,10 trên các indicator đơn.
- Chọn sang CONFIRM (≤ 6 ứng viên, ghi vào SELECTION.md + commit TRƯỚC khi đọc Y 2024–25): tối đa 3 indicator FDR sống |IC| lớn nhất + C_ALL + C_TOP5 + ML. Không indicator đơn nào sống FDR VÀ C_ALL có p EXPLORE ≥ 0,20 ⇒ track S ĐÓNG ngay.
- CONFIRM — một ứng viên ĐẠT khi CẢ:
  (1) IC cùng dấu EXPLORE, CI90 cụm không chứa 0, Holm một phía α = 0,10 trên số ứng viên thực chọn;
  (2) điểm IC 2024 và 2025 đều cùng dấu;
  (3) kinh tế: VETO ngũ phân vị xấu nhất (cutpoint EXPLORE) ⇒ mean Y_leg nhóm bị loại < mean nhóm giữ, CI90 cụm không chứa 0, VÀ tổng PnL nhóm bị loại ≤ 0 ở CẢ 2024 và 2025.
- Track G (gate linh hoạt, chỉ market-level M1–M6 + C_ALL market = trung bình phân vị có dấu M1–M6):
  - G-relax: Δ = mean Y72(near-miss ∩ ngũ phân vị thuận) − mean Y72(phút pass B0). ĐẠT khi Δ ≥ 0 với CI90 dưới > −1 pp VÀ Y72(near-miss ∩ thuận) > 0 ròng, cả hai band [0,85;1) và [0,70;1), cùng dấu 2024 và 2025.
  - G-veto: Δ = mean Y72(pass ∩ ngũ phân vị nghịch) − mean Y72(pass còn lại) < 0, CI90 không chứa 0, cùng dấu 2024 và 2025.
  - Khử cụm, bootstrap như trên; Holm trên (6 market indicator + 1 tổ hợp) × 2 band. EXPLORE chọn tối đa 2 ứng viên.
- Lưu ý ghi trước: R5 cho thấy Y72 tốt có thể KHÔNG ra PnL ⇒ G ĐẠT chỉ là điều kiện cần cho Pha 1.

## §4 Pha 1 (CHƯA ĐƯỢC CHẠY — cần MASTER duyệt sau Pha 0)
Arm dự kiến cho ứng viên đạt: S-VETO (bỏ leg ngũ phân vị xấu, slot để trống trả lại cho ứng viên tiếp theo như sim tự nhiên), G-RELAX (mở gate near-miss khi thuận, so iso-count), G-VETO, K-FLEX (K = 32 khi thuận / 16 khi nghịch / 24 còn lại; chỉ nếu track G đạt). Cổng GO như R5P2/GATE_SMART: ΔCalmar > 0 ≥ 7/8 seed; maxDD không sâu hơn 2 pp; ΔCAGR22 ≥ −2 pp; ≥ 3/4 năm ΔPnL ≥ 0; futility sau 4 seed (≥ 2/4 ΔCalmar ≤ 0 ⇒ DỪNG); HO 2026 cùng dấu; khả thi live (tính được từ kline1m live, causal, parity). GO ⇒ chỉ forward shadow paper, KHÔNG đổi v1.2.

## §5 Tài nguyên + an toàn (BẮT BUỘC)
- Oracle: mọi job nặng qua `flock ~/claude_master/locks/oracle_heavy.lock`; trước khi chạy kiểm `free` mem_avail ≥ 4 GB và đĩa trống ≥ 15 GB, sai ⇒ chờ/DỪNG. `nice -n 19 ionice -c3`; giới hạn RAM tiến trình 3 GB (`systemd-run --user --scope -p MemoryMax=3G` hoặc `ulimit -v`); ≤ 4 worker. Tổng CPU Oracle Pha 0 ≤ 2 h. Dữ liệu mới ≤ 1,5 GB trong `~/claude_master/ind1114/`; xoá trung gian khi xong. Không chạy khi owner đang deploy (`pgrep -af 'owner_deploy|deploy_ingest|deploy_v12|update_watchdog'` có kết quả ⇒ chờ).
- Kaggle: việc đọc kline1m nặng (resample 1h/4h/1d) làm trên Kaggle, chia kernel theo năm, ≤ 4 kernel đồng thời, ≤ 12 kernel-giờ; dùng polars/pyarrow (pandas 1 luồng ~19 phút/tháng). enable_internet=false. Output nhỏ (parquet nến 1h + indicator theo leg) rồi tải về Oracle. Trước hết KIỂM KHO: nếu Oracle/Kaggle đã có nến 1h/1d OHLCV đủ 2022–2025 thì dùng lại, không resample.
- CẤM: chạm 242 / live / jar / cron; chạy sim mới; mở Y CONFIRM trước khi commit SELECTION.md.
- Bí mật: CẤM cat/grep/sed/cut/head/less trên *.env, tg.env, env.local, PrivateConfig*, keys*, conf/env.sh. Chỉ được `grep -oE '^[A-Za-z_][A-Za-z0-9_-]*'` (tên khoá) hoặc sha256 → 8 ký tự.
- Code Python dùng `logging`, cấm `print`.

## §6 Khoá + sản phẩm
1. Commit prereg này vào vz_e1_wt `docs/prereg/PREREG_IND_COMBO.md` (ghi hash + md5) TRƯỚC khi đọc bất kỳ Y nào.
2. Commit danh sách indicator sau khử trùng + MDE + SELECTION.md TRƯỚC khi đọc Y CONFIRM.
3. Kết quả: `docs/result/IND_COMBO_P0.md` (bảng EXPLORE, SELECTION, CONFIRM, track G, HO mô tả, tài nguyên đã dùng, verdict ĐÓNG / ĐỀ XUẤT PHA 1).
