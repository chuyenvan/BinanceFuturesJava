# PREREG_E2E_REPLAY_V12 — phép thử (iii) "REPLAY ĐƯỜNG LỆNH" trước MICRO (CHỐT 2026-11-16, MASTER; TRƯỚC khi dựng fixture 11-05 và chạy)

**Trạng thái:** CHỐT bởi MASTER 2026-11-16 ~16:45 +07. Chưa có lượt replay nào trên jar r4u3fin2. Tiêu chí dưới đây không đổi sau khi thấy số.
Nguồn thiết kế: `~/claude_master/v12/REPLAY_RECON_1116.md` (khảo sát chỉ đọc), audit `AUDIT_GOLIVE_1116_C.md` (C-02, C-03), ADD22 §3.

## 0. Mục đích và SỬA ĐỔI so với ADD22 §3 (iii)
- ADD22 §3 (iii) ghi "so với sim A3 cùng ngày". Khảo sát cho thấy **không có sim A3 cho bất kỳ ngày 2026 nào** (các run `r1-a3-*` kết thúc
  20251230; A3 2026 hoãn vì thiếu feature S1 2026; chưa chứng minh seed sim nào trùng model live cut20251231). Sửa đổi này được chốt TRƯỚC
  khi có bất kỳ số replay nào:
  - **Trước MICRO (prereg này, "phương án B"):** replay qua ĐÚNG byte jar live, so với (a) **REF độc lập** viết bằng numpy từ ĐẶC TẢ (không
    import / không gọi Java) và (b) **log dry thật ngày 2026-11-05**. Chứng minh "jar = đặc tả A3 trên dữ liệu thật", KHÔNG chứng minh
    "jar = sim engine".
  - **Trước PILOT ("phương án A", prereg riêng):** dựng sim A3 trên cửa sổ 2026 và so replay ↔ sim engine. Chưa có A ⇒ không bật pilot.
- Lý do cần phép thử: 5/5 ngày SẠCH của G-MICRO (i) đều có gate đóng; sizing / DCA / exit chưa từng được so; bộ replay cũ (e2e-replay-1105)
  gắn cứng `.dcaGridEnabled(true)` (CrashDayRig:400-402) nên đã che lỗi D-01.

## 1. Đối tượng
- Jar: `~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4u3fin2`, md5 `641803565297d4065d90245e04a00f11`. Classpath = đúng file jar này
  + test-classes của harness; KHÔNG dùng `target/classes`. Harness từ chối chạy nếu md5 khác; ghi vào `result.json` md5 jar và
  `ClassLoader.getResource` của 10 class (C3LiveEntry, C3LiveRuntime, LiveGridSizing, LiveDcaGridC3, DcaUtils, EntryGate, AIRejectFilter,
  GatePreFilter, TrailingStopManager, LiveGateRollingRatio) — cả 10 phải trỏ vào jar đó.
- Runtime dựng qua **đường production đọc Cfg/env** (như `C3LiveRuntime:419,425`), cấm gắn cứng `dcaGridEnabled` / `legBudgetFn`.
- Cấu hình: giá trị của danh sách trắng key chiến lược (bảng AUDIT_GOLIVE_1116_D §1; không key bí mật) đọc từ env.sh 242 bằng
  `grep -E '^(export )?(TEN1|TEN2|…)='` với tên cụ thể. Override khai trước: `LIVE_ADAPTER=dry`, `C3_CAPITAL` theo lượt,
  `LIVE_APPLY_GRID_RATIO=true`, `LIVE_DCA_GRID_ENABLED=true`, `C3_EXCLUDE_LEGACY_HELD=false`, đường dẫn dữ liệu, `LIVE_IS_SHADOW_HOST=true`.
  Ghi vào kết quả: tập TÊN biến chiến lược của 242 không có trong replay (phải rỗng, trừ danh sách khai trước).

## 2. Dữ liệu
- **Fixture chính thức (11-05):** cửa sổ 2026-11-05 07:00 +07 → 2026-11-14 07:00 +07. `sel_dump` live trong `pull242/<ngày>/dumps` cho các
  ngày của cửa sổ; buffer gate `pull242/2026-11-05/run/gate_ratio_live.bin.gz` (chỉ bản ghi < START); Vision 1m 11-05…11-14; exchangeInfo
  gần nhất ≤ 11-05; dòng BIG_DOWN từ `full.log` nếu có.
- **Fixture phát triển (10-30, đã có trong `~/claude_master/e2e1105/fx`):** MỌI việc port / gỡ lỗi / cân chỉnh harness và REF chỉ làm trên
  fixture này. Fixture 11-05 chỉ được chạy sau khi (1) harness + REF đã commit, (2) A1 đã duyệt harness + REF. Lượt đầu trên 11-05 = lượt
  CHÍNH THỨC.
- Nếu lượt chính thức lộ lỗi của HARNESS/REF (không phải của jar): được sửa, nhưng phải ghi errata (lỗi gì, commit sửa), chạy lại và báo cáo
  CẢ HAI lượt; tiêu chí và dung sai không đổi. Lỗi của jar ⇒ FAIL, không sửa harness cho khớp.

## 3. REF độc lập
- Viết bằng numpy/python từ đặc tả, không import Java, không đọc output của replay. Đặc tả = công thức dưới đây + tham số từ profile sim A3
  (`~/kaggle_sim/out/r1-a3-a1/prof_run.properties`) + `docs/c3live/E2E_REPLAY.md`. Dev phải viết mục "Đặc tả REF" (công thức exit đầy đủ:
  arm, trailing, ratchet, time-stop) vào tài liệu kết quả và commit TRƯỚC lượt chính thức; A1 đối chiếu REF ↔ đặc tả.
- Sizing (đã đối chiếu với log dry thật 11-05, cờ tắt: 37,5 × (1 − 0,06734/0,6) = 33,29 ≈ 33,2859 trong log):
  `b(legIdx) = C × SIM_F_BASE / Σw × w_legIdx × DCA_GRID_SCALE × (1 − U_before / 0,6)` = `0,0225 × C × (1 − U_before/0,6)` với tham số 242
  (F_BASE 0,015; weights 1,1,1,1; SCALE 6,0); trần 4,5 % × C; `b < 5` ⇒ BUDGET_SMALL; `U_before = marginUsed(sổ thật) / C`;
  `qty = floor(b / px, stepSize)`.
- Giá trị tính tay ghi trước (C = 10 000, các leg PREDICT liên tiếp cùng phút, bỏ qua làm tròn qty): leg 1 = 225,00; leg 2 = 216,56;
  leg 3 = 208,44 (mỗi giá trị ±0,5 % do notional sau floor). Sau 23 leg: U ≈ 0,35 (< 0,6 ⇒ không skipFull).
- DCA grid: bậc k (k = 1,2,3) đến hạn khi giá ≤ giá vào leg đầu × (1 + level_k), level = −0,50 / −0,75 / −0,90; `legIdx = legCount`;
  tối đa 3 leg DCA; budget theo công thức trên.

## 4. Các lượt
| Lượt | Sàn giả | C3_CAPITAL | Mục đích |
|---|---|---|---|
| R0 | FakeExchange1m | 10 000 | lượt chấm chính |
| R0-DRY | DryGateway production | 10 000 | cùng tiêu chí E1/S1 trên gateway dry thật |
| R-OLD | DryGateway | 10 000, 2 cờ TẮT | độ trung thực của rig so với log dry thật 11-05 |
| S-DCA | FakeExchange1m | 10 000 | đường giá tổng hợp ép ≥ 2 cụm qua đủ 3 bậc |
| FIN-INJ | FakeExchange1m | 10 000 | bỏ 1 symbol PASS khỏi tập fin ở 1 phút có entry |
| R-1000, R-4000 | DryGateway | 1 000 / 4 000 | chỉ báo cáo, phục vụ quyết định vốn micro (§6) |
| R-SIMQ (tuỳ chọn) | FakeExchange1m | 10 000 | q của sim thay buffer live (D-02); chỉ báo cáo |

## 5. Tiêu chí (PASS / FAIL; "KHÔNG XẢY RA" không tính là PASS)
- **C1 cấu hình:** md5 jar đúng; 10/10 class nạp từ jar; log có `[LIVE-SIZING] … =true`, `[LIVE-DCA-GRID] … =true … applyRatio=true`,
  `[MINUTE-FIN] BAT`, `[GATE-RATIO]` live BAT; tập tên biến thiếu = rỗng. Thiếu 1 ⇒ FAIL toàn bộ, không chấm tiếp.
- **E1 chọn coin (R0, R0-DRY):** tập + thứ tự (phút quyết định, symbol) của leg PREDICT ≡ REF 100 %; n ≥ 20 leg.
- **S1 sizing (R0, R0-DRY):** mọi SUBMIT: |b − b_REF| / b ≤ 1e-5 với U của chính lượt đó; qty khớp floor theo stepSize; 3 giá trị tính tay ở §3 đúng.
- **D1 DCA:** (tự nhiên, nếu có) phút đến hạn + legIdx ≡ REF 100 %; (S-DCA, BẮT BUỘC) ≥ 2 cụm × 3 bậc: legIdx 1,2,3 đúng thứ tự, đúng phút
  đến hạn, budget đúng công thức, KHÔNG có leg thứ 5, không leg nào trước khi chạm bậc.
- **X1 thoát (R0):** n ≥ 10 cụm đã thoát, có ≥ 1 time-stop 168 h và ≥ 1 trailing. Lý do thoát của cụm 1 leg ≡ REF 100 %; phút thoát ≥ 98 %
  cùng phút, còn lại lệch ≤ ±1 phút; giá thoát: trung bình Δ(replay − REF)/REF ∈ [−0,8 %; 0], từng cụm ≥ −1,5 % hoặc ≤ 2 tick.
  Không đủ n hoặc thiếu loại thoát ⇒ "KHÔNG ĐỦ MẪU" = không PASS (bổ sung bằng đường giá tổng hợp, khai trong errata TRƯỚC khi chạy bổ sung).
- **F1 fin (FIN-INJ):** đúng leg của symbol bị bỏ ở phút đó KHÔNG được gửi; không thế chỗ bằng hạng 25; có dòng `[MINUTE-FIN-EXCL]`;
  các leg khác của phút đó không đổi so với R0.
- **K1 lành mạnh (R0, R0-DRY):** 0 dòng ERROR, 0 latch, 0 KHAN.
- **E2 trung thực (R-OLD ↔ log dry thật 11-05, 23 SUBMIT 22:52–22:53):** ≥ 20/23 SUBMIT thật khớp (symbol + phút) trong replay và budget
  khớp |Δ|/b ≤ 1e-4; MỌI SUBMIT lệch (thiếu/thừa) phải thuộc đúng một nhãn khai trước: {LEGACY-11-05 (ngày đó coin LEGACY bị loại),
  khác jar r4q↔fin2 ở BIG_DOWN-SEL / universe A1, exchangeInfo}. Lệch không gán được nhãn ⇒ FAIL.
- **Kết luận (iii):** PASS ⇔ C1, E1, S1, D1 (S-DCA), X1, F1, K1, E2 đều PASS. Bất kỳ FAIL nào ⇒ (iii) FAIL ⇒ không tạo gate file.

## 6. Quyết định vốn micro (luật ghi trước, từ R-1000 / R-4000)
- Đếm số leg (entry + DCA) của R0 mà ở vốn 1 000 bị BUDGET_SMALL hoặc dưới min notional. Nếu ≥ 90 % leg của R0 vẫn đặt được ở 1 000 ⇒
  micro = 1 000. Nếu < 90 % ⇒ micro = 4 000 (owner đã chấp nhận tới 4 000 ngày 11-16). Việc "nâng riêng leg dưới mức tối thiểu" là đổi jar,
  thuộc Đợt 3, không ảnh hưởng luật này.

## 7. Giới hạn đã biết (phải ghi vào gate file; KHÔNG được coi là đã kiểm)
- Không so với sim engine (phương án A, trước pilot).
- Vòng main `DetectEntrySignal2TradeNormal` không chạy: các guard của `createOrderBuyRequest0`, sổ giấy twin, `liveBookFull` (skipFull đọc U
  sổ giấy — audit LEGACY-DCA 11-16), sizing theo `price_realtime` (D-03). Feature / p15 / S1 đã có parity G-MICRO (i) phủ.
- X14 (336 h) không đủ dữ liệu trong cửa sổ; BIG_DOWN không có ngày 11-05; tierMul gắn 1.
- Dữ liệu Vision sạch hơn dữ liệu live (không rớt WS, không giá cũ).
- Buffer gate live đang nhiễm (D-02): replay khớp live nhưng cả hai có thể lệch sim; R-SIMQ chỉ báo cáo.

## 8. Quy trình
1. Prereg này commit TRƯỚC khi dựng fixture 11-05.
2. Dev: port rig (worktree riêng, commit WIP thường xuyên), REF, mục "Đặc tả REF"; chỉ chạy trên fixture 10-30.
3. A1 (độc lập): duyệt harness (không gắn cứng cấu hình, classpath jar thật) + REF ↔ đặc tả.
4. Dựng fixture 11-05, chạy lượt chính thức 1 lần, ghi `docs/c3live/E2E_REPLAY_V12_RESULT.md` + `result.json` (md5 đầu vào), commit.
5. MASTER đọc kết quả, tự kiểm lại ≥ 3 con số từ log thô trước khi báo owner.
