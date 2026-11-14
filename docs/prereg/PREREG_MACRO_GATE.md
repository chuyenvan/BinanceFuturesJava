# PREREG_MACRO_GATE — bộ lọc regime vĩ mô liên thị trường (port nguyên ngưỡng từ HKUDS/AI-Trader) cho gate p15

Ngày: 2026-11-14 · Tác giả: MASTER · Thực thi: agent Opus (mới) · Trạng thái: Pha 0 (chỉ đo). Pha 1 (sim) CHỈ chạy khi MASTER duyệt.

## §0 Vì sao có prereg này + khai báo rủi ro
- Owner 11-14: "model lỗ không có nghĩa không có edge" ⇒ soi lại AI-Trader (repo d03ff6c, arXiv 2512.10971).
- Kết quả soi:
  1. "Edge" DeepSeek ở crypto (−12,18 % so với CD5 −14,30 %, 14 ngày, 1 lần chạy, 10 coin, ~2 lệnh) khớp số học với việc giữ tiền mặt (đỉnh 41 %) trong thị trường giảm = GIẢM EXPOSURE, không phải alpha chọn điểm vào. Phần "buy-the-dip" trùng với gate p15 đang có.
  2. Thứ CÓ THỂ là thông tin mới với hệ: module `service/server/market_intel.py::_build_macro_signals` — bỏ phiếu regime từ tài sản TradFi (QQQ, XLP, GLD, UUP) + BTC + giọng tin vĩ mô; và `_build_etf_flow_snapshot` (ước lượng dòng BTC ETF = % đổi giá × volume/avg5). Hệ hiện tại CHỈ dùng dữ liệu crypto; điểm yếu đã đo = REGIME (2022 ≈ 0, HO Q3 2026 âm). Chưa nhánh nào thử dữ liệu TradFi (khớp T6 REGIME overlay trong hàng đợi 10-31).
- Ưu điểm thiết kế: ngưỡng lấy NGUYÊN từ code bên thứ ba ⇒ không có bậc tự do tune của ta.
- Rủi ro khai trước:
  - HARKing: đã biết 2022 hệ ≈ 0 và 2022 QQQ giảm / USD mạnh ⇒ EXPLORE 2022–23 gần như biết trước; kiểm thật là CONFIRM 2024–25.
  - Regime tự tương quan theo ngày ⇒ số đợt độc lập rất nhỏ; bootstrap phải theo khối THÁNG, và đếm số episode regime.
  - Bài học IND_COMBO (7a1448ca): nhóm bị veto vẫn lãi ⇒ veto vô dụng. Tiêu chí kinh tế ΣPnL nhóm bị veto ≤ 0 là BẮT BUỘC.
  - Phụ thuộc live mới (giá đóng ETF Mỹ hằng ngày) nếu sau này dùng.
  - Ledger đa kiểm định ~130+; họ này 6 kiểm.

## §1 Baseline + dữ liệu
- B0, leg, cụm (đợt ≤ 60′), Y72 near-miss: Y HỆT IND_COMBO Pha 0 (prereg 14ed6c00, result 7a1448ca; tái dùng script đã commit, dựng lại bảng leg 8 seed). ts leg đổi sang UTC (printDone `start` là UTC+7).
- EXPLORE 2022-01-01..2023-12-31 · CONFIRM 2024-01-01..2025-12-31 · HO 2026-01..06 chỉ mô tả.
- Dữ liệu ngoài (tải trên Oracle, KHÔNG dùng API key, tổng < 20 MB): OHLCV ngày đã điều chỉnh (adjusted close) của QQQ, XLP, GLD, UUP, IBIT, FBTC, ARKB, BITB, HODL, BRRR từ 2021-10-01 đến 2026-06-30. Lấy 2 nguồn độc lập nếu tới được (vd stooq + Yahoo); đối chiếu return 20 phiên lệch ≤ 0,5 pp ở ≥ 99 % ngày; chỉ có 1 nguồn ⇒ ghi cờ `MOT_NGUON` và kiểm tay 10 ngày ngẫu nhiên với nguồn công khai khác. Không tải được ⇒ DỪNG báo MASTER.
- BTC ngày: từ kho kline sẵn có (nến ngày UTC đã đóng).

## §2 Tín hiệu (CỐ ĐỊNH — port nguyên ngưỡng AI-Trader, KHÔNG tune)
Tính mỗi ngày D từ nến ngày ĐÃ ĐÓNG. Phiên Mỹ ngày D và nến BTC ngày D chỉ được dùng cho quyết định từ 00:00 UTC ngày D+1 trở đi.
- S1 btc_trend: return BTC 7 nến ngày. ≥ +4 % bullish · ≤ −4 % defensive · còn lại neutral.
- S2 qqq_trend: return QQQ 20 phiên. ≥ +3 % bullish · ≤ −3 % defensive.
- S3 qqq_vs_xlp: (return QQQ 20 phiên − return XLP 20 phiên). ≥ +2 pp bullish · ≤ −2 pp defensive.
- S4 safe_haven: max(return GLD 20 phiên, return UUP 20 phiên). ≥ +3 % defensive · ≤ 0 bullish.
- (S5 macro_news_tone của AI-Trader: KHÔNG có lịch sử point-in-time nếu thiếu API key ⇒ BỎ ở prereg này — sai lệch khai trước.)
- V4 = phiếu trên S1–S4: bullish nếu số bullish ≥ số defensive + 2; defensive nếu số defensive ≥ số bullish + 2; còn lại neutral.
- V3 = như V4 nhưng chỉ S2–S4 (bỏ S1 vì S1 tương quan cơ học với chính cú sập kích hoạt gate).
- E (chỉ MÔ TẢ, dữ liệu có từ 2024-01): điểm dòng ETF = % đổi giá 1 phiên × (volume / TB volume 5 phiên trước), mỗi mã inflow ≥ +2,5 / outflow ≤ −2,5; tổng hợp inflow nếu số inflow ≥ số outflow + 2 và tổng điểm > 0 (ngược lại tương tự). Không có EXPLORE ⇒ không được làm ứng viên.
Họ kiểm (6): trạng thái defensive của S1, S2, S3, S4, V4, V3.

## §3 Thống kê Pha 0
Trạng thái gán theo phút ĐẦU của cụm. D = cụm/leg ở trạng thái defensive; N = phần còn lại.
- m1 = mean PnL % leg (D) − mean PnL % leg (N), gộp 8 seed. m2 = ΣPnL USD của leg D (trung bình theo seed).
- Bootstrap theo KHỐI THÁNG LỊCH 2 000 lần, seed 20261115, CI90.
- Báo kèm: % leg và % cụm thuộc D; số EPISODE (chuỗi ngày defensive liên tiếp có ≥ 1 cụm); bảng theo năm.
- TRƯỚC khi đọc Y CONFIRM: ghi số khối tháng, số episode CONFIRM của từng kiểm (chỉ dùng X) + MDE80 của m1 (phương sai khối EXPLORE) vào SELECTION.md.
- EXPLORE — ứng viên khi CẢ: m1 < 0 với CI90 không chứa 0; m2 ≤ 0; D chiếm 5–50 % leg; ≥ 4 episode. Chọn tối đa 2 ứng viên có m2 âm nhất. Không có ⇒ track R ĐÓNG.
- CONFIRM — ĐẠT khi CẢ: m1 < 0, CI90 khối tháng không chứa 0, Holm một phía α = 0,10 trên số ứng viên thực chọn; m2 ≤ 0 gộp 2024–25 VÀ ≤ 0 ở mỗi năm có ≥ 3 episode; ≥ 4 episode trong CONFIRM (ít hơn ⇒ "KHÔNG ĐỦ MẪU", coi như không đạt); D chiếm 5–50 % leg.
- Chiều bullish (tăng size khi thuận): CHỈ mô tả (owner 10-19 không muốn tăng size).
- Track G (gate linh hoạt): định nghĩa G-relax / G-veto Y HỆT IND_COMBO §3, thay "ngũ phân vị thuận/nghịch" bằng trạng thái bullish/defensive của V4 và V3 (2 kiểm × 2 band, Holm). EXPLORE chọn ≤ 1.
- HO 2026: bảng mô tả cùng định nghĩa, không dùng để quyết định.

## §4 Pha 1 (CHƯA ĐƯỢC CHẠY — cần MASTER duyệt)
Arm dự kiến cho ứng viên đạt: R-VETO (không mở leg MỚI khi defensive; DCA/exit giữ nguyên), R-HALF (size × 0,5 khi defensive), G-RELAX nếu track G đạt. Cổng GO như R5P2: ΔCalmar > 0 ≥ 7/8 seed; maxDD không sâu hơn 2 pp; ΔCAGR22 ≥ −2 pp; ≥ 3/4 năm ΔPnL ≥ 0; futility sau 4 seed; HO 2026 cùng dấu; khả thi live (nguồn giá ETF hằng ngày, fail-open khi thiếu dữ liệu, parity). GO ⇒ chỉ forward shadow paper, KHÔNG đổi v1.2.

## §5 Tài nguyên + an toàn (BẮT BUỘC)
- Oracle: `flock ~/claude_master/locks/oracle_heavy.lock`; trước mỗi job mem_avail ≥ 4 GB và đĩa trống ≥ 15 GB (sai ⇒ chờ/DỪNG); `nice -n 19 ionice -c3`; RAM tiến trình ≤ 2,5 GB (đặt MemoryMax/ulimit — lần trước đỉnh 3,04 GiB là vượt); ≤ 4 worker; CPU ≤ 1 h; dữ liệu mới ≤ 0,5 GB trong `~/claude_master/macro1114/`, dọn trung gian khi xong. `pgrep -af 'owner_deploy|deploy_ingest|deploy_v12|update_watchdog'` có kết quả ⇒ chờ.
- Kaggle: chỉ khi cần Y72 near-miss; ≤ 1 kernel, ≤ 2 kernel-giờ.
- CẤM: chạm 242 / live / jar / cron; sim mới; mở Y CONFIRM trước khi commit SELECTION.md; dùng API key.
- Bí mật: CẤM cat/grep/sed/cut/head/less/awk trên *.env, tg.env, env.local, PrivateConfig*, keys*, conf/env.sh, kaggle.json. Chỉ `grep -oE '^[A-Za-z_][A-Za-z0-9_-]*'` hoặc sha256 → 8 ký tự.
- Python dùng `logging`, cấm `print`.

## §6 Khoá + sản phẩm
1. Commit prereg này vào vz_e1_wt `docs/prereg/PREREG_MACRO_GATE.md` (hash + md5) TRƯỚC khi đọc Y.
2. Commit SELECTION.md (kiểm dữ liệu ngoài, tần suất trạng thái, episode, MDE, ứng viên) TRƯỚC khi đọc Y CONFIRM.
3. Kết quả `docs/result/MACRO_GATE_P0.md`: bảng EXPLORE 6 kiểm, SELECTION, CONFIRM, track G, mô tả E + chiều bullish + HO, tài nguyên, sai lệch, verdict ĐÓNG / ĐỀ XUẤT PHA 1.
