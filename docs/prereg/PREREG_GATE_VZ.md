# PREREG_GATE_VZ — gate p15 + feature VZ cấp thị trường (taker flow / volume / OI / LS)

- Ngày chốt: 2026-10-17, TRƯỚC khi dựng feature, train hay chạy sim. Mọi thay đổi sau commit này = addendum có ngày, ghi lý do, viết TRƯỚC khi xem số bị ảnh hưởng.
- Phạm vi: **chỉ nghiên cứu**. KHÔNG đổi logic hệ cũ, KHÔNG đổi shadow 242 / jar / model live (lệnh owner 10-17). Nếu GO ⇒ ứng viên **v1.1**, việc áp dụng cần owner duyệt và reset cửa sổ shadow.
- Owner yêu cầu: "tỉ mỉ, tránh NO-GO trên phân tích mỏng" ⇒ có điều khoản mở rộng 16 seed (mục 6.3) thay vì kết luận vội khi CI chạm 0.

## 1. Giả thuyết

Gate p15 hiện tại (XGB market-level, 33 cột V3FULL: giá/biến động/breadth/funding/lịch) **không có** dòng lệnh chủ động (taker), khối lượng tương đối, và vị thế (OI, long/short). Trong cú sập, bán chủ động cạn kiệt + OI xả mạnh + LS lệch có thể báo điểm hồi 15' của giỏ coin thua tốt hơn. Nếu đúng, p15 mới chọn phút vào tốt hơn ⇒ CAGR/Calmar sim K24+skipFull tăng, ghép cặp theo seed.

Bằng chứng trước (để không lặp và không kỳ vọng quá):
- 06/2026 (TASK-018/026/041): OI/LS cấp thị trường lọt top importance của gate H1 (nhãn ret_24h / gate chặn-sập) nhưng **không generalize** (fold 2022 lift 0×). Nhãn và vai trò khác bài này (p15 = upside 15' của giỏ, dùng để chọn phút mua), nên chưa phải bằng chứng chết, nhưng là cảnh báo: importance ≠ tiền.
- 10-04 ABLATION: rank-IC không dự báo tiền ⇒ quyết định chỉ bằng sim.
- S1 selector: OI12/funding/LS_TAKER/OFI đều NULL ở tầng chọn coin (khác tầng gate).

## 2. Dữ liệu và căn thời gian (đã đo, không suy diễn)

- Store gate: Kaggle `chuyendinh/bdchain-gate-store/gate_dataset_full.csv` (tải 10-17 về `~/claude_master/gvz/store/`, md5 csv a1c78e2f…, 2.889.623 dòng). Bản `.csv.gz` gốc md5 4bde28cd đã bị xoá khi dọn đĩa. Kiểm đồng nhất ở D1 (mục 5).
- **Căn thời gian store (đo 10-17, 2022-03-01..03, n≈4.320):** `momentum1M` tại dòng T tương quan 0,866 với lợi suất nến 1m có **open time = T** của BTC (và 0,868 với ETH); với T−1: 0,10; T+1: 0,06 ⇒ feature V3FULL tại dòng T dùng nến mở lúc T (đóng lúc T+1m).
- ⇒ Feature VZ tại dòng T chỉ dùng nến 1m có open time **≤ T − 1m** (trễ thêm 1 nến so với V3FULL, cố ý để không khuếch đại bất kỳ lệch căn nào của nhãn). Snapshot metrics dùng `create_time ≤ T − 10m`: an toàn cho CẢ hai quy ước create_time của Vision (đầu/cuối cửa sổ, đổi 2024-03-04, không đồng nhất theo symbol — xem data_leak_oi_2026-09-03), không cần dò quy ước theo symbol-ngày.
- Nguồn: kline1m Vision UM toàn bộ symbol USDT (gồm coin đã huỷ niêm yết) 2021-01→2025-12 (`~/claude_master/gvz/k2021/` cho 2021-01..11, `~/vz_e1/raw/` từ 2021-12); metrics5m Vision `~/claude_master/rex/met/` (bắt đầu 2021-12-01). 2026 KHÔNG đọc cho tới bước HO.

## 3. Feature (chốt, không thêm/bớt sau khi xem kết quả)

Ký hiệu: tbq = taker_buy_quote, qv = quote_volume, nt = n_trades; cửa sổ w nến = các nến open time ∈ [T−w, T−1] phút. Universe tại mỗi phút = mọi symbol có nến ở phút đó với qv > 0.

**VZ-A (8 cột, chỉ kline):**
1. `vzTkr5` = Σtbq/Σqv toàn thị trường, w=5
2. `vzTkr15` — w=15
3. `vzTkr60` — w=60
4. `vzTkr240` — w=240
5. `vzTkrBtc15` = tbq/qv của BTCUSDT, w=15
6. `vzTkrMed15` = trung vị theo symbol của tbq/qv (w=15), chỉ symbol có Σqv(15) ≥ 10.000 USDT
7. `vzQvR60` = log( Σqv(60) / (Σqv(1440)/24) )
8. `vzNtR15` = log( Σnt(15) / (Σnt(1440)/96) )

**VZ-B (VZ-A + 5 cột metrics):** lưới 5m g(T) = floor((T − 10m)/5m)·5m; giá trị symbol tại g = snapshot có ts làm tròn xuống 5m = g (không có ⇒ symbol vắng ở g).
9. `vzOiC1h` = log( ΣOIV_g / ΣOIV_{g−1h} ), Σ trên symbol có mặt ở CẢ hai mốc
10. `vzOiC4h` — g−4h
11. `vzOiC24h` — g−24h
12. `vzLsTop` = log trung vị (symbol có OIV ≥ 1 triệu USDT) của sum_toptrader_long_short_ratio (vị thế top trader) tại g
13. `vzLsAcc` = log trung vị cùng tập của count_long_short_ratio (tài khoản toàn thị trường) tại g

Thiếu dữ liệu ⇒ NaN (XGB xử lý missing; không fill 0). VZ-B trước 2021-12 = NaN (Vision metrics bắt đầu 2021-12-01). Không winsorize (XGB dựa trên ngưỡng, bất biến đơn điệu); |log| vô cực (Σ=0) ⇒ NaN.

Loại trừ có chủ đích (để giới hạn số phép thử): basis/premium (A1 đã đóng), funding (đã có trong V3FULL), liquidation (UM không có lịch sử), bookDepth (độ phủ mỏng).

## 4. Arm, recipe, sim

- Arm `VA` = V3FULL + VZ-A (41 cột); arm `VB` = V3FULL + VZ-A + VZ-B (46 cột). Thứ tự cột: V3FULL rồi VZ theo thứ tự mục 3.
- Recipe y nguyên `gate_ablation_driver.retrain`: nhãn `label_oldbasket`, purge 15', 19 fold quý từ 2021-04-01, train cut theo UTC, OOS theo +07, XGB depth4/n150/lr0,05/sub0,8/col0,8/mcw10, n_jobs 4. Không HPO. Phần ≥ SEAL (2026-01-01 +07) giữ p15 gốc của pred.bin (như mọi vòng trước).
- 8 seed: 42, 7, 13, 21, 99, 123, 777, 2024.
- **Baseline ghép cặp** = cùng recipe, chỉ V3FULL, cùng seed, cùng jar/profile/override:
  - seed 7…2024: run `gqsf-s*` đã có (p15 python, ON).
  - seed 42: run gqsf-a1 dùng pred.bin Java (không cùng đường train) ⇒ chạy THÊM baseline `gvz-b42` = p15 G0 python (tái lập ở D1) với override ON. Ghép VA/VB seed 42 với `gvz-b42`, không với gqsf-a1.
- Sim: jar `sim-jar-gqsf` (sha256 0944841c…), profile `r4_kg0_k16_f015_g155` md5 0e0caef0…, override = `GA.B0OV` + `SELECTOR_RANK_TOPK=24` + `GATE_QUOTA_SKIP_WHEN_FULL=true`, sim_end 20251231, bundle như gqsf, kernel `tools/kaggle_sim.py` HEAD, khối `pred_ds`. Tag `gvz-va-<seed>`, `gvz-vb-<seed>`, `gvz-b42`. Tổng 17 sim.
- Parity mỗi run (thiếu 1 mục ⇒ run VOID, chạy lại, không chấm): jar sha, topk 24, key ON, B0OV, `pred_md5_used` = md5 pred của arm, `pred_md5_base` = 5dd6bb4c, ok=true, mapper ≥ 800.

## 5. Kiểm dữ liệu (phải PASS trước khi train; FAIL ⇒ sửa code dựng feature, không sửa định nghĩa)

- D1: G0 (seed 42, V3FULL) train lại từ store tải về: pearson với pred.bin ≥ 0,99 mọi fold (như 10-04), và so `gabl/p15_G0.npy`: max |Δ| ≤ 1e-6 (⇒ store và môi trường trùng vòng 10-04). Nếu chỉ đạt pearson mà không trùng bit ⇒ ghi nhận, dùng p15 G0 mới cho `gvz-b42`, tiếp tục.
- D2 phủ: VZ-A không NaN ≥ 99% dòng store 2021-01-02..2025-12-31; VZ-B ≥ 95% dòng 2021-12-02..2025-12-31.
- D3 nhân quả độc lập: 30 dòng T ngẫu nhiên (rng 20261017, rải 2021–2025), tính lại 13 cột bằng đường code thứ hai lọc trực tiếp parquet theo `open time ≤ T−1m` / `ts ≤ T−10m`; khớp ≤ 1e-5 tương đối.
- D4 trễ: tính lại vzTkr15 với trễ 0 (gồm nến T) và trễ 1; tương quan với `label_oldbasket` không được TĂNG mạnh khi bỏ trễ chỉ vì đó là biến thể không dùng — chỉ báo cáo (bằng chứng căn đúng: bản trễ 0 và trễ 1 lệch nhau đúng 1 nến).
- D5 sanity: vzTkr* ∈ (0,1); tương quan vzTkrBtc15 với momentum15M dương; số symbol universe theo năm báo cáo.

## 6. Quy tắc quyết định (DEV = 2022-01-01..2024-12-31; rebase 2021-12-31)

Chỉ số mỗi run (từ hạ tầng chấm `gate_skipfull_driver.score`, MTM legacy): CAGR_DEV, Calmar_DEV, maxDD_MTM_DEV, lợi suất năm 2022/2023/2024/2025, n lệnh/năm, phút gate-mở/năm. Δ = arm − baseline cùng seed.

### 6.1 GO một arm (tất cả):
- C1: mean ΔCAGR_DEV > 0 và cận dưới CI t ghép cặp **97,5%** (Bonferroni 2 arm; t_{0,9875;7} = 2,841) > 0.
- C2: ΔCAGR_DEV > 0 ở ≥ 6/8 seed.
- C3: mean ΔCalmar_DEV ≥ 0; mean ΔmaxDD_DEV ≥ −2pp (không sâu hơn quá 2pp); mọi seed |maxDD toàn kỳ| ≤ 40%.
- C4: không dồn 1 năm: mean Δ lợi suất năm > 0 ở ≥ 2/3 năm 2022–2024 và không năm nào mean Δ < −3pp.
- C5 (VAL 2025, đọc một lần): mean Δ lợi suất 2025 ≥ −1pp.

### 6.2 Chọn arm: nếu cả hai GO, chọn VA trừ khi mean ΔCAGR_DEV(VB) − mean ΔCAGR_DEV(VA) ≥ 1pp (VB phụ thuộc thêm nguồn OI/LS live).

### 6.3 Mở rộng một lần (chống NO-GO mỏng): nếu arm trượt C1 CHỈ vì cận dưới CI ≤ 0, trong khi mean ΔCAGR_DEV ≥ +1,5pp và C2 ≥ 5/8 ⇒ chạy thêm 8 seed (101, 202, 303, 404, 505, 606, 707, 808) cho arm đó VÀ baseline V3FULL của chúng (16 sim). Chấm lại trên 16 seed: C1 với t_{0,9875;15} = 2,490, C2 ≥ 12/16, C3–C5 như trên. Không mở rộng lần hai.

### 6.4 NO-GO: còn lại. Ghi rõ mean/CI/từng seed; không thử biến thể feature khác trong vòng này.

## 7. HO 2026 (một lần, chỉ arm được chọn nếu GO)

- Viết addendum TRƯỚC khi đọc bất kỳ dữ liệu 2026 nào: cách train mô hình HO (dữ liệu < 2026-01-01 +07, purge 15', 8 seed, arm vs baseline V3FULL), bundle/khoảng sim 2026 (dataset kline 2026 + store 2026), chỉ số.
- Tiêu chí (chốt bây giờ): mean ΔROI_HO ≥ 0 và ≥ 5/8 seed Δ ≥ 0. HO ngắn ⇒ đây là kiểm "không tệ hơn", không phải bằng chứng tăng.

## 8. Parity live (điều kiện ÁP DỤNG v1.1, không phải điều kiện nghiên cứu)

- Đã đo 10-17: đối tượng kline live `KlineObjectSimple` (Aerospike `kline_1m_opt`) chỉ có open/high/low/close/totalUsdt — **KHÔNG có taker_buy_quote và n_trades** ⇒ VZ-A cần mở rộng ingest 242 (stream kline WS có trường `Q`/`n`). VZ-B cần nguồn OI/LS live (có `LiveOiFeatProvider`/ingestor OI cũ; trạng thái chạy trên 242 chưa kiểm; điểm nối backfill↔forward chưa đo — data_leak_oi mục (b)).
- Nếu GO: (P1) xây ingest trên nhánh v1.1, ghi ≥ 14 ngày; (P2) so feature tính từ 242 với Vision cùng ngày: tương quan ≥ 0,99 mỗi cột, sai lệch p99 báo cáo; (P3) p15 live vs p15 offline tương quan ≥ 0,99. Thiếu P1–P3 ⇒ KHÔNG áp dụng dù GO.

## 9. Chẩn đoán báo cáo (không dùng để quyết định)

IC Spearman p15 vs nhãn theo năm (arm vs baseline); tỉ phần gain của cột VZ trong mỗi fold; phút gate-mở/năm và Jaccard phút với baseline; lợi suất các đợt sập lớn (2022-05, 2022-06, 2022-11, 2024-08-05, 2025-10-10).

## 10. Ngân sách và an toàn

17 sim (+16 nếu 6.3), 2 kernel song song tối đa toàn tài khoản; không Binance REST từ Oracle; không chạm 242 (chỉ đọc code repo); kiểm `df -h` trước mỗi bước lớn (dừng nếu < 500 MB); KHÔNG build/upload jar mới. Dùng lại dataset riêng tư `sim-jar-gqsf` (build 10-04, thuộc nhóm jar cũ CÓ THỂ chứa PrivateConfig thật — đã nằm trên Kaggle từ trước; 10-16 đã khuyên owner xoay key) để ghép cặp đúng với baseline gqsf. Không đọc, không in chuỗi khoá.


## Addendum 1 (2026-10-17 09:25, TRƯỚC khi có bất kỳ p15 VZ hay sim arm nào)

- **Nguồn giá MTM:** ticker bin cục bộ (`~/kaggle_data_hpo`) đã bị xoá khi dọn đĩa ⇒ `reset_rule_score.run_mtm` không chạy được. Thay bằng `research/gvz/gvz_mtm.py`: giữ nguyên toàn bộ logic run_mtm/MTMState, CHỈ đổi nguồn close 1m sang kline1m Vision. Kiểm: tái lập cache `gqsf/mtm.json` cho `gqsf-s7` và `gqsf-a1` — dd_total, uw, dd_year, uw_year, dd_win **trùng tuyệt đối** (−22,748916…/116,4667; −22,207383…/117,3278). MTM của MỌI run (arm và baseline) tính bằng cùng module này. Thêm cửa sổ `dd_dev` = [2022-01-01, 2025-01-01) cho C3.
- **D1 PASS:** G0 train lại từ store Kaggle trùng bit `gabl/p15_G0.npy` (max |Δ| = 0), pearson vs pred.bin min 0,9919 ⇒ store, recipe, môi trường (python3 hệ thống, xgboost 3.2.0) trùng vòng 10-04. Baseline seed 42 = `pred_B_S42` md5 b75efb61.
- CAGR_DEV và lợi suất năm tính từ `equity` daily của sim (`gate_skipfull_driver.cagr_from/year_ret`), giống vòng gqsf.

## Addendum 2 (2026-10-17 09:45, sau D2–D5 lần 1, TRƯỚC khi train arm VZ nào)

Lần kiểm 1: D2 PASS; D3/D5 FAIL. Nguyên nhân đã đo, đều là dữ liệu/độ chính xác, không phải định nghĩa feature:
- **Metrics 2021-01..11 chỉ có 1 symbol/tháng** (12/2021: 138 symbol) — file `rex/met/metrics5m-2021` có vài dòng trước mốc Vision 2021-12. Mục 3 đã chốt "VZ-B trước 2021-12 = NaN"; builder chưa áp ⇒ nay áp: VZ-B = NaN với T < 2021-12-02 (thêm 24h warm-up cho vzOiC24h, khớp cửa sổ D2 của VZ-B). Checker D3 cũng dùng mốc này theo T.
- **D3 sau 2021-12:** 4 ô lệch đều là vzOiC1h/4h giá trị ~1e-5 lưu float32; |Δ| ≈ 6e-9 nhưng tương đối 3e-4. Dung sai D3 sửa thành |Δ| ≤ 1e-5·(0,01 + |b|). VZ-A: 0 ô lệch trên 30 dòng.
- **D5 range:** 16 phút 2021-03-02 01:36–01:51 có vzTkr5/15 ≥ 0,999 và 1 phút 2025-08-29 06:33 vzTkrBtc15 = 1,0 — lỗi nguồn Vision (taker_buy ≈ volume). Giữ nguyên, không làm sạch (17/2,6 triệu dòng; XGB dựa ngưỡng). D5 range chuyển thành chỉ báo cáo.
- D4 (báo cáo): bản build trùng tuyệt đối biến thể trễ 1 (|Δ| 3e-8), lệch biến thể trễ 0 tới 0,17 ⇒ căn đúng. IC Spearman với nhãn tháng 2022-06: trễ 0 0,090 vs trễ 1 0,085 — không có dấu hiệu rò rỉ theo nến.
- Ghi nhận trước khi train (không dùng để chọn): IC Spearman toàn kỳ với nhãn — vzNtR15 +0,19, vzQvR60 +0,14 (ổn định 5/5 năm, nhưng có thể trùng thông tin với volumeSpike/volatility của V3FULL); vzLsTop +0,33 nhưng theo năm 0,23/−0,01/0,13/0,20/0,01 (không ổn định — nghi xu hướng cấp độ); taker ratio |IC| < 0,09.

## Addendum 3 (2026-10-17 ~09:55) — quyết định owner về áp dụng (không đổi phép đo)

Owner: "cứ chạy, không go-live; trừ khi K24 + skipFull có vấn đề sau shadow". ⇒ Kết quả vòng này chỉ là **ứng viên dự phòng**. Kể cả GO (gồm HO 2026) cũng KHÔNG đưa vào v1.1 và KHÔNG mở nhánh ingest live (mục 8), trừ khi shadow K24+skipFull trên 242 lộ vấn đề và owner yêu cầu. Quy tắc C1–C5, 6.3, mục 7 giữ nguyên.
