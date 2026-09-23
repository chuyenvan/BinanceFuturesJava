# PREREG — GD92 × {HINGE V3, LADDER L1}: gate trượt trên nền T170 + biến thể EXIT

Viết **TRƯỚC** khi build/chạy. Chốt tham số + tiêu chí. Ngày 2026-09-23. DEV only (không 2026).
**Không sửa thiết kế sau khi thấy kết quả.**

Câu hỏi của owner (nguyên văn):

> *"thử chạy gd92 với `HINGE V3 weak 0.17` và `LADDER L1` xem thế nào rồi in chi tiết bảng pnl ra."*

---

## 0. Vì sao đây là phép thử MỚI (và là phép thử khó)

Hai tổ hợp này **chưa từng chạy**:

| yếu tố | trạng thái đã biết |
|---|---|
| **GD92** (`SIM_GATE_ROLLING_PCT=0.92` + `SIM_GATE_ROLLING_DAYS=90`) | đã **THUA T170** khi chạy một mình (`docs/RESULT_GD92_RECHECK.md`): **0 TỐT / 3 XẤU** (win% −4.58 · TSloss% +6.41 · meanP −1.93, cả ba ngoài CI) và **FAIL rào cứng toàn kỳ** (maxDD **−16.55%**, UW **278**) |
| **HINGE V3** (`SIM_TS_PNOPUMP_WEAK_THR` 0.29→0.17) trên nền T170 | **NULL** (0/5 rate ngoài CI) — `docs/RESULT_TRAIL_HINGE.md` |
| **LADDER L1** (`TS_LADDER` bậc thang) trên nền T170 | **NULL** (0/5 rate ngoài CI) — `docs/RESULT_TRAIL_LADDER.md` |
| **GD92 trên nền T170** (thay vì nền `x1_c3_full` gate scale 1.00 như lần gốc) | **CHƯA TỪNG CHẠY** — đây là biến cần đo |
| **GD92 + exit variant** | **CHƯA TỪNG CHẠY** — đây là câu hỏi của owner |

Điểm cần nhớ: GD92 gốc chạy trên nền `x1_c3_full` (**gate scale 1.00**, họ T100). Nay ghép
với nền **T170 (gate scale 1.70, `SIM_GATE_DYN_SCALE=1.70`)**. Kết quả GD92 cũ **không** suy ra
được kết quả trên nền mới — phải đo.

---

## 1. Sự thật đã xác minh (dùng lại, không suy diễn lại)

1. **GD92 = đúng 2 key**: `SIM_GATE_ROLLING_PCT=0.92` + `SIM_GATE_ROLLING_DAYS=90`
   (profile gốc `profiles/archive/x1_gd92.properties`, `PROFILE_HASH=52ee74bb5477b363 keys=21`).
2. **⚠️ Code rolling gate KHÔNG có trên `module`** — `GateRollingThreshold.java` bị xoá ở
   `f1c43a3`. Code nằm ở branch `gd92-recheck`, commit **`1db0613`** (phục hồi nguyên văn từ
   `f1c43a3^` + 3 điểm nối dây, md5 file `e1e99295c76bfd066493ca25ebeb1243`, 149 dòng).
   ⇒ Cách làm: **`git cherry-pick -n 1db0613`** (không commit) trên `module` → build jar → chạy
   sim → **`git checkout -- src/`** trả `module` về nguyên trạng; chỉ commit docs + script.
   **KHÔNG merge `gd92-recheck`.**
3. **Exit flags đã có sẵn trên `module`** (kiểm bằng file, không bằng trí nhớ):
   - HINGE: `SIM_TS_PNOPUMP_WEAK_THR` (`Configs.java:798`)
   - CAP phẳng: `SIM_TS_MAX_GAP` / `SIM_TS_MAX_GAP_WEAK` (`Configs.java:801-802`)
   - LADDER: `TS_LADDER` / `TS_LADDER_LO` / `TS_LADDER_GAPS` (`Configs.java:476-479`), default **OFF**
     ⇒ byte-identical.
4. **Override tham chiếu lấy NGUYÊN VĂN từ `prof_run.properties` của chính 2 run tham chiếu**
   (không tự diễn giải lại):
   - HINGE V3 = `profiles/x1_th_weak17.properties` = `x1_gs_t170` + **đúng 1 dòng**:
     `SIM_TS_PNOPUMP_WEAK_THR=0.17` (kiểm bằng `diff`, xem §5).
   - LADDER L1 = `prof_run.properties` của run `tl-l1` = `x1_gs_t170` + **3 dòng**:
     `TS_LADDER=1`, `TS_LADDER_LO=0.00,0.10,0.25,0.50,1.00`, `TS_LADDER_GAPS=0.04,0.08,0.15,0.25,0.35`
     (+ `SIM_TRAIL_TRACE=1` đo-lường-only; `WFO_FUNDING_PRED_DIR` là hạ tầng, do tool tự trỏ mount).

---

## 2. Nền + hạ tầng (khoá)

| | |
|---|---|
| Branch | `module` HEAD `fc7065d` + **cherry-pick `1db0613` (không commit)** |
| Dataset | `chuyendinh/sim-x1-2021-bundle` (= `wfo_ds_x1_2021`, `TIME_RUN=20210701`) |
| Cửa sổ | `TIME_RUN=20210701` .. `SIM_END_DATE=20251231` (DEV, ~1,645 ngày) |
| Ticker | `TICKER_SOURCE=file`, 1,826 ngày, mapper ≥ 800 (guard có sẵn) |
| Sim chạy | **KAGGLE CPU kernel** (`docs/KAGGLE_SIM.md`). **KHÔNG chạy Java/sim trên Oracle** (shadow active) — Oracle chỉ `mvn -o package`. |
| Jar | build `mvn -o package` (tests BẬT) trên cây đã cherry-pick; đóng gói dataset **`sim-jar-gd92xexit`** (chỉ `sim.jar` + `prof_x1_c3_full.properties`), truyền qua `jar_ds=` |
| Chi phí | 0 (CPU kernel không tính quota) |

---

## 3. Các chân (khoá TRƯỚC)

Mọi chân: profile `x1_gs_t170` + override ghi dưới đây + `SIM_TRAIL_TRACE=1` (đo-lường-only;
tiền lệ `tl-par` == `tl-part` byte-identical ⇒ không đổi `printDone`).

| tag | nội dung | override |
|---|---|---|
| `gx-par1` | **parity 1 (BẮT BUỘC)** — T170 nguyên bản, KHÔNG key rolling, jar mới | `{}` (không override giao dịch) |
| `gx-par2` | **parity 2 (khuyến khích)** — `x1_c3_full`, KHÔNG key rolling | profile `x1_c3_full` |
| `gx-a` | **(A) GD92-ONLY** (đối chứng: tách đóng góp GD92 khỏi exit) | `SIM_GATE_ROLLING_PCT=0.92`, `SIM_GATE_ROLLING_DAYS=90` |
| `gx-b` | **(B) GD92 + HINGE V3** | (A) + `SIM_TS_PNOPUMP_WEAK_THR=0.17` |
| `gx-c` | **(C) GD92 + LADDER L1** | (A) + `TS_LADDER=1`, `TS_LADDER_LO=0.00,0.10,0.25,0.50,1.00`, `TS_LADDER_GAPS=0.04,0.08,0.15,0.25,0.35` |
| `gx-d` | (D) **tuỳ chọn** GD92 + cap 10/30 (ưu tiên thấp) | (A) + `SIM_TS_MAX_GAP=0.30`, `SIM_TS_MAX_GAP_WEAK=0.10` |

Chạy 5 slot song song: `gx-par1`, `gx-par2`, `gx-a`, `gx-b`, `gx-c`. `gx-d` chạy sau nếu còn slot.

---

## 4. Cổng parity (BẮT BUỘC, chạy TRƯỚC khi đọc kết quả)

- **Parity 1 (chính)**: profile `x1_gs_t170` **không có key rolling** ⇒ `printDone.csv` phải
  **byte-identical** md5 **`efb793e2468ca3a7318da0f0ad23d4fc`** (n=1089, equity 111070).
  ⇒ chứng minh code rolling **trơ khi không khai báo key**.
- **Parity 2 (khuyến khích)**: `x1_c3_full.properties` ⇒ md5 **`dc16e4da6ff6cb7b8d41c592bc3d9c45`**
  (đúng như `RESULT_GD92_RECHECK` §0b).
- **Khác ⇒ DỪNG, báo RO**, không đọc kết quả A/B/C.
- Xác nhận log **`[GATE-ROLL]` BẬT thật** trong A/B/C (pct/window, mốc đầu, ngưỡng min/max,
  `nBeforeFirst=0`).

---

## 5. Chấm điểm (khoá TRƯỚC)

1. **5 rate chất lượng** (theo leg, toàn cửa sổ), so với **`gx-par1`** (= T170):
   `win%` (+), `TSloss%` (−), `mP|SM` (+), `mP|SL` (+), `meanP` (+).
   (dấu = hướng "tốt hơn")
2. **CI**: paired bootstrap **block-72h**, `NREP=2000`, `SEED=20260905`, anchor 2021-07-01.
   Báo **CẢ HAI độ rộng**:
   - legacy **`×1.21`** (như brief owner yêu cầu),
   - chuẩn hoá **`inflate(k)=sqrt(2 ln k)`** với **`k=3`** (ba chân A/B/C so T170) = `1.482304`
     — theo `docs/RISK_APPETITE.md` §1 / `AUDIT_CI_INFLATE_STANDARDIZATION.md`.
   Một rate chỉ tính là **"ngoài CI"** khi ngoài **CẢ HAI** độ rộng (tiền lệ `traillad_score.py`).
3. **Rào cứng** `docs/RISK_APPETITE.md` (ngưỡng MỚI: maxDD ≤ 30%/năm, UW ≤ 200 ngày,
   quý xấu nhất ≥ −15%, không năm âm, tập trung 1 coin ≤ 15% equity)
   — **kiểm CẢ theo năm LẪN toàn kỳ** (bài học GD92: PASS theo năm nhưng FAIL toàn kỳ).
4. **BẮT BUỘC: bảng PnL CHI TIẾT THEO NĂM** cho từng chân: năm · n · win% · TSloss% · meanP ·
   **PnL (USDT)** · **ret%** · maxDD% · UW (ngày) · qmin% · equity cuối năm. Kèm hàng tham chiếu
   T170 / HINGE V3 / LADDER L1 (đã có sẵn, đọc lại — không chạy lại).
5. Báo **n · hold · turnover · capture ratio** nhóm đỉnh ≥20/50/100% nếu tính được (từ
   `trailTrace.csv`).
6. **PnL/equity báo riêng, KHÔNG dùng để chọn.**

### Luật kết luận (đã khoá)
- **GO** chỉ khi: **≥2 rate ngoài CI cùng hướng TỐT** + **hết rào cứng (cả năm LẪN toàn kỳ)** +
  **0 rate XẤU ngoài CI**.
- Không hơn ⇒ **NULL**, ghi rõ; và trả lời **GD92 có làm exit variant "sáng" hơn không** (so
  (B),(C) với HINGE V3 / LADDER L1 trần).
- Kết quả dương vẫn chỉ là **ứng viên**, cần forward. Không tự tích hợp sản xuất.

---

## 6. Dự đoán ghi trước (chấp nhận SAI)

1. **Cả 3 chân A/B/C: NULL** (0–1 rate ngoài CI). GD92 một mình đã 3 XẤU/3; exit variant một mình
   đã NULL — ghép hai cái NULL không sinh ra hiệu ứng mới là kỳ vọng mặc định.
2. **Rào cứng: PASS theo năm nhưng FAIL toàn kỳ** ở cả A/B/C — đoạn dưới nước dài
   2021-11-16 → 2022-08-20 (UW ~278 ngày) do GD92 tạo ra; HINGE/LADDER chỉ chạm các leg đạt
   +7%/+10% nên **không** rút ngắn được đoạn đó.
3. **A/B/C mang theo "vết" xấu của GD92** so với T170: `win%` thấp hơn, `TSloss%` cao hơn.
4. **GD92 làm exit variant sáng hơn? KHÔNG kỳ vọng** — (B) sẽ gần giống A hơn là giống HINGE V3
   trần; (C) sẽ gần giống A hơn là giống LADDER L1 trần.

Nếu dự đoán sai theo hướng TỐT hơn ⇒ ghi rõ + nêu giả thuyết nhân quả, KHÔNG tự nâng thành GO.

---

## 7. Multiplicity (ghi trước, không viện sau)

Đây là vòng **exit/gate thứ ~6** chạy chống T170 trong chương trình này (TRAIL-HINGE 3 biến thể,
TRAIL-LADDER 3, TRAIL-CAP-1030 2, CLOSE-BIGGAP 18, PEAK-CLOSE 1, + vòng này 3 chân).
`k=3` chỉ phủ **vòng này**. Một thắng lợi đơn lẻ **không đủ** để đổi incumbent — phải qua holdout
2026 trước. Vì kỳ vọng là NULL, vấn đề multiplicity **không cần viện đến** để bảo vệ kết luận.

---

## 8. Điều KHÔNG làm
Không push. Không merge `gd92-recheck` vào `module`. Không commit code rolling (chỉ docs + script).
Không chạm 242. Không đóng holdout 2026. **Không** quét biến thể GD92 (0.88/0.90/0.94/0.96,
W=60/120/180). **Không** quét thêm biến thể exit. Không đổi incumbent. Dọn temp.
