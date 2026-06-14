# TASK-024: Export funding LABEL per-coin (path thô → triple-barrier ở train) + validate — bước 1 funding model

- **status:** REVIEW — code DONE; RUN+validate **BLOCKED** (builder TASK-010 chưa chạy → set `symbol_lifecycle` rỗng). Bước 1 của funding model.
- **owner:** CCD-024 · **updated:** 2026-06-14
- **Liên hệ:** ADR-0011 (funding = SELECTOR per-coin: "coin NÀO sắp bơm"). Label cũ = first-passage maxPrice +6%/72h → thay bằng **triple-barrier**. Đây là H1-DATA của funding (tương đương TASK-012 cho gate).

## Nguyên tắc (học từ gate 012)
- **Export PATH THÔ, KHÔNG ép nhãn 3-lớp ở đây.** Mỗi `(coin, t)` xuất: `maxFavorable` = max((high(τ)/close(t)−1)) và `maxAdverse` = min((low(τ)/close(t)−1)) với τ∈(t, t+H], + thời điểm chạm. → train sẽ áp barrier X/Y + horizon (quét, KHÔNG re-export). Đúng ranh giới H1/H2.
- Per-coin (khác gate = aggregate). Sample theo cùng nhịp dùng cho serve (chốt: 15m? hay theo settlement funding? — ghi rõ).

## Universe + survivorship (BẮT BUỘC)
- PHẢI gồm coin đã die (coin sắp die = nhãn xấu, không được loại — nếu loại thì model học "mọi coin đều sống sót" = survivorship, vô dụng đúng lúc cần).
- Dùng `SymbolLifecycleManager.isAlive(symbol, t)` (TASK-010) để xác định coin có giao dịch tại `t` — KHÔNG đọc `DIED_SYMBOLS`. ⚠️ Phụ thuộc builder 010 đã chạy (set `symbol_lifecycle` có data); nếu builder CHƯA chạy → task này BLOCKED phần universe, báo ngay (đừng fallback DIED âm thầm).

## Yêu cầu
- Mỗi `(coin, t)`: `maxFavorable`, `maxAdverse`, `tHitFav`, `tHitAdv`, `retEnd` (close(t+H)/close(t)−1), `nBars` (đủ data trong H?). H đủ rộng để quét (đề xuất H_max = 72h, lưu path đủ suy nhiều H nhỏ hơn — hoặc lưu theo vài mốc).
- Nguồn: ticker `kline_1m_opt` (price). Look-ahead: path nhìn (t, t+H] cho LABEL (đúng — label được phép nhìn tương lai); FEATURE (task sau) mới phải ≤t. Ghi rõ tách bạch.
- Output: `outputs/funding_label.csv` (như `gate_return.csv`).

## Validate
- Phân bố `maxFavorable`/`maxAdverse` theo coin/năm; tỉ lệ (giả lập) chạm +6% trong 72h (đối chiếu trực giác cũ).
- Recompute ~5 (coin,t) bằng đường khác.
- Look-ahead: chỉ dùng bar trong (t, t+H]; bỏ (coin,t) thiếu data tới t+H (`nBars` thiếu → loại, không 0 giả).
- Bắt đúng coin bơm lịch sử (sample vài coin x100 lần): maxFavorable lớn đúng đợt bơm.
- Coin die: gần lúc delist `maxAdverse` âm sâu / data dừng — xác nhận universe có coin die.

## An toàn / tài nguyên
- Đọc-only ticker (226), ghi `outputs/`. Chạy 226. SLF4J. KHÔNG đụng live.

## Acceptance
- [~] `funding_label.csv` path thô per-coin, gồm coin die (qua lifecycle), 2021→nay. — **CODE XONG**, CHƯA chạy (BLOCKED builder 010).
- [~] Validate phân bố + recompute + look-ahead + coin-die. — **CODE XONG** (chạy cùng tool), CHƯA có số (BLOCKED).
- [x] KHÔNG ép nhãn 3-lớp (để train); KHÔNG đọc DIED (dùng lifecycle). — lưu path thô + snapshot 4 mốc H; universe qua `isAlive`, guard `loadedCount==0`.

## (Code điền) — `ExportFundingLabel.java` (commit pending) · compile PASS javac11
- **Sample nhịp + H + cột path:** nhịp **15m** (constant `SAMPLE_STEP_MS`; khớp sibling gate TASK-012, đủ mịn triple-barrier, nhẹ ~15× so nhịp-1m export feature cũ). Path bar = 15m (gộp 1m→15m: hi=max maxPrice, lo=min minPrice, close=close nến 1m cuối bucket). Mốc **H={4h,12h,24h,72h}** = {16,48,96,288} bước; H_MAX=288. **27 cột:** `tEpochMs,tDate,symbol` + mỗi H: `maxFav_H, maxAdv_H, tHitFav_H(phút), tHitAdv_H(phút), retEnd_H, nBars_H`. `close(t)` = close nến 15m tại bucket t; path chỉ nến (t, t+H]. **KHÔNG ép 3-lớp** — train quét X/Y + horizon từ path. Streaming per-coin (deque anchor ≤288), O(bars×288×coins), bộ nhớ thấp.
- **Universe qua lifecycle (builder chạy chưa?):** anchor tạo chỉ khi `SymbolLifecycleManager.isAlive(sym, t)` (gồm coin chết trong [firstSeen,lastSeen]); KHÔNG đọc DIED. ⛔ **Builder TASK-010 CHƯA chạy** (recon TASK-021 2026-06-14: set `symbol_lifecycle` rỗng) → thêm getter `loadedCount()`; tool DỪNG ngay nếu `==0` (BLOCKED, không fallback DIED âm thầm). isAlt = USDT-perp, loại BTC/ETH(vai gate)/BTCDOM/USDC/đa-tài-sản.
- **Validate phân bố/recompute/coin-die:** lớp `Validate` chạy sau export (trên 226): (a) phân bố maxFav/maxAdv p1/5/50/95/99 mỗi H + maxFav_72h theo NĂM; (b) tỉ-lệ giả-lập chạm +6%/72h (chỉ nBars_72h đủ) đối chiếu trực giác label cũ; (c) recompute ĐỘC LẬP 5 anchor (đọc lại 1m→15m đường khác, so maxFav/maxAdv_72h); (d) look-ahead inherent (nến (t,t+H], thiếu→giữ nBars thiếu KHÔNG 0 giả); (e) top-20 maxFav_72h (bắt coin bơm lịch sử); (f) đếm dòng nBars_72h thiếu + coin chạm thiếu-data + status lifecycle.
- **⛔ CHẶN tiếp theo (cần user/điều phối):** chạy `SymbolLifecycleBuilder` trên 226 (job nặng — TASK-010 REVIEW) → set `symbol_lifecycle` có data → MỚI chạy `java ... ExportFundingLabel` trên 226 (ghi PID/.run theo luật dọn-job), rồi soi log validate.
