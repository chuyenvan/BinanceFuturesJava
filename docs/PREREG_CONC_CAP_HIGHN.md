# PREREG — TRẦN TẬP TRUNG 1 COIN 15% (`CONC_CAP_PERCOIN`) TRÊN NỀN NHIỀU LỆNH

Chốt **TRƯỚC** khi chạy bất kỳ sim nào. Ngày 2026-09-24. Branch `module` (HEAD `4850b03`).
Sim chạy **TRÊN KAGGLE CPU KERNEL** (`docs/KAGGLE_SIM.md`) — **KHÔNG** chạy Java/sim trên Oracle
(Oracle chỉ `mvn -o package`). **KHÔNG** `claude-run`/Claude Code. **KHÔNG** push. **KHÔNG** merge
`gd92-recheck`. DEV only (cửa sổ `2021-07-01 .. 2025-12-31`, **không** chạm 2026).

---

## 0. VÌ SAO CÓ VÒNG NÀY

`docs/RESULT_FRAGILITY_N.md` (commit `4850b03`) kết luận: khi đánh **1x** (đã xác nhận `lv=1.0000`
trên 100% leg cả 3 nền), **kênh MẤT THẬT duy nhất có thể loại bằng cơ chế** là **tập trung 1 coin**
(coin delist/về 0 trong khi đang giữ thì không hồi phục; còn maxDD/UW chỉ là **tạm thời** vì
exposure ≤ 57.5% equity ⇒ không thể cháy tk). Số đo được:

| nền | tap trung 1 coin max | coin | thời điểm | vs trần 15% |
|---|---|---|---|---|
| T170 (`x1_gs_t170`) | 9.77% | FTT | 2022-11-10 | dưới |
| **T100** (`x1_c3_full`) | **28.51%** | CUDIS | 2025-11-12 | **VƯỢT 13.5 điểm** |
| **GD92** | 14.38% | JELLYJELLY | 2025-11-07 | sát trần |
| **`hn-g-cp` (GD92+CAP)** | **15.29%** | — | — | **vượt 0.29 điểm** |

Cơ chế đã có sẵn trong code: `CONC_CAP_PERCOIN_ENABLED=1` + `CONC_CAP_PERCOIN_PCT=0.15`, guard
tại `SimulatorMarketLevelTicker1MStopLoss.createOrder` — chặn HẲN leg mới khi
`(margin coin đang mở + margin leg mới)/equity > pct`. Đã prove **1 lần duy nhất** ở
`docs/RESULT_DCA_AGG_PERCOIN.md` (nền LOOSE, conc 17.15% → 12.51%, binding 45, **0 rate XAU**).
**Vòng này** đo lại đúng cơ chế đó trên **2 nền nhiều lệnh đang là ứng viên** (T100, GD92) và
trên chân **GD92+CAP** — nơi `RESULT_FRAGILITY_N` để lại conc **vượt trần**.

⚠️ **Biết trước (không được "quên" khi báo cáo):** T100 và GD92 base **đã FAIL rào cứng toàn kỳ
từ trước** (T100 UW 248 + conc 27.23%; GD92 UW 278 — `RESULT_GD92_RECHECK.md` §4,
`RESULT_EXIT_HIGH_N.md` §0). ⇒ Vòng này **KHÔNG** phải vòng tìm incumbent; nó là **phép đo cơ chế**
("trần per-coin làm được gì, mất gì") **cộng** phép đo tác dụng phụ lên 5 rate.

---

## 1. SỰ THẬT ĐÃ XÁC MINH (dùng lại, không suy diễn lại)

| mốc | cấu hình | n (leg) | equity | md5 `printDone.csv` |
|---|---|---|---|---|
| **T170** (`x1_gs_t170`) | gate scale 1.70, không rolling | **1,089** | **111,070** | `efb793e2468ca3a7318da0f0ad23d4fc` |
| **T100** (`x1_c3_full`) | gate scale 1.00, không rolling | **2,559** | **121,770** | `dc16e4da6ff6cb7b8d41c592bc3d9c45` |
| **GD92** (`hn-g92`) | `x1_c3_full` + `SIM_GATE_ROLLING_PCT=0.92` + `SIM_GATE_ROLLING_DAYS=90` | **2,632** | **133,944** | `cd913759ecd4bf50adab2b818eaf9525` |
| **GD92+CAP** (`hn-g-cp`) | GD92 + `SIM_TS_MAX_GAP=0.30` + `SIM_TS_MAX_GAP_WEAK=0.10` | **2,608** | — | `43fb90ee41c29b39ebd2ffc64b19996b` |

Ba mốc OFF ở trên **đã có sẵn trên đĩa** (`/home/ubuntu/kaggle_sim/out/<tag>`) từ vòng
`RESULT_EXIT_HIGH_N` — **KHÔNG chạy lại**, dùng làm đối chứng OFF (cùng jar
`sha256 bb282f40d66b97ec435d4f5bd2678dbbd29dc11965bda700f43e14c2f28654bb`, cùng bundle
`sim-x1-2021-bundle`, cùng cửa sổ). Vòng này chỉ đổi **1 trục duy nhất**: bật `CONC_CAP_PERCOIN`.

⚠️ Code rolling gate **KHÔNG có trên `module`** (`GateRollingThreshold.java` bị xoá ở `f1c43a3`).
Dùng `git cherry-pick -n 1db0613` (branch `gd92-recheck`), build jar, chạy, **sau đó
`git checkout -- src/`** trả `module` nguyên trạng. **KHÔNG commit, KHÔNG merge.** Ghi rõ
sha256 jar + md5 file `GateRollingThreshold.java` đã dùng.

**Chứng minh "cùng 1 trục" cục bộ (làm TRƯỚC khi push):** diff tập key/giá trị giữa profile chạy
OFF (`kaggle_sim/out/<tag>/prof_run.properties`) và profile chạy ON **chỉ khác 2 dòng**
`CONC_CAP_PERCOIN_ENABLED` / `CONC_CAP_PERCOIN_PCT` (không có `SIM_TRAIL_TRACE`, xem §6).

---

## 2. THIẾT KẾ — 3 chân ON + 3 đối chứng OFF + 1 chân parity (4 kernel mới)

| # | tag | nền | override THÊM so với OFF | đối chứng OFF |
|---|---|---|---|---|
| 0 | `cc-par1` | `x1_gs_t170` | — (cổng parity, **KHÔNG** bật cap) | `t170-x1-2021` |
| 1 | `cc-t100` | `x1_c3_full` | `CONC_CAP_PERCOIN_ENABLED=1`, `CONC_CAP_PERCOIN_PCT=0.15` | `hn-t100` |
| 2 | `cc-g92` | `x1_c3_full` + rolling GD92 | cap | `hn-g92` |
| 3 | `cc-g-cp` | `x1_c3_full` + rolling GD92 + CAP 10/30 | cap | `hn-g-cp` |

Với `GD92 = {SIM_GATE_ROLLING_PCT: 0.92, SIM_GATE_ROLLING_DAYS: 90}` và
`CAP1030 = {SIM_TS_MAX_GAP: 0.30, SIM_TS_MAX_GAP_WEAK: 0.10}` (lấy **đúng** giá trị từ
`prof_run.properties` của các chân OFF, không tự diễn giải).
Tất cả: `TICKER_SOURCE=file`, `SIM_END_DATE=20251231`, `TIME_RUN=20210701` (qua cửa sổ bundle
`sim-x1-2021-bundle`), guard mapper ≥ 800, ticker ≥ 1,826 ngày.
**KHÔNG** đặt `SIM_TRAIL_TRACE` (vòng này không đo capture; thêm trace là vô ích và làm chậm).

---

## 3. CỔNG CHẶN — chạy TRƯỚC, chưa qua thì DỪNG, báo RO

| cổng | điều kiện PASS | nếu FAIL |
|---|---|---|
| **P1 parity** | `cc-par1` (x1_gs_t170, cap **OFF**) md5 **`efb793e2468ca3a7318da0f0ad23d4fc`**, n=1089, eq 111,070 | DỪNG, báo RO (`docs/KAGGLE_SIM.md` §0) |
| **P2 rolling thật** | log `cc-g92`/`cc-g-cp` có `[GATE-ROLL] BAT: pct=0.92 window=90d` + `nBeforeFirst=0` | DỪNG, báo RO |
| **P3 cap bind THẬT** | log `cc-t100` có `[CONC-PC] MODE pct=0.15` **VÀ** `[CONC-PC] SUMMARY blocked=N` với **N ≥ 1**, **VÀ** md5 khác `dc16e4da…` | **KHÔNG dừng**, nhưng **BẮT BUỘC ghi rõ**: chân có `blocked=0` ⇒ kết quả của chân đó **TẦM THƯỜNG** (cap là no-op ⇒ OFF ≡ ON byte-identical) |
| **P4 key bind** | md5 `cc-*` **KHÁC** md5 OFF tương ứng ở **ít nhất 1 chân** | tất cả trùng ⇒ cap là no-op trên mọi chân, báo rõ là kết quả vô hiệu |

`PROFILE_HASH` trên Kaggle **không** so được với Oracle (bị ghi đè `WFO_FUNDING_PRED_DIR` sang
mount Kaggle) — so bằng md5 `printDone.csv` + `keys=` + diff key/giá trị cục bộ.

---

## 4. CHẤM — 5 rate chất lượng + CI hai độ rộng

- **5 rate** (như `research/analysis/gd92xexit_score.py`, tái dùng nguyên): `win%` · `TSloss%` ·
  `mP|SM` · `mP|SL` · `meanP`.
- **Baseline để so = đối chứng OFF CỦA CHÍNH NỀN** (cùng bảng §2): `cc-t100` vs `hn-t100`;
  `cc-g92` vs `hn-g92`; `cc-g-cp` vs `hn-g-cp`. Bổ sung (tham chiếu, **không** phải tiêu chí):
  mọi chân vs T170.
- **CI**: block-72h, **2000 rep**, seed **20260905**, anchor **2021-07-01**; báo **CẢ HAI** độ
  rộng: legacy **×1.21** (brief owner yêu cầu) và chuẩn hoá **`inflate(k) = sqrt(2 ln k)`** với
  **k = 3** (`1.482304`, `docs/AUDIT_CI_INFLATE_STANDARDIZATION.md`).
  **"XAU ngoài CI" = ngoài ở CẢ HAI độ rộng** (tiền lệ `traillad_score.py`, `exithighn_score.py`).
- **Câu hỏi trung tâm:** cap có làm **rate nào XẤU đi ngoài CI** không, và biên độ Δ là bao nhiêu.

## 5. RÀO CỨNG (`docs/RISK_APPETITE.md`) — kiểm **CẢ theo năm LẪN toàn kỳ**

`tập trung 1 coin ≤ 15%` · `UW ≤ 200 ngày` · `maxDD` theo năm **≤ 30% (S1)** và **≤ 40% (S2 —
mức hiện hành §6 RISK_APPETITE, chốt 2026-09-24)** · `quỹ xấu nhất ≥ −15%` · `không năm âm`.
Báo **CẢ HAI** chuẩn maxDD (30% và 40%) theo năm **lẫn** toàn kỳ.

**Bắt buộc in:**
1. **Tập trung 1 coin max theo thời gian** (OFF vs ON) + **số lần guard BIND** + **số leg bị chặn**
   (đếm dòng `[CONC-PC] SKIP` trong `sim.out`, đối chiếu `SUMMARY blocked=`).
2. **Bảng PnL chi tiết theo năm** cho **mỗi cặp OFF/ON**: năm · n · win% · TSloss% · meanP ·
   PnL(USDT) · ret% · maxDD% · UW · qmin% · equity ⇒ **chặn tập trung MẤT BAO NHIÊU PnL (%)**
   (toàn kỳ và theo năm).
3. `n` · `meanP/leg` · `hold_med` · `turnover` · **`Σfunding/ΣPnL`** (hạng thêm ở
   `RESULT_FRAGILITY_N` §6.3).
4. Bảng so OFF vs ON từng chân: conc · số lần bind · 5 rate ngoài CI · UW/maxDD(30/40) · năm âm.

## 6. LUẬT KẾT LUẬN (khoá trước)

- **ĐỀ XUẤT BẬT MẶC ĐỊNH** chỉ khi **CẢ BA**: (i) **0 rate XAU ngoài CI** (cả hai độ rộng) ở
  **mọi chân có bind ≥ 1**; (ii) **conc max ≤ 15%** ở mọi chân ON; (iii) **PnL mất ≤ ~10%**
  toàn kỳ ở mọi chân ON.
- Nếu ON **mất nhiều PnL** (> ~10%) **hoặc** làm **bất kỳ rate nào XAU ngoài CI** ⇒ **ghi rõ,
  KHÔNG đề xuất**.
- Chân nào `blocked = 0` ⇒ kết quả chân đó là **no-op** (không dùng để kết luận cap tốt/xấu).
- **KHÔNG tự bật** mặc định; **KHÔNG** tự tích hợp vào sản xuất. Equity/CAGR **KHÔNG** phải tiêu
  chí chọn (chỉ báo cáo).

## 7. DỰ ĐOÁN GHI TRƯỚC (để đối chiếu sau, không sửa)

| dự đoán | lý do |
|---|---|
| `cc-t100` **bind mạnh** (blocked ≫ 0), conc 28.51% → **≤ 15%** | conc vượt trần 13.5 điểm, CUDIS/ALPINE là 2 cụm lớn |
| `cc-g92` **bind ≈ 0** (OFF conc 14.38% < 15%) ⇒ **OFF ≡ ON byte-identical**, kết quả **tầm thường** | trần 15% cao hơn đỉnh lịch sử của nền GD92 |
| `cc-g-cp` bind **rất ít** (OFF 15.29%, vượt 0.29 điểm) | sát trần |
| **0 rate XAU ngoài CI** ở chân bind ≥ 1 | tiền lệ `RESULT_DCA_AGG_PERCOIN` (binding 45, 0 XAU) |
| PnL mất ở `cc-t100` **nhỏ** (< 10%) | ở vòng DCA cap chỉ mất ~1.8% equity |
| **KHÔNG** chân nào GO (T100/GD92 base vốn FAIL rào cứng toàn kỳ) | đây là phép đo cơ chế |

## 8. KỶ LUẬT

Không push. Không merge `gd92-recheck`. Code rolling cherry-pick `-n` rồi `git checkout -- src/`.
Chỉ commit docs + script + profile. Không chạm 242. Không đóng holdout 2026. Không quét biến thể
(pct 0.10/0.20, aggregate cap, biến thể exit/gate mới). Không đổi incumbent (T170 giữ).
Dọn temp sau khi xong.
