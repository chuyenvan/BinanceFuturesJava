# PREREG_SHORT_FEASIBILITY — SHORT có cửa không? (đảo hướng + đảo gate, PROXY 0-sim)

Chốt: **2026-09-30**, TRƯỚC khi chạy bất kỳ phép đo mới nào của vòng này. File này commit
**TRƯỚC** mọi commit script/kết quả (đúng `docs/runbooks/AGENT_RUNBOOK.md` luật 2; sai thứ tự
commit ⇒ kết quả **VOID**). Sau khi chạy **KHÔNG sửa thiết kế** (định nghĩa proxy, ngưỡng, cổng,
cách xử lý chi phí/funding, quy ước dấu).

Trạng thái: **ĐANG CHỜ ĐO** (khi xong ⇒ `docs/result/RESULT_SHORT_FEASIBILITY.md`).

Owner 2026-09-30: *"đo ngược hướng và ngược gate xem short có cửa nào để triển khai không … cần
pred 1 tập riêng check cho short"*.

---

## 0. Câu hỏi + tiên lượng ghi TRƯỚC

**Câu hỏi:** chiều SHORT có cửa nào (carry / down-signal / rank-short / reverse-gate) đủ để
**build** (dựng lại đường SELL + pred/gate riêng) không?

**Bối cảnh (đã có, không đo lại):** engine hiện **LONG-ONLY**
(`research/SimulatorMarketLevelTicker1MStopLoss.java:375` — `{ // co ENABLE_SHORT da go 2026-09-03 }`;
entry `OrderSide.BUY`). Baseline long `G2+FLAT3` (`profiles/g2_flat3.properties`) PASS 4 tầng §9
(`docs/decisions/0013-giu-g2-chuyen-ofi.md`). ⇒ Muốn short **phải sửa code**, không phải config.

**Tiên lượng (ghi trước, không sửa sau khi thấy số):** **NO-GO** — vì (i) sổ long sống bằng
**chuyển động GIÁ lên** sau khi mua-đáy (bằng chứng `RESULT_*` về MOM15/reversal-bounce), nên
đảo chiều tại cùng điểm vào sẽ **âm đối xứng**; (ii) carry short đã đo **NO-GO** (`RESULT_SHORT_CARRY`),
hedge overlay **NULL** (`RESULT_HEDGE_OVERLAY_A`), down-signal **NO-GO** (`RESULT_BIGUP_MEDIUPDOWN`);
(iii) chi phí (fee+slip+funding) ~0,15–0,31 %/chu kỳ > mọi gross đo được. Điều kiện tôi bị chứng
minh sai = §4 (cổng GO).

---

## 1. Ràng buộc (CỨNG)

1. **CHỈ ĐỌC + proxy 0-sim** — KHÔNG sim/train, **KHÔNG sửa `.java`**.
2. KHÔNG chạm production/242/ONNX/LIVE.
3. KHÔNG push file dữ liệu; chỉ push `.md`/`.py`/`.json` tổng hợp.
4. **DEV ≤ 2025-12-31**; KHÔNG chạm 2026 (seal).
5. Disk `/` ~95 % ⇒ nhẹ; **KHÔNG dùng CPU lớn** (có tiến trình khác đang chạy).
6. Output tool nhỏ; commit sớm + push.

---

## 2. Nguồn dữ liệu (đã có, chỉ đọc)

| Ký hiệu | Nguồn | Nội dung |
|---|---|---|
| `G2ART` | `/home/ubuntu/kaggle_sim/out/de-p1` | artifact run **G2** thật: `result.json` (n 2517, eq 131 908), `storage/printDone.csv` (2517 lệnh BUY đã đóng) |
| `S1PANEL` | `/home/ubuntu/ledger/pred_s1a2x1.parquet` (6,57 M dòng) | score selector S1 (`score=−s1`), 2021-12-31..2025-12-31 |
| `CLOSES` | `/home/ubuntu/java/fsrun/CLOSES_1H.bin` | close 1h per coin, 627 sym, ≤2026-01-01 |
| Tham chiếu | `docs/result/RESULT_SHORT_CARRY.md` (`edd1e70`), `RESULT_HEDGE_OVERLAY_A.md` (`03c037e`), `RESULT_BIGUP_MEDIUPDOWN.md` (`5102899`), `RESULT_FUNDING_TOPK_ROTATE.md`, `RESULT_FUNDING_SIGN.md`, `RESULT_S1_RANK_QUALITY.md`, `RESULT_REVERSAL_BOUNCE.md`, `RESULT_PUMPDUMP_DETECT.md`, `RESULT_ALT_REGIME_WAVES.md` | — | bằng chứng đã công bố (dùng cho INVENTORY, KHÔNG đo lại) |

**Chi phí (khóa, lấy từ `profiles/g2_flat3.properties`/`config.properties`):**
`SIM_RATE_FEE=0.000982`/chân, `SIM_SLIPPAGE_RATE=0.000067`/chân
⇒ **`fee_rt = 2×0,000982 = 0,1964 %`/vòng**, **`slip_rt = 2×0,000067 = 0,0134 %`/vòng**.
Quy ước dấu: `rate > 0` ⇒ long TRẢ / short THU (`RESULT_FUNDING_SIGN` §0–§1, đã kiểm 2 tầng).

---

## 3. Các PROXY sẽ đo (định nghĩa khóa, chạy một lần)

### P1 — ĐẢO CHIỀU TỪ THẾ (counterfactual short trên tập lệnh long của `G2`)

- Tập: 2517 lệnh long đã đóng trong `G2ART/storage/printDone.csv` (`side=BUY`).
- **Mirror giá:** cùng giá vào `entry`, **thoát tại ĐÚNG giá thoát `tp` của long** ⇒
  `ret_short_price = −ret_long_price` với `ret_long_price = tp/entry − 1`.
  ⚠️ **XẤP XỈ, nói rõ:** trailing/stop-loss của short là **path-dependent khác** long; mirror
  tại cùng giá thoát **không** tái tạo được đường đi. Đây là **đối chứng đảo dấu**, không phải
  short chạy được live.
- **Net (USDT):** `net_short = Σ(−pnl_long) − 2×Σ(notional×(SIM_RATE_FEE+SIM_SLIPPAGE_RATE))`,
  `notional = quantity×entry`. (Suy trực tiếp: `Σpnl_long = ΣP_long+ΣF_long−Fee`; short đối xứng
  `Σ(−P_long)+Σ(−F_long)−Fee` ⇒ hiệu hai sổ `= −2×Fee` ⇒ `net_short = −Σpnl_long − 2×Fee`.)
- Dấu funding tự lật: `F_short = −F_long` (không cần đo thêm).
- Báo cáo: `Σpnl_long`, `net_short`, win% short (= lệnh có `ret_long_price<0`), tách theo năm.

### P2 — ĐẢO GATE (S1 score: short ở decile cực trị)

- Panel: `S1PANEL` join `CLOSES` (snapshot 1h, như `research/analysis/s1_rank_quality.py`,
  `min_n=10`; decision `t ≤ 2025-12-31 00:00`).
- `s1 = −score` (cao = được S1 ưu tiên = **long pick**). Chia **decile** theo `s1` mỗi snapshot.
- **Hai cách đọc đảo gate đều chốt trước** (chống post-hoc):
  - **P2a**: short **decile 0** (s1 thấp nhất = bị S1 xếp "tệ nhất");
  - **P2b**: short **decile 9** (s1 cao nhất = chính là long pick ⇒ đảo dấu gate).
- Chất lượng = **mean forward return** `ret{1,4,24}h` per decile + `n_snapshot`, `n_obs`.
  Báo **toàn decile 0..9** (không chọn sau khi thấy số).
- **Bối cảnh bắt buộc giải quyết:** `RESULT_S1_RANK_QUALITY` có **mâu thuẫn nội tại giữa dấu
  `rank_ic` (âm) và bảng quintile (Q4 cao nhất)** ⇒ phép đo P2 **tự tính lại** IC và decile để
  chốt dấu (không chép doc cũ).

### P3 — ĐỐI CHIẾU CHI PHÍ (benchmark)

- Với `G2ART`: `fee_rt`, `slip_rt` ở trên; so với gross trung bình/lệnh.
- Với carry: dùng số `RESULT_SHORT_CARRY` (funding thu **+0,0251 %/chu kỳ 8h**, cost
  **0,1599 %/chu kỳ**, cost/gross **810 %**) làm mốc — **không đo lại**.

---

## 4. LUẬT KẾT LUẬN (khóa TRƯỚC)

**GO** (có cửa để build) **chỉ khi** thoả **ít nhất một** điều kiện:

| # | Điều kiện GO | Nguồn |
|---|---|---|
| G1 | `net_short` (P1) **> 0** (USDT, sau fee+slip+funding) | P1 |
| G2 | tồn tại decile `d` ở P2 với `mean ret24h(d) ≤ −(fee_rt+slip_rt) = −0,2098 %` **VÀ** cùng dấu âm ở **≥3/4 năm** (2022–2025) | P2 |
| G3 | carry short (đã đo) có biến thể net > 0 — **phản chứng**: đã NO-GO ⇒ không đạt | P3 (`RESULT_SHORT_CARRY`) |

**NO-GO** nếu **cả G1 và G2 đều FAIL**. Không có "vùng xám": không đề xuất build nếu chỉ "gần dương"
hoặc chỉ dương ở một năm — luật bền vững y như `RESULT_BIGUP_MEDIUPDOWN`.

**Kết luận bắt buộc dứt khoát:** `GO` hoặc `NO-GO/NULL` (kèm số). Nếu `NO-GO` ⇒ **đóng hướng short**
cho tới khi có **DATA MỚI** (liquidation feed / orderbook L2 / fill thật) — dữ liệu hiện tại
(close 1h/1m + funding) **không** đo được squeeze/liquidation, vốn là rủi ro chính của short.

Cổng phụ (không quyết định): nêu lại **chi phí build** (số file/dòng phải sửa để dựng đường SELL +
pred/gate riêng) và **rủi ro cấu trúc** (squeeze/funding/borrow) — dẫn số đã có, không đo mới.

---

## 5. Sản phẩm

| File | Nội dung |
|---|---|
| `docs/prereg/PREREG_SHORT_FEASIBILITY.md` | file này (commit TRƯỚC đo) |
| `docs/result/RESULT_SHORT_FEASIBILITY.md` | kết quả + INVENTORY + trả lời 4 câu |
| `research/analysis/short_feas_proxy.py` | P2/P3 (S1 decile + IC, 0-sim) |
| `research/analysis/short_feas_reverse.py` | P1 (counterfactual short trên `G2ART`), 0-sim |
| `docs/result/RESULT_SHORT_FEASIBILITY.json` | số tổng hợp (nhỏ) |
