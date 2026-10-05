# PREREG_SHORT_V3_R3 — Breakdown momentum (cascade xả)

Ngày 2026-10-02 · Chương trình: `docs/research/PROGRAM_SHORT_V3.md` @ a8eff3fb §R3 · Executor: research agent · MASTER: Claude.
Pre-reg này commit TRƯỚC khi đo bất kỳ outcome nào. Chưa chạy gì trên dữ liệu forward. Harness tái dùng: P0A
(`research/analysis/short_v2_p0a_statemap.py`, pre-reg `PREREG_SHORT_V2_P0A.md` @ 07d9e335, kết quả `c7a6f4d7`).

Câu hỏi: coin vừa phá đáy 30 ngày với volume gấp đôi và rơi ≥5% trong ngày có tiếp tục giảm (cascade xả) đủ để short
có lãi, và có TÁCH khỏi ALL cùng ngày không (điều P0A fail: excess_7d mọi trạng thái |≤0,28%|).

## 1. Chép nguyên §R3 chương trình (ngưỡng KHÓA)
Trạng thái BRK tại ngày d (causal): `close_d ≤ min(close[d-30..d-1])` (phá đáy 30 ngày) VÀ `quoteVol_d ≥ 2 × median quoteVol[d-30..d-1]`
  VÀ `close_d / close_{d-1} − 1 ≤ −0,05`. Cooldown 7 ngày/coin.
Giữ T ∈ {3d, 7d} (k=2), SL +10% (1h), phí 0,112, funding exact. Đối chứng: ALL cùng ngày; và BRK-không-volume (chỉ phá đáy) để tách vai trò volume.
Báo: như P0A (bleed, pSQ10, netproxy, cover, theo năm, CI raw/inflate 1,18) + excess vs ALL cùng ngày.
GO-R3 ⇔ netproxy_T > +0,5% ngoài CI raw & inflate; ≥3/4 năm; excess vs ALL > +0,3%; pSQ10 ≤ 0,8 × pSQ10(ALL).

## 2. Nguồn dữ liệu (y hệt P0A §4, chỉ đọc)
- Daily close ngày d = `CLOSES_1H.bin` tại ts = (d+1) 00:00 UTC; đường giá forward = 1h closes cùng file.
- quoteVol ngày UTC = cache `~/claude_master/1002/p0a_cache/qv/*.parquet` (Aerospike `kline_1m_opt`, Σ totalUsdt 1440 phút;
  stage `qv` của P0A; CHỈ ĐỌC, không tạo lại). Universe ngày d = symbol có trong cache ngày d.
- Funding exact: `/tmp/fund_cache.npz` qua `funding_cum` của P0A (short NHẬN khi rate > 0; Σ rate có ts ∈ (t0, t_exit]).
- Tập coin như P0A: `*USDT`, không `_`, loại BTCUSDT (vẫn trong mẫu số) và 5 stable. tier, bull: hàm `compute_states` của P0A
  (tier = tercile quoteVol mean 30d [d-29..d] cross-section; bull = BTC close > SMA50).
- Không đọc 2026: forward chỉ giữ lệnh có t0 + 24T h ≤ 2026-01-01 00:00 UTC.

## 3. Triển khai chỉ báo (chốt trước khi đo; chỉ dùng ngày ≤ d)
Lưới ngày lịch đầy đủ, ngày thiếu = NaN.
- `lo30_d` = min(close[d-30..d-1]); yêu cầu ĐỦ 30/30 close hợp lệ. `r1_d` = close_d/close_{d-1} − 1 (cả 2 hợp lệ).
- `mqv_d` = median(quoteVol[d-30..d-1]) trên các giá trị hợp lệ > 0, yêu cầu ≥ 20/30; `quoteVol_d` hợp lệ > 0.
- **Coin-ngày hợp lệ (E)** = close_d, close_{d-1}, lo30_d, mqv_d, quoteVol_d đều hợp lệ, d ∈ [2022-01-01, 2025-12-31].
- `raw_BRK` = E ∧ close_d ≤ lo30_d ∧ quoteVol_d ≥ 2·mqv_d ∧ r1_d ≤ −0,05.
- `raw_BNV` (BRK-no-vol) = E ∧ close_d ≤ lo30_d ∧ r1_d ≤ −0,05 (không điều kiện volume; ⊇ raw_BRK).
- **Cooldown 7 ngày/coin** (tách riêng cho BRK và BNV): duyệt d tăng dần trong DEV; entry tại d nếu raw và không có entry
  cùng coin tại d−1..d−7 (tức ngày d+1..d+7 sau một entry bị chặn, d+8 được phép). Chuỗi cooldown bắt đầu 2022-01-01
  (sự kiện trước DEV không tính). Cooldown chỉ chặn ENTRY; raw ngày bị chặn vẫn đếm trong sanity.
- **ALL** = mọi coin-ngày E (không cooldown, không điều kiện nào thêm) — rổ đối chứng cùng ngày.
- cover = n_entry / n coin-ngày E (DEV); báo cả cover của raw (trước cooldown).

## 4. Lệnh và outcome (y hệt P0A §5)
Đơn vị = coin-ngày BRK sau cooldown: short tại close ngày d (t0 = (d+1) 00:00 UTC, P0 = daily close), T ∈ {3, 7} ngày,
exit t0 + 24T h. Đường 1h c_k, k = 1..24T. `retEnd_T` = c_{24T}/P0 − 1 (NaN ⇒ close hợp lệ cuối, đếm `n_trunc`; không có
close forward ⇒ loại). `maxFav_T` = max c_k/P0 − 1. SL: giờ đầu tiên c_k ≥ 1,10·P0 (⇔ pSQ10), exit tại giờ đó.
`fund` = Σ rate (t0, t_exit]. `pnl = (−retEnd nếu ¬SL; −0,102 nếu SL) − 0,00112 + fund`; `netproxy_T` = mean(pnl).
Thêm (CHỈ báo cáo): `pnl_noSL = −retEnd_T − 0,00112 + fund_full_T` (giữ hết T, không SL) — phần bleed thuần.
`bleed` = mean/median retEnd_T thô. `excess` (dấu P0A) = retEnd_T − mean retEnd_T của ALL cùng ngày d cùng T;
**`excess_short` = −mean(excess)** (dương = BRK rơi MẠNH hơn rổ cùng ngày, tốt cho short). Báo thêm excess theo pnl
(pnl − mean pnl ALL cùng ngày) chỉ để tham khảo.

## 5. CI
Bootstrap khối 7 ngày lịch liên tiếp (theo ngày entry, khối b = (d − 2022-01-01)//7), NREP 2000, seed 20260905, thống kê
= Σpnl/Σn của các khối rút (pooled mean) — hàm `ci_block` P0A. CI raw = percentile 2,5/97,5.
**Inflate k=2 → hệ số 1,18**: CI_infl = mean − (mean−lo)·1,18 ; mean + (hi−mean)·1,18 (NỚI 18%). Ghi chú: công thức P0A
z_k/1,96 với z_2 = √(2 ln 2) = 1,177 cho hệ số 0,60 (THU HẸP CI) — không bảo thủ, KHÔNG dùng; chương trình ghi "inflate
1,18" ⇒ hiểu là nhân nửa-độ-rộng 1,18. Chọn TRƯỚC khi đo, không đổi.

## 6. Luật GO-R3 (áp cơ học; chọn diễn giải TRƯỚC khi đo)
Ứng viên = BRK tại T=3 và T=7 (k=2). BNV và ALL chỉ là đối chứng (không được GO). Một ô (BRK, T) PASS khi đồng thời:
- G1 `netproxy_T` (toàn DEV) > +0,5%;
- G2 cận dưới CI RAW > 0 VÀ cận dưới CI INFLATE > 0 (cùng diễn giải "ngoài 0" như P0A C3);
  (báo thêm, KHÔNG dùng cho verdict: cận dưới > +0,5%);
- G3 ≥ 3/4 năm (2022–2025, theo năm entry) có `netproxy_T` > 0 ("năm dương"); (báo thêm số năm > +0,5%);
- G4 `excess_short` toàn DEV > +0,3%;
- G5 pSQ10(BRK,T) ≤ 0,8 × pSQ10(ALL,T), ALL = gộp mọi coin-ngày E toàn DEV cùng T (nghĩa đen chương trình);
  (báo thêm, KHÔNG dùng: pSQ10 ALL khớp ngày = trung bình pSQ10 rổ ALL các ngày có BRK, trọng số theo số BRK).
GO-R3 ⇔ ≥1 ô PASS. Thiếu 1 điều kiện ⇒ ô đó NO-GO. n BRK quá nhỏ không tự là điều kiện nhưng báo.

## 7. Sanity BẮT BUỘC (in TRƯỚC bảng chính)
- S-a: n coin-ngày E theo năm; n raw_BRK / BRK sau cooldown / raw_BNV / BNV theo năm; số ngày lịch có ≥1 BRK; max BRK/ngày;
  n_trunc; % lệnh có funding; n lệnh có tier NA.
- S-b causal (như P0A): với 3 ngày cắt 2022-06-15, 2023-09-01, 2025-03-10, thay toàn bộ close/quoteVol SAU ngày cắt bằng số
  ngẫu nhiên, tính lại E, raw_BRK, raw_BNV, entry sau cooldown, lo30, mqv, r1; assert mọi ngày ≤ ngày cắt GIỐNG HỆT. Fail ⇒ dừng.
- S-c: in 10 BRK mẫu (rải đều theo thứ tự thời gian): ngày, coin, close_{d-1}, close_d, r1, lo30, quoteVol_d/mqv, tier,
  retEnd_7, maxFav_7, SL. Kiểm tay điều kiện đúng.
- S-d: SL ⇔ maxFav ≥ 10% (đếm lệch); BRK ⊆ BNV (assert); BRK sau cooldown không có 2 entry cùng coin cách ≤ 7 ngày (assert).

## 8. Bảng đầu ra cố định
- **A** [BRK, BNV, ALL] × T ∈ {3,7}: n, cover, bleed mean/median, excess_short (bleed), excess pnl, pSQ10, pSQ20, P(ret≤−10%),
  funding mean, SL-rate, netproxy, CI raw, CI inflate, netproxy_noSL (+ CI raw), số năm dương / năm > +0,5%.
- **B** theo năm 2022–2025: mỗi [nhóm × T]: n, bleed mean, excess_short, pSQ10, funding, netproxy, netproxy_noSL (+ CI raw T=7).
- **C** BRK theo tier (LỚN/VỪA/NHỎ) và theo bull/¬bull, T ∈ {3,7}: n, bleed, excess_short, pSQ10, netproxy, CI raw — CHỈ
  báo cáo, không chọn lát.
- **D** phân rã netproxy (như P0A G): −bleed, SL-convexity, funding, phí.
- **E** bảng GO G1..G5 cho (BRK,3), (BRK,7) → verdict.
Output: `research/analysis/short_v3_r3_breakdown.py` (import hàm P0A, không sửa file đó) → `docs/result/RESULT_SHORT_V3_R3.json`
+ `.md`. Không cache mới trong repo.

## 9. Cấm
Không đổi ngưỡng BRK (30d, 2×, −5%), cooldown, T, SL, phí sau khi thấy số; không thêm lát/biến thể/T; không chọn tier/regime.
"Giá như đổi X" ⇒ mục "đề xuất amend", KHÔNG chạy. Không đọc 2026. Không Java. Không sửa `.java`. Không chạm 242.
Lock `~/claude_master/1002/oracle_heavy.lock` cho job; nếu lock của job khác tồn tại chỉ chạy khi `free -g` available ≥ 10G.
Giới hạn biết trước: SL/maxFav trên 1h closes = cận dưới squeeze, SL khớp đúng +10,2% ⇒ netproxy lạc quan (P0A: SL-convexity
chiếm phần lớn netproxy LIQ) ⇒ báo netproxy_noSL bên cạnh.
