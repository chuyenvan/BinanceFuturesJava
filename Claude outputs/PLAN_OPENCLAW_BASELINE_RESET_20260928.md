# PLAN cho OpenClaw (Oracle) — RESET BASELINE + LUẬT: "nhiều cược nhỏ cùng chất lượng" thay vì "nới gate"

Soạn: MASTER (Claude), 2026-09-28 tối, theo yêu cầu owner. Chỉ phân tích/thiết kế — OpenClaw thực thi.
Nguồn số: docs/result/* trên branch `module` @ `8f3d847`. Mọi con số dưới đây trích từ doc (ghi tên file).

## 0. TL;DR
- Giả thuyết owner: "T170 quá chặt + lưới 15' ⇒ ít lệnh, nhồi margin; giảm margin 3–4×, tăng số cược, chấp nhận winrate giảm".
- Số đã đo nói: **2/3 đúng, 1/3 sai**.
  1. ✅ **Lưới 15' là nút chặn lớn nhất** — nhịp 1' cho +46% lệnh, **cùng chất lượng**, +9.84pp CAGR, NGOÀI CI (RESULT_SIM_CADENCE_MATCH).
  2. ✅ **Giảm size + tăng K** giữ nguyên win% (không đổi chất lượng), rủi ro tốt hơn mọi mặt (RESULT_SIZE_COUNT, B2).
  3. ❌ **Nới GATE để tăng lệnh = thêm lệnh RÁC**: đường cong đơn điệu, lệnh biên có EV ≤ 0 (RESULT_GATESCALE_KEEPLEG0, _SWEEP, _GATE_ROOTCAUSE).
     Gate 1.70 KHÔNG phải "ăn khớp với 15'" — T170 được chọn ở sim nhịp 1'; ở 15' nó chỉ bị bóp thêm cơ hội.
- **Bức tường tự tạo thật sự** không phải gate, mà là (i) rào (a)/(b′) định nghĩa trái bản chất chiến lược skew dương, (ii) luật
  "≥2 rate ngoài CI hướng TỐT" (superiority) trong khi MDE 3.6–19pp ≫ cải tiến thật 1.7–5.4pp ⇒ không gì qua được ⇒ luôn giữ
  incumbent. Thay bằng **luật non-inferiority + robustness** (mục 3).
- Tăng số cược bằng **nhịp 1' + K rộng + size nhỏ** (cùng thời điểm gate mở, nhiều coin hơn, mỗi coin ít margin hơn) — KHÔNG bằng
  hạ ngưỡng gate.

## 1. Bằng chứng (đã đo, không chạy lại)
### 1.1 Nhịp (RESULT_SIM_CADENCE_MATCH)
| cấu hình | n | entry/ngày | CAGR | maxDD(ngày) | UW |
|---|---|---|---|---|---|
| all-1' (KEEPLEG0) | 1085 | 0.660 | +27.14% | −11.21 | 147 |
| sel15 (live hiện tại) | 744 | 0.453 | +17.29% | −6.27 | 166 |
| all-15' | 420 | 0.256 | +11.08% | −5.93 | 278 |
sel15 vs all-1': ΔCAGR −9.84pp, CI trên −0.49 (ngoài CI); 0/5 rate ngoài CI ⇒ khác biệt là SỐ LỆNH, không phải chất lượng.
Live muốn nhịp 1' cần CASCADE (PLAN_CASCADE_ENTRY: 1 lượt ~228s, 94% ở FUNDING predict toàn universe; key `ENTRY_CASCADE`, OFF mặc định).

### 1.2 Size × K (RESULT_SIZE_COUNT, nền sel15)
| arm | size | K | n | CAGR | maxDD | UW | qmin | conc/coin | %top-1 | q* | win% |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B0 | ×1 | 8 | 744 | 17.29 | −6.27 | 166 | −3.36 | 6.77 | 19.13 | 21.2 | 88.44 |
| B2 | ×0.5 | 16 | 1152 | 15.06 | −5.48 | 164 | −1.36 | 3.74 | 15.83 | 25.5 | 88.80 |
| B4 | ×0.5 | 32 | 1878 | 18.43 | −7.04 | 277 | −2.27 | 3.49 | 16.80 | 22.2 | 87.86 |
| B3 | ×0.25 | 32 | 1885 | 12.65 | −5.00 | 278 | −0.78 | 2.12 | 15.23 | 26.0 | 87.85 |
win%/TSloss% (không phụ thuộc size) TRONG CI 5/5 ⇒ coin hạng 9–32 cùng chất lượng hạng 1–8. B2 bị loại CHỈ vì (a)/(b′) + luật superiority.
Lưu ý: giảm size 3–4× (B3) làm CAGR tụt mạnh và UW kéo dài — ×0.5 là vùng hợp lý; "3–4×" chỉ nên đi kèm K ≥ 24–32 và nhịp 1'.

### 1.3 Nới gate (RESULT_GATESCALE_KEEPLEG0, nhịp 1')
| scale | n | CAGR | maxDD | UW | meanP/leg |
|---|---|---|---|---|---|
| 1.70 | 1085 | 27.14 | −11.21 | 147 | 5.147 |
| 1.55 | 1245 | 25.73 | −12.37 | 204 | 4.536 |
| 1.40 | 1411 | 26.58 | −12.62 | 221 | 4.227 |
| 1.25 | 1701 | 24.46 | −13.71 | 221 | 3.567 |
Thêm 616 lệnh (1.70→1.25) mà SumPnL giảm 9.4k ⇒ lệnh biên EV âm. Trên nền T170: win% −1.8…−3.9pp, TSloss +2.5…+5.6pp ngoài CI (RESULT_GATESCALE_SWEEP).
GATE_RECAL (phân vị cuộn, nhịp 15'): n ×2.5–4.4 nhưng meanP/leg 49→10–16, UW 568–773 ⇒ "nhiều lệnh rác".

## 2. BASELINE đề xuất
**B* = KEEPLEG0 + nhịp 1' (all-1', không SIM_ENTRY_SAMPLE_MIN) + CONC_CAP 15%** (md5 kỳ vọng = 99e42b75 vì cap no-op ở KEEPLEG0).
Lý do: là cấu hình DEV tốt nhất có chất lượng đã kiểm, live tái lập được sau khi bật cascade. sel15 giữ làm "nền live hiện hành" để đối chiếu.

## 3. LUẬT MỚI (thay superiority + (a)/(b′)) — cần owner duyệt trước khi OpenClaw chạy Phase 2
Tầng 1 — RÀO RỦI RO (giữ, là thật): maxDD **MTM phút** ≤ 40%/năm · UW ≤ 250 · quý xấu nhất ≥ −20% · 0 năm âm · conc 1 coin ≤ 15% · gross ≤ 70%.
Tầng 2 — RÀO ĐỘ BỀN (thay (a)/(b′)): q* ≥ 15% · %PnL top-1% lệnh ≤ 25% · bỏ top-3 EPISODE (ngày có lệnh, nối khoảng trống ≤2 ngày) ⇒ ΣPnL > 0.
Tầng 3 — NON-INFERIORITY chất lượng vs B* (CI block-72h, 2000 rep, seed 20260905, inflate(k)): win% không kém quá −2.0pp; TSloss% không
  tệ quá +2.5pp; mP|SM% và mP|SL% (trên `profit` %, KHÔNG USDT) không tệ hơn ngoài CI. (Không tính meanP — trùng đại số.)
Tầng 4 — MỤC TIÊU (điểm, không đòi significance): Calmar_MTM = CAGR/|maxDD MTM phút| ≥ B*, VÀ n ≥ 1.3× B*, VÀ conc/coin ≤ B*.
Chọn: ứng viên qua cả 4 tầng, Calmar_MTM cao nhất; hoà ⇒ chọn n lớn hơn (ưu tiên owner "nhiều lệnh để ổn định").
Chống dredging: k ứng viên khoá trước (≤6), không mở biến thể quanh winner; chạm HOLDOUT 2026 1 lần là cổng cuối (Phase 4).

## 4. PHASES cho OpenClaw
Luật chung: KHÔNG chạy Java/sim trên Oracle (shadow đang chạy) ⇒ sim trên Kaggle (bundle `sim-x1-2021-bundle` + overlay); DEV ≤ 2025-12-31;
pre-reg commit TRƯỚC khi tính số; mỗi run parity trước; không deploy; không push dữ liệu. Đọc `docs/runbooks/AGENT_RUNBOOK.md`,
`docs/runbooks/KAGGLE_SIM_48M.md`, `docs/runbooks/RISK_APPETITE.md` trước.

### Phase 0 — vệ sinh (0 compute)
- Gỡ `_claude_tmp/` khỏi git (`git rm -r --cached _claude_tmp`, thêm `.gitignore`); xoá `_claude_audit_bundle_20260928.tar.gz` nếu có.
- Công cụ chấm dùng CHUNG cho mọi phase: 1 script `research/analysis/reset_rule_score.py` tính đủ tầng 1–4 (rate trên `profit` % theo
  `c3_rates.py:94-109`; maxDD/UW MTM phút theo tooling RESULT_INTRADAY_DD; q*, top-1%, episode jackknife). Tự kiểm: chấm lại KEEPLEG0 và
  cd-sel15 phải khớp số đã công bố (n/equity/CAGR/maxDD daily/q*/top-1%).

### Phase 1 — chấm lại artifact CÓ SẴN theo luật mới (0 sim) — pre-reg `PREREG_RESET_RULE_P1.md`
Đối tượng (đã có printDone/sim.out trên Oracle `kaggle_sim/out` / `java/devrun`): FG_KEEPLEG0 (1'), cd-sel15, sc-b1..b4, gatescale KEEPLEG0
1.55/1.40/1.25, gs2-t1xx (nền T170), cc-t100, kg0-q995/q998/q999(-15m).
Đầu ra: bảng 4 tầng; mục đích = xác nhận luật hoạt động hợp lý (dự báo MASTER ghi trước: B* qua tầng 1–2; gate-loosened FAIL tầng 3;
sc-b2 qua tầng 1–3 nhưng tầng 4 kém B* vì nhịp 15'). MTM phút thiếu ticker 1m cho tag nào ⇒ ghi KHÔNG CHẤM ĐƯỢC, không thay bằng daily.

### Phase 2 — sim mới trên Kaggle, k=5 KHOÁ TRƯỚC (pre-reg `PREREG_RESET_RULE_P2.md`) — sau khi owner duyệt luật mục 3
Tất cả nhịp 1', KEEPLEG0 + CONC_CAP 15%, chỉ đổi knob có sẵn (SIM_F_BASE, SELECTOR_RANK_TOPK, SIM_GATE_DYN_SCALE):
| arm | size (SIM_F_BASE) | K | gate | ý nghĩa |
|---|---|---|---|---|
| R0 | ×1 (0.03) | 8 | 1.70 | = B* (parity 99e42b75) |
| R1 | ×0.5 | 16 | 1.70 | B2 ở nhịp 1' |
| R2 | ×0.5 | 32 | 1.70 | B4 ở nhịp 1' |
| R3 | ×0.33 | 24 | 1.70 | "giảm margin ~3×" của owner, gross ≈ giữ |
| R4 | ×0.5 | 16 | 1.55 | kiểm 1 bước nới gate nhẹ khi đã phân tán |
inflate(k=5)=1.7941. Dự báo MASTER ghi trước: R1/R3 qua tầng 1–3, n ×1.4–2.2, Calmar_MTM ≈ B* (±15%); R2 rủi ro UW > 250; R4 FAIL tầng 3.
Kiểm hợp lệ: R0 md5 = 99e42b75; gross MAX < U_MAX 0.60 mọi arm; U_MAX/throttle không bind ngầm (báo số lệnh bị chặn).

### Phase 3 — độ bền ứng viên thắng (0 sim)
Episode jackknife (bỏ top-1/3/5), bootstrap cụm episode (5000 rep, seed 20260928), DSR với độ phân tán SR từ các run DEV cùng cửa sổ,
placebo "cùng phút vào, coin ngẫu nhiên" (harness replay thoát của RESULT_EXIT_FIT) — dùng lại pre-reg nháp PREREG_INCUMBENT_ROBUST
(MASTER đã soạn, trong `_claude_tmp/robust/` bản Windows) nếu còn.

### Phase 4 — HOLDOUT 2026 một lần (pre-reg riêng, owner duyệt) rồi mới tính chuyện live
- Cần pred/gate 2026 dựng lại bằng đúng pipeline WFO (RESULT_PREDBIN_REPRO: tái lập được bằng retrain) + S1 bins 2026; khai rõ phần
  2026 đã bị nhìn (p15/feature 08–09/2026, audit-only).
- Tiêu chí holdout: không vi phạm rào tầng 1; Calmar_MTM > 0; chênh với B* không tệ ngoài CI (7–9 tháng chỉ bắt được thất bại lớn).
- Chỉ sau đó: bật `ENTRY_CASCADE` + nhịp 1' + profile thắng trên shadow (owner duyệt, parity 2 md5, EntryCascadeTest), theo dõi ≥ 4 tuần.

## 5. Rủi ro phải nhớ
- K rộng cùng thời điểm gate mở = đa dạng hoá TRONG sự kiện, KHÔNG tạo sự kiện độc lập mới ⇒ n_eff tăng ít; tường power (~9 episode)
  vẫn còn; phải nhìn tầng 2 (episode) chứ không chỉ n.
- Non-inferiority cho phép nhiễu lọt vào ⇒ giới hạn k, khoá trước, holdout là cổng cuối — không bỏ qua Phase 4.
- Nhịp 1' ở live phụ thuộc cascade + tải Oracle (4 core); đo lại chi phí/tick sau cascade trước khi hứa 1'.
- Gate live đang đóng vì REGIME yên (RESULT_FEATDIFF_PASS2) ⇒ forward sẽ ít lệnh bất kể cấu hình; không kết luận từ vài tuần live.
