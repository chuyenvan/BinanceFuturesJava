# STRATEGY — Entry Alpha & Exit Monetization (nguồn sự thật chiến lược)

> Mục đích: mô tả chiến lược đang theo đuổi + thang validation + vị trí hiện tại.
> Phân biệt rõ **ĐÃ ĐO** vs **GIẢ THUYẾT** (nguyên tắc "đo không đoán").
> Viết 2026-07-26. Bổ trợ (không thay thế): `PIPELINE_PROVENANCE.md`, `STRATEGY_CONSOLIDATED.md`,
> `reports/153.md`, `reports/156.md`, `NEXT_SESSION_TODO_entry_alpha.md`.

---

## 1. Hệ thống nền

BinanceFuturesJava — **long-only, USDT-M perpetual, đòn bẩy 1x**. Mục tiêu ≥20%/năm ổn định,
validate qua thang lợi nhuận theo quý. Ba trụ:

- **Entry (selector)**: XGBoost chấm mỗi (coin, thời điểm) một điểm `P(win) = P(giá chạm +6% trong horizon H)`.
  Nhãn triple-barrier (`maxFav/maxAdv/tHitFav/tHitAdv/retEnd/nBars`), H ∈ {4h,12h,24h,72h}.
  Bản chất = **bộ xếp hạng cross-sectional**: "coin nào sắp bơm mạnh nhất".
- **Gate**: lọc regime/chất lượng — quyết định lúc nào được vào lệnh, coin nào đủ điều kiện.
- **Exit**: hiện tại **trailing, KHÔNG hard stop-loss**; entry kiểu martingale/DCA.

Đây KHÔNG phải chiến lược lướt/scalp theo thiết kế. Nó là **momentum ranking long-only**:
chọn coin sắp động đậy mạnh → giữ → exit quản lý đuôi.

## 2. Câu hỏi cốt lõi

> Entry có **ALPHA thật** (tách khỏi beta thị trường + artifact dữ liệu) không, và nếu có thì **monetize được** không?

Chưa xây/đổi model production. Giai đoạn hiện tại = **đo lường để quyết định**, chưa triển khai.

## 3. Chuỗi chẩn đoán — ĐÃ ĐO

1. **Selector là bộ dự đoán "spike" (maxFav), KHÔNG phải return.** Nhãn = chạm +6%, bỏ qua điểm thoát
   và drawdown. Dataset `wf-pred-ret2` — tên "ret2" là **nhầm lẫn lịch sử**, nhãn train thật = maxFav≥6%
   (xác nhận `reports/153.md`). Là 17-fold walk-forward leak-free, copy từ Oracle, không train lại.
2. **Kỹ năng xếp hạng CÓ THẬT.** Re-probe SMOKE trên universe **UNFILTERED** (bỏ gate top-10% |rate30m|):
   rankIC 0.18–0.23, LIFT 2.9–4.4 (fold OOS 2024Q2). Cao hơn hẳn subset thiên kiến (IC 0.078)
   → edge rank **không phải artifact extreme-mover**. Lần đầu tách sạch.
3. **NHƯNG rank skill KHÔNG thành return alpha ở endpoint.** Top-decile realized ≈ mua coin trung bình
   (alpha ~0; 12h hơi âm; winrate <50%). Cơ chế (`reports/153.md`): model giỏi đoán "sẽ chạm +6% lúc nào đó"
   nhưng đường đi tới đó **thường thọt sâu trước** (SL quét), và endpoint cố định rửa lãi/lỗ về trung bình.
   Edge co gần hết khi chuyển từ định nghĩa A (maxFav thô) sang B (SL+1% path thật).
4. **Direction này đã FAIL Java WFO thật** (ret2wf: 43.8% OOS-positive < 70%; maxFav3: 50%, Task 156).

**Kết luận đo được:** edge nằm ở **maxFav (cú bơm), KHÔNG ở endpoint**. Rank skill vô dụng cho PnL
nếu exit không bắt được cú bơm trước khi nó rút.

## 4. Chiến lược đang theo đuổi

Giữ nguyên selector (rank có giá trị), **dồn lực vào EXIT để biến rank skill thành tiền** —
ý tưởng "cắt lỗ / nuôi lãi" làm đúng cách:

- **Nuôi lãi**: khi coin đã bắt đầu bơm (trailing kích hoạt sau +3%), để chạy để bắt đuôi phải tới +6%+
  (phần MFE model dự đoán được). KHÔNG chốt sớm ở 3-4%.
- **Cắt lỗ thông minh**: KHÔNG SL cứng cắt sớm (chính nó bị cú thọt-trước-bơm quét, giết kèo thắng).
  Thay bằng trailing chỉ siết SAU khi có lãi (lock +1%) + time-stop ở edge horizon (4h) để không ôm lỗ dài.

Kèm đó **gate** đổi sang lọc regime **nhân quả** (không dùng regime look-ahead), né bear (nơi realized âm
bất kể chọn coin gì).

**Không** tách chiến lược song song / không cross-sectional-momentum-parallel (đã rejected: short-loser leg
là nơi lỗ tụ + phá bất biến long-only).

## 5. Thang validation (thứ tự — không nhảy bước)

0. **WFO sạch** — vá gate coverage 2021-2022 (Task 156 REVIEW; exit endpoint hiện tại → FAIL).
1. **Entry-alpha (ĐANG CHẠY)** — re-probe selectability trên UNFILTERED, walk-forward toàn quý
   (KHÔNG 70/30 recent). Kernel Kaggle `chuyendinh/reprobe-unfiltered-wf`.
2. **Track A** — nếu edge (dạng maxFav) ổn định: `ExportEventPath` (Java, path OHLC 1m sau event)
   + Python trailing sim (activate +3% / lock +1% / quét trail width) → **net EV top-decile sau cost + funding**.
   Đây là bước SINH-TỬ: biến rank skill thành PnL.
3. **Exit Machine v1** — time-stop 4h + trailing activate ≥3% + cấu trúc 3-trạng-thái.
4. **Re-label** selector theo triple-barrier phản ánh exit mới; **re-label gate** cho regime.
5. **A/B DCA** (no-DCA mặc định) → rồi mới **sizing/Kelly**.

## 6. Nguyên tắc ràng buộc (kỷ luật đo)

- Đo trên universe **unfiltered + walk-forward** (không subset thiên kiến, không 70/30 recent).
- **Pre-register** ngưỡng PASS trước khi nhìn số.
- Measure trong **pipeline Java thật** — backtest-lite rank KHÔNG transfer.
- Đo bằng **cơ chế thực thi thật** (SL+1% path / trailing), không phải retEnd endpoint.
- Trừ **cost + funding** trước khi kết luận (funding drag hold dài chưa trừ ở nhiều đo cũ).
- Long-only bất biến (short cần SL bắt buộc → loại).
- Phân biệt rõ **đã-đo** vs **chưa-chứng-minh**. Quyết định PnL là của Uni.

## 7. Vị trí hiện tại (2026-07-26)

- Export unfiltered XONG (2021-01→2026-07, 22 file, 737 coin, lưới 15m, FF_SAMPLE_RATE=0.5).
- Dataset Kaggle `chuyendinh/funding-tool1-features-unfiltered` ĐÃ push (features + symid_map.csv).
- Re-probe FULL walk-forward XONG (kernel `chuyendinh/reprobe-unfiltered-wf`, 18 fold 2022Q1→2026Q2, 4h+12h, v1 bỏ OI).

### VERDICT full (2026-07-26) — đo được
| Horizon | rankIC med | IC posfrac | LIFT med | alpha med | alpha posfrac | winrate | VERDICT |
|---|---|---|---|---|---|---|---|
| 4h  | 0.204 | **18/18** | 4.64 | +0.006% | 10/18 | 0.477 | WEAK |
| 12h | 0.265 | **18/18** | 2.86 | −0.030% | 7/18  | 0.481 | WEAK |

- **Selectability THẬT + CỰC ỔN ĐỊNH**: rankIC dương **18/18 quý**, IC med 0.20–0.27, LIFT 2.9–4.6.
  → edge rank không phải artifact, không phải fluke 1 quý. Đây là kết luận mạnh nhất của cả nhánh.
- **Endpoint alpha ~0 / coin-flip**: alpha med ≈ 0, chỉ dương ~40–56% quý, winrate <50%.
  → rank skill KHÔNG thành return ở endpoint. Đúng chẩn đoán "edge ở maxFav, không ở endpoint".
- VERDICT = **WEAK** cả 2 horizon (PASS_selectability, FAIL_alpha).

### Nhánh quyết định (đã resolve theo verdict)
→ Rơi vào nhánh "IC dương ổn định + alpha ~0" → **xác nhận edge nằm ở maxFav (spike)**.
→ Hành động kế (đề xuất): **Track A** — exit (trailing bắt spike) có biến rank skill thành net-dương
  sau cost/funding không. Cần path 1m (`ExportEventPath`, CHƯA có — phải build) HOẶC proxy triple-barrier (Track A-lite).

### QUYẾT ĐỊNH (Uni, 2026-07-26): DỪNG — chốt WEAK
Selectability thật + ổn định nhưng KHÔNG monetize được ở endpoint. Track A **PARKED** (chưa build).
Artifact resume: dataset `chuyendinh/funding-tool1-features-unfiltered`, kernel `chuyendinh/reprobe-unfiltered-wf`,
kết quả `reprobe_out_full/reprobe_unfiltered.json` (Oracle). Resume = build `ExportEventPath`+trailing sim HOẶC Track A-lite proxy.

## 8. Một câu tóm

Chọn coin sắp bơm mạnh (selector rank — đã chứng minh có skill trên unfiltered), giữ long-only 1x,
dùng exit trailing bắt cú bơm (không chốt sớm, không SL cắt trước bơm), gate lọc regime.
Edge entry là "coin nào sắp động đậy"; nó **chỉ thành tiền nếu exit bắt được đuôi phải**.
**Track A là phép thử sinh-tử** cho điều đó.

## 9. Lịch sử tài liệu
- 2026-07-26: tạo mới; VERDICT full re-probe (WEAK: selectability 18/18 quý, alpha ~0); Uni quyết DỪNG, Track A parked.
- 2026-07-26 (b): RE-ĐO sửa overlap (`reprobe-unfiltered-wf-dedup`) + short-probe (`short-probe-bottom-decile`). Xem `reports/reprobe_dedup_short_20260726.md`.
  * **Overlap KHÔNG phải artifact:** overlap thổi số event ~9–19× (113k→6–13k) nhưng xsecIC≈pooledIC (0.19–0.22) và 18/18 quý dương GIỮ NGUYÊN ở cả 2 mode; n_indep 176–427/fold. Selectability = THẬT, chắc hơn tưởng.
  * Endpoint alpha ~0 (dedup nhích âm), âm sau cost → WEAK confirmed. Spread top−bottom ≈ 0.
  * **Short bottom-decile NOT_VIABLE** (pnl sau SL −0.16%, 0–1/18 fold dương): coin điểm thấp underperform tương đối nhưng vẫn tăng tuyệt đối → short lỗ. Bottom-decile chỉ dùng gate/diagnostic, KHÔNG thành leg.
  * Code audit: lỗ hổng lớn nhất còn lại = fixed-H ≠ variable-hold exit (production). Next = Track A-lite + correlation test 3 tầng (endpoint / A-lite / Java WFO slice).
- 2026-07-27: Track A-lite (hard-SL first-touch, Kaggle) = CHẾT (mọi policy NO, best −0.32%/−0.43%, 0–1/18 fold dương); short-probe = NOT_VIABLE. oi_z gate screen (Kaggle `oiz-gate-probe`): veto_q50 12h alpha +0.055%, 12/18 quý dương, frequency sống (nhưng endpoint, chưa cost). **Trailing WFO 1m thật (`ce wfo_verify`, DCA off, funding on) = TÍN HIᡸU DƯƠNG ĐẦU TIÊN**: `wfo_ds_ret2wf_4h_ff` w8=+797(wfe1.36,169tr), w10=+411(wfe0.29,240tr), w12 fail-timeout. oi_z-veto CHỒNG (`wfo_ds_oiz75`) = frequency wall (ZERO/TOO_FEW, reject30/30). Xem `reports/trailing_oiz_wfo_20260727.md`. NEXT: WFO trailing full slice sạch 2023+ (TICKER_SOURCE=file, DCA off) → verdict; oi_z chỉ test lại dạng thay-gate.
- 2026-07-27 (VERDICT trailing full-slice): WFO trailing (DCA off, funding on, TICKER_SOURCE=file) w4–16: 9/10 window có-lệnh DƯƠNG nhưng **WFE median ≈0.24 < 0.5 = FAIL** (overfit), PnL dồn w15 (+7469), 7/13 window ZERO/TOO_FEW (frequency nghẽn). → trailing là hướng DƯƠNG duy nhất nhưng **WEAK, chưa PASS**. Trần thật = FREQUENCY/gate. Fanout Kaggle `trailfan` FAILED 9/16 (kernel đọc aerospike226, chưa wire hpo-ticker-daily file). Handoff đầy đủ: `reports/HANDOFF_20260727_entry_alpha.md`. NEXT: (1) gate/frequency (Task156 + MOM15 cùn), (2) chống overfit HPO, (3) oi_z thay-gate, (4) wire Kaggle file-ticker.
- 2026-07-27 (tối, GATE ABLATION — hồi sinh nhánh): hạ gate `MIN_MOMENTUM_15M` baseline(0.02284)→0.010 (fixed-genome N=1, DCA off, funding on, TICKER_SOURCE=file): %OOS-SUCCESS 46%→69% (75% ex-w16), net-EV +51%, PnL dàn khỏi w15 (68%→46%), **WFE median 0.68 (≥0.5 PASS), maxDD 26%** → trailing gần-PASS. Non-monotonic: gate→0/off = PHÁ HUỶ (BURN, maxDD 59%, −55k). **WFE 0.24 cũ = artifact HPO over-tightening** (cần N=30 confirm). FREQUENCY = trần ràng buộc (xác nhận). Close-branch NEXT#5 KHÔNG kích hoạt. Kaggle fanout self-contained (`java-run-lc` config→`TICKER_SOURCE=file`, parity w6 437.41/1.2052/56 khớp Oracle). Xem `reports/gate_freq_ablation_20260727.md`. NEXT: oi_z-thay-gate (build dataset, chạy Kaggle) + rebuild jar N=30 confirm + đóng window BURN/LOCK.
- 2026-07-27 (SỬA): claim "Kaggle thiếu ticker/path → trailing bắt buộc Oracle" = SAI. `hpo-ticker-daily` = ticker 1m intraday shard-ngày (1826 file, ~662 sym×1440'). → trailing WFO chạy được trên KAGGLE FLEET (fanout: java-run-lc + wfo-ds-ret2-4h-ff + hpo-ticker-daily), không bó Oracle. Cách scalable = `ce wfo_fanout` (2 Oracle + 5 Kaggle). Provenance: dùng v6 (07-13, post ghost-clean), không phải bản 07-04 stale.
