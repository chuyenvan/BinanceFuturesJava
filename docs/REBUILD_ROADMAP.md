# REBUILD ROADMAP — data + 2 model (market gate + funding selector) + hạ tầng

> Bản đồ sống cho mạch rebuild (ADR-0009): backfill data, lifecycle/validate/pipeline, **cả hai model** (market gate = ADR-0010, funding selector = ADR-0011), tích hợp. Chi tiết quyết định ở các ADR; file này là tuyến đường + trạng thái.

## Vì sao rebuild (ADR-0009)
- Training data méo (thiếu coin die → feature avg-top100-sập + label lệch) → đo model trên đó vô nghĩa.
- Code train cũ mất (chỉ còn ONNX) → không tái tạo/không vá drift được → train lại bằng pipeline kiểm soát; **ONNX = baseline so sánh**.
- Mục tiêu: **"đủ tốt + biết trần edge"**, KHÔNG cầu toàn (edge market mỏng, x1.21 rule).

---

## P1 — Backfill đủ data (TASK-005)
Fill ticker coin sập/chết → re-export 100% training data. Chỉ ticker, không prediction.
- **Phạm vi:** lọc DD-từ-đỉnh (`minClose/maxClose`) ≥ 60% (KHÔNG dùng cột `drawdownToBottom` — sai từ firstOpen). ~30 coin.
- **An toàn:** 242 live chỉ dùng ~2 ngày gần; lịch sử xa fill thoải mái. Fill 226 → audit → 242.
- **Trạng thái:**
  - Pilot LUNA: PASS (id 760, giá khớp, coin khác bit-nguyên).
  - Mẻ 1 đợt A (ANC/SRM/DODO/HNT/AUDIO): PASS.
  - Đợt A còn lại (id 766–779): GỘP, đang/duyệt chạy, audit per-coin.
  - **Re-validate** coverage (đang chạy): tìm sym thiếu MỚI ngoài 36.
  - Đợt B (10 coin còn niêm yết): CHỜ — cần xác định mốc live mỗi coin, chỉ fill lịch sử xa.
  - **B6:** BỎ re-export feature cũ → chỉ sample-check survivorship (feature cũ đổi). Export feature MỚI = H1/P2, 1 lần sau cụm hạ tầng + code feature mới.

---

## P2 — Model mới (làm sau khi P1 backfill xong + cụm hạ tầng)

### Market = GATE (ADR-0010) — thiết kế ĐÃ CHỐT
- **Nhiệm vụ:** gate thị trường (cho mở long mới + điều tiết mức), KHÔNG chọn coin.
- **Label:** classification 3 lớp — forward return H (close-to-close): `giảm ≥X%` / trung tính / `tăng ≥X%`.
- **Phạm vi:** thị trường rộng (BTC+ETH+breadth+funding+regime).
- **Features:** lõi breadth/funding/volatility/momentum-tỉa; **bỏ time** (overfit); candidate (SMA tương đối, alignment ngắn-dài/bear-rally, regime bull-bear line, ETH-mom, đồng-pha BTC-ETH) → để selection tỉa.
- **Việc CẦN DATA (chưa làm):**
  - Quét **H ∈ {4,12,24h}, X ∈ {−15,−20%}**.
  - **Feature-selection / importance** — làm ĐÚNG: permutation/SHAP trên **held-out walk-forward** (KHÔNG train, KHÔNG CV ngẫu nhiên); **gom nhóm tương quan** (BTC/ETH-mom…) permute/drop theo nhóm; đo ổn định nhiều fold/seed. Mục đích: phát hiện leakage + tỉa thừa, KHÔNG suy nhân quả.
  - Xử **imbalance** lớp "giảm mạnh" (thiểu số, quan trọng nhất).
  - **Cổng:** model phải THẮNG rule trần ("breadth thấp VÀ funding cao → chặn"); không thì dùng rule, bỏ ML.

### Funding = selector (CHỜ)
- Đang hiệu quả → chưa đụng. Nhưng backfill đổi data của nó → **re-train trên data mới**; soi lại label/feature trước khi train. Bàn sau khi market xong.

---

## P3 — Tích hợp + tối ưu (sau khi có model mới)
- Model mới → gen prediction → **chụp lại TOÀN BỘ golden baseline** (cũ vô hiệu do data đổi — ADR-0009) → bump CONFIG_VERSION.
- Tối ưu dần: breaker (ADR-0008: MARGIN halt giữ; DCA cap redefine theo vốn/concentration), chiến lược.

---

## Prerequisite trước golive — luồng nến 15m/4h BTC/ETH
- Feature 15m/4h (SMA, momentum, alignment, regime) cần nến 15m/4h mà hệ chỉ có 1m.
- **CHỐT: AGGREGATE từ `kline_1m_opt`** (O=first,H=max,L=min,C=last,V=sum), KHÔNG lấy 15m/4h riêng từ Binance → tránh **train/serve skew** (feature train = feature prod vì cùng một phép aggregate) + đồng bộ mô hình hiện tại. → tách TASK riêng (backfill aggregate historical + rolling-aggregate ingest prod), xong TRƯỚC golive.
- Chỉ BTC/ETH. Lưu set riêng (`kline_15m_btceth`/`kline_4h_btceth`).
- Historical: backfill aggregate 1 lần (cho train). Production: rolling-aggregate khi nến 1m về + ingest. Phải có + warm-up đủ TRƯỚC golive.
- **DIED_SYMBOLS-live (nối DEFERRED split SIM/LIVE):** coin đợt B còn sống (RAY/FTT/SC/DGB/WAVES/GLMR/MDT/IDEX/RAD/STRAX) bị live bỏ qua `DIED_SYMBOLS` → nguồn gốc survivorship (data cố ý không ghi, không phải tự thiếu). Backfill historical đủ cho TRAIN; nhưng data chúng **dừng ở mốc backfill** vì live không cập nhật tiếp. Nếu feature PRODUCTION dùng chúng → phải **gỡ khỏi DIED_SYMBOLS-live + re-ingest TRƯỚC golive** (kẻo lệch train/serve: train có, prod đứng yên).

## Tham khảo (key research — áp vào P2)
Chuẩn: López de Prado *Advances in Financial ML*; open-source mlfinlab, qlib (Microsoft); bổ trợ Aronson (data-snooping).
1. **Triple-barrier labeling** = đúng label 3 lớp (chạm +X%/−X%/hết H) — dùng công thức chuẩn.
2. **Meta-labeling** — gate = ML lọc tín hiệu rule sơ cấp (khớp vai trò gate + cổng "thắng rule").
3. **Sample uniqueness / de-overlap** cho label overlapping H-giờ → sample weights.
4. **Purged K-fold + embargo** — CV time-series chặn leakage (dạng nghiêm của held-out walk-forward).
5. **Feature importance MDA + substitution effect** — gom nhóm tương quan, không tin ranking đơn lẻ.
6. **Deflated Sharpe / data-snooping** — quét nhiều H/X/feature phải phạt số lần thử + đòi OOS nghiêm.

## Pipeline & tính toàn vẹn dữ liệu (P2 — nguyên tắc)

### Features: thêm bằng domain GIỜ, tỉa bằng importance SAU
Importance chỉ **tỉa** feature đã có — KHÔNG đề xuất feature mới. Nên: **thêm** (candidate domain: SMA, alignment, regime, ETH, đồng-pha) làm ngay khi thiết kế; **bớt** (tỉa thừa) chờ có data → importance. Bỏ-được-ngay-không-cần-data: TIME (overfit), momentum khung dư (gom). Còn lại để importance quyết.

### Xuất data train — validate NHIỀU LỚP (sai 1 tí → model vô giá trị)
Một **harness validate export** (kiểu golden), fail-fast + fingerprint, tách khỏi train. **2 tầng:**

**Tầng INPUT (Aerospike) — tái dùng + cải tiến package `aerospike.validate_data`:**
- Giữ: `CheckGapTicker` (quét phút trống có hệ thống); `ValidateMarketObjectConsistency` (**recompute-and-compare** MDO tính-lại-từ-ticker vs DB — viên ngọc, nhân rộng).
- Cải tiến: (1) `ValidateAerospikeVsBinance` so **cả OHLCV** (không chỉ close; volume tolerance riêng); (2) **sampling có hướng** vào 30 coin backfill + biên vòng đời, không random toàn cục; (3) **gap intra-coin** (mỗi coin đủ phút liên tục trong đời nó); (4) **sanity per-record** (giá>0, vol≥0, no NaN/inf, cross-field max≥close/open≥min); (5) bỏ kết luận "100%" từ sample → báo coverage thật.
- **Dùng 2 chỗ:** nghiệm thu backfill NGAY (trước B6) + lại trong H1 mỗi export.

**Tầng OUTPUT (dataset export) — dùng khuôn recompute-compare:**
- **Look-ahead/leakage:** label chỉ dùng `[t, t+H]`, feature chỉ `[.., t]`.
- **Recompute feature:** mẫu feature trong dataset = tính-lại-từ-ticker (khuôn MDO consistency).
- **Alignment** feature↔label đúng timestamp; **sanity** (NaN/range/cột-hằng); **determinism** (re-export 2 lần khớp fingerprint); **survivorship** (có coin die); **golden sample** kiểm tay.
- **Cross-audit ĐỘC LẬP (CCD / đường-code-khác):** recompute KHÔNG dùng cùng hàm export → bắt lỗi *logic* cùng-nguồn (recompute-cùng-code sẽ khớp giả nếu hàm sai). Đây là lớp kiểm mạnh nhất — hai cài độc lập khó cùng sai một kiểu.

### Pipeline tự động + hàm mục tiêu
Đích: tự động export→validate→feature-select→HPO train→eval→(đạt)retrain. Khả thi, nhưng:
- **Objective KHÔNG phải accuracy** — gate phục vụ trading → đo **kinh tế OOS**: gate cải thiện Sharpe/maxDD của hệ so với không-gate VÀ so với rule; tôn trọng imbalance (lớp giảm). Dùng **deflated Sharpe** (phạt số lần thử).
- ⚠️ **Anti-overfit ở MỌI tầng** (automation + HPO trên edge-mỏng + data-ít-sập = cỗ máy overfit nếu lỏng): purged K-fold + embargo; **một OOS "đông lạnh" không cho HPO chạm**, chỉ dùng nghiệm thu cuối; phạt phức tạp.
- **Goodhart:** objective tốt tới đâu, tối ưu mạnh vào nó vẫn lệch mục tiêu thật → OOS đông lạnh là chốt chặn.
- **Model NHỎ** (ít cây/depth/feature, regularization mạnh): rẻ WFO/HPO + chống overfit + dễ giám sát. Ưu tiên model nhỏ thắng rule khiêm tốn hơn model to đẹp-trên-backtest.

### Kiến trúc 2 harness (ranh giới = dataset version-hoá)
**Người chạy = Code headless (`claude -p`) + cron/script, KHÔNG phải Desktop** (Desktop chỉ soạn spec + review report; không có shell, không nhận trigger ngoài).
- **Harness 1 — DATA:** Aerospike + feature spec → export toàn bộ candidate → validate nhiều lớp → sàng lọc THỐNG KÊ (correlation/IC/dedup nhóm tương quan) → **dataset sạch + fingerprint** (artifact bàn giao). KHÔNG train, KHÔNG importance model-based.
- **Harness 2 — TRAIN:** dataset version-hoá → train (Kaggle) → eval OOS (deflated, vs-rule) → **importance model-based (MDA/SHAP)** → report → review/optimize (HPO, tỉa = chọn subset cột). Lặp nội bộ; chỉ gọi H1 lại khi THÊM feature mới. OOS đông lạnh nằm ở đây, tách khỏi HPO.
- **Lưu ý:** Kaggle giới hạn session/quota → HPO từng đợt, không auto-retrain 24/7. Importance cần model nên thuộc H2, không H1.

## Lifecycle metadata (hạ tầng nền — prerequisite trước B6)
Set `symbol_lifecycle` (namespace `ticker`, song song `symbol_mapper`) + class `SymbolLifecycleManager` (load-cache kiểu `SimpleSymbolMapper`).
- **Value:** `{firstSeen, lastSeen, status, delistTs?}`. Tính bằng batch-scan `kline_1m_opt` per-coin; tính lại định kỳ.
- **3 trạng thái (KHÔNG phải 2):** LIVE (niêm yết + data gần) / DEAD (delist thật, lastSeen≈delistTs) / **DATA-INCOMPLETE** (còn niêm yết nhưng data-ta thủng — như 13 coin sống-chưa-track). Phân biệt DEAD vs DATA-INCOMPLETE phải **đối chiếu Binance exchangeInfo**, KHÔNG suy từ mỗi data-ta (kẻo loại nhầm coin sống = tái lập survivorship).
- **Validate:** recompute-compare (lifecycle vs scan thật) + lệch data-ta vs niêm-yết-thật = chỗ thiếu data.
- **Phục vụ:** mốc-live đợt B (P1) · loại zombie khi tính feature/basket (P2 export) · check-delist trong backtest (P3) · thay cột `drawdownToBottom` ad-hoc.
- **Timing:** không chặn đợt B (đang thủ công); làm trong cụm hạ tầng sau đợt B, **trước export feature mới (H1)** (để feature loại zombie đúng).

## Trạng thái 1 dòng
P1 ĐÓNG (TASK-005, commit d387229): 30 core (id 760-789), B6 xác nhận survivorship méo feature THẬT. ĐANG: CỤM HẠ TẦNG — 15m/4h (009 ✅ historical; forward-rolling chờ golive) ‖ died-symbols (008 ✅ applied live, config 129) ‖ lifecycle (010, CCD#3) ‖ validate-input (011, chờ). **H1 đã khởi động:** label gate CHỐT (`docs/H1_GATE_SPEC.md` §1: median-alt return, ngưỡng tuyệt đối scale-√H, export return thô → 3-class ở H2) → export label = TASK-012 (chạy ngay). Tiếp: features gate (§2, mỗi feature validate riêng). P2 funding (0011) sau khi gate xong. P3 (golden+breaker, CONFIG_VERSION) chờ sau train.
