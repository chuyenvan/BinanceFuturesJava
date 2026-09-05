# QUEUE — hang doi thi nghiem DEV, theo thu tu

Doc `docs/AGENT_RUNBOOK.md` truoc. Moi job phai co `docs/PREREG_*.md` commit TRUOC khi chay.
Lay job DAU TIEN co status `READY`. Job `BLOCKED` phai cho user duyet trong chat.
Sau khi xong: doi status thanh `DONE <commit>`, ghi ket qua vao doc rieng, commit.

---

## Q1 — Chot horizon time-stop  [BLOCKED: can user duyet mo lai quota] — LUU Y: F2/T1/W1 deu thay cat som keo UW len 150-190d; mo lai chi khi rang buoc UW<=120 duoc chap nhan la tieu chi

E1 da dung het quota 4/4 (`docs/PREREG_EXIT.md`) va ra phan quyet TS_H=72.
Nhung pre-reg co 2 loi dac ta, agent tu phat hien va KHONG sua sau:
- P2 do **count tuyet doi** cua `STOP_MARKET_DONE` nen bo qua win rate tut
  84.85% -> 79.21% (tong lenh tang 970 -> 1010 vi cat som giai phong margin).
- Rang buoc cung dat theo **NAM** nen X72 pass, du underwater dai ra
  **93 -> 156 ngay** va 2022Q1 di tu +0.7% xuong **−4.4%**. Neu dat theo QUY thi
  X96 va X72 deu bi loai.

Day la van de vi underwater 93 ngay la **ly do duy nhat** con bien minh cho viec
giu C2b (xem AGENT_RUNBOOK muc 4). X72 danh doi dung cai do.

**Can user quyet:** mo lai quota voi pre-reg sua 2 loi tren (P2 do TY LE thang,
rang buoc theo QUY + underwater <= 120 ngay), hay chot X96 (maxDD −10.7%, tot nhat
trong 4 run, mean(profit|SL) −13.99 vs −18.90 parity), hay giu 168h.
KHONG duoc tu chon X96 sau khi da thay so — do la sin.

---

## Q2 — Ban le STRONG/WEAK `TS_PNOPUMP_WEAK_THR`  [DEAD KEY — W1 bd20e42: mergeOrder() khong chep symbolPred, 100% lenh WEAK cap 0.03. Sua bug truoc, roi quet lai]

**Co che:** ban le dang 0.29 ma **88.55% hang duoc admit co score < 0.30**. Tuc ban le
nam dung giua dai van hanh — dich mot chut la lat hang loat lenh giua cap giveback
8% (STRONG) va 3% (WEAK). Chua tung co run don le nao. Sobol hang 10 (0.0099).

**Runs: dung 3.** `SIM_TS_PNOPUMP_WEAK_THR` in {0.05 (tat ca STRONG), 0.29 (parity),
0.60 (tat ca WEAK)}. Nen C2b, 1 dataset build. Tag `W005` / `W029_parity` / `W060`.
Dat qua **profile copy**, khong qua env (bay so 2).

**Tieu chi PRIMARY (rate tren 800+ lenh):** `mean(profit | STOP_MARKET_DONE)` va
`sd(profit | STOP_MARKET_DONE)`. Gia thuyet: cap rong hon (STRONG) => giu winner lau
hon => mean cao hon nhung sd cao hon. Neu mean **khong** doi qua 0.5pp giua 0.05 va
0.60 thi ban le nay TRO va dong lai vinh vien.
**Rang buoc cung:** maxDD <= 15%, underwater <= 120 ngay, khong quy nao < −5%.
**Parity gate:** `W029_parity` phai byte-identical C2b (md5 8f7afdfb...).
**Quy tac quyet dinh:** chon bien the co mean(profit|STOP_MARKET_DONE) cao nhat MA
thoa het rang buoc cung. Neu ca 3 trong sai so thi ghi null va dong huong.

---

## Q3 — Siet momentum gate  [DONE W1 bd20e42: 5 rate don dieu nhung FAIL underwater 172/223d > 120; D va E la CUNG truc (ti so MIN_MOM/RATE_MAX). Null cho ung dung]

**Co che:** chieu NOI da thu va xau: 0.006 -> equity cao hon (60,953) nhung maxDD
**−21.1%** (vuot tran 15%); 0 -> 10,305 voi 14,007 lenh. Chieu SIET **chua tung thu**
tren nen C2b. Gia thuyet: siet cat dung nhom lenh bien — nhom chiem phan lon 147 lenh
bi time-stop (66.6% chua tung vuot +3% lai).

**Runs: dung 3.** `SIM_MIN_MOMENTUM_15M` in {0.008 (parity), 0.010, 0.012}.
Tag `M008_parity` / `M010` / `M012`. Profile copy.

**Tieu chi PRIMARY (deu la rate):** `TSloss%` (= n STOP_LOSS_DONE / n tong) phai
GIAM don dieu khi siet; `win%` phai TANG; `mean(profit|STOP_MARKET_DONE)` khong
duoc giam qua 0.3pp.
**Rang buoc cung:** so lenh khong duoi 600 (duoi nua thi mat het power do luong);
maxDD <= 15%; underwater <= 120 ngay.
**Quy tac quyet dinh:** chon muc siet cao nhat thoa het dieu tren. Neu TSloss%
khong giam don dieu => co che sai, ghi null, dong huong.

---

## Q4 — Mo DEV ve 2021-07  [BLOCKED: can user quyet danh doi]

Chi tiet `docs/D1_DATA_AUDIT.md`. Trang thai:
- Moc som nhat kha thi = **`20210701`** (train 329,882). `20210401` train = 0 vi
  `wfo_gate_pred.csv` bat dau 2021-03-31. => **duoc +6 thang, khong phai +11.**
- Aerospike da du 2021, **khong can copy gi**.
- `rk_oi_delta24h`: cat mat ~0 (mean IC 0.0000, doi dau, |IC| max 0.0165).
- `ls_global`: cat mat THAT — mean IC −0.0396, manh thu 4/9, 1 trong 4 feature
  nhat quan dau, ~13% tong |IC| cua nhom nhat quan. Sau khi cat, S1 con 3 feature
  nhat quan => gan nhu thuan volatility/drawdown.
- Trong 2021 CA HAI = noise (OI 1 coin/thang toi 2021-11) => giu chung khi mo ve
  2021H2 con **te hon** cat.
- **BLOCKER cho tang tien:** `predwf_G015x26` khong co bin 2021 (som nhat 20220101)
  va G015x26 KHONG reproduce duoc. => mo 2021 chi validate duoc **tang selector**
  (rank-IC / edge5) qua Python, **KHONG chay duoc Java sim**. Muon co equity 2021
  phai train G015 moi cho 2021Q3/Q4 — luc do khong con la G015x26 va provenance
  cua C2b doi.

**Can user quyet:** (a) chi lam tang Python de biet selector co on dinh qua regime
bull khong — nhung da chot la selector khong quan trong, nen gia tri thap; hoac
(b) train G015 moi cho 2021 va chap nhan doi provenance baseline; hoac (c) bo qua.

---

## Q5 — Sizing  [DONG — khong chay]

`F_BASE` (importance #1 Sobol, PDP don dieu −4.83 -> +8.12pp), `U_MAX` (#4),
`DCA_GRID_SCALE` (#3, 1.5 -> 2.0 cho 59,227 nhung maxDD −15.55 vuot tran).
**Ly do dong:** sizing khong doi chat luong tung lenh, chi doi thang do. Tieu chi
duy nhat con lai la maxDD/underwater — deu single-realization, n_eff nho, khong co
power. Day la nut risk preference user dat, khong phai bai toan toi uu.
Mo lai chi khi user noi ro muc rui ro muc tieu (vd "chap nhan maxDD 20% de doi CAGR").

---

## Q6 — No ky thuat, khong sinh alpha nhung phai lam  [READY, uu tien thap]

1. Patch `VisionMetricsClient.parseDay` (lo 5-phut forward) — BAT BUOC truoc moi
   rebuild OI.
2. Rotate API key trong git history.
3. Don 5 key chet khoi `configs/c2b.properties` + `c2b_ticklog.properties` roi bat
   `CONFIG_STRICT=1` lam gate mac dinh.
4. Dong venh K=8 (sim) vs K=5 (live).
5. Giai phong dia: an toan cao ~9.5 GiB, can xac nhan ~30 GiB (`docs/D1_DATA_AUDIT.md`
   muc D). **2 bay:** `up5/*.zip` va `up_zip/*` cung inode (nlink=2) => xoa 1 ben
   duoc 0 byte; truncate set Aerospike KHONG shrink `.dat`.

---

## F1 — Nới dòng cơ hội ở tổng exposure không đổi  [DONE `d6935ef`]

**Kết luận:** NULL — `SELECTOR_RANK_TOPK` 8→16/24/32 (bù `SIM_F_BASE` giữ
`K × F_BASE = 0.24`, C1 lệch chỉ +4%) làm `sd(daily)` giảm đúng dự đoán
(0.008098→0.006913) nhưng `mean` giảm gấp 3 lần thế, Sharpe 1.491→0.980, và cả 3
biến thể LOẠI ở ràng buộc cứng (underwater 195/227/254d vs 93d) ⇒ **giữ K=8, đóng
hướng**. Cơ chế: `medP`=5.50 không đổi nhưng `TSloss%` tăng đơn điệu 15.2→21.7%
trên 970→2,779 lệnh — rank sâu chết bằng time-stop nhiều hơn, không phải thắng ít hơn.
Pre-reg `576e6c2`, chi tiết `docs/F1_FLOW_RESULT.md`.

---

## F2 — Conditional exit: cắt lệnh KHÔNG CHẠY tại giờ H  [DONE `7d0eb38`]

**Kết luận:** NULL — luật "chưa arm + giữ > 72h + đỉnh đạt được < 5%/4% ⇒ đóng market"
cắt TRÚNG nhóm chết (`mean(profit|STOP_LOSS_DONE)` −18.90 → −13.95%, `mean(profit|
STOP_MARKET_DONE)` chỉ −0.034pp) nhưng **FAIL 2/3 PRIMARY** (`TSloss%` 15.15→19.04,
`win%` 85.26→81.66) và **FAIL ràng buộc cứng** (underwater 93→156 ngày, cùng con số của
E1 `X72`) ⇒ **đóng hướng**. Cơ chế hỏng ở đường truyền: margin giải phóng sớm KHÔNG quay
vòng đủ (tổng lệnh chỉ 970→1,003, +3.4%) nên không pha loãng được mẫu số — lần thứ hai
sau F1 một hướng chết vì kênh tái triển khai vốn yếu hơn giả định. Equity cao hơn
(60,390→61,851/62,317) nhưng đi NGƯỢC phán quyết và nằm trong nhiễu 2.57pp ⇒ không dùng.
Đo offline `docs/F2_COND_EXIT_MEASURE.md` (join nhãn 100%, dự báo số lệnh bị cắt 146 vs
thực tế 148 — công cụ dùng được). Pre-reg `a4b3b05`, chi tiết `docs/F2_RESULT.md`.
Param `SIM_COND_EXIT_HOURS` / `SIM_COND_EXIT_MIN_FAV` giữ trong code, mặc định 0 = TẮT.

---

## F3 — Nguồn cung hay tầng quyết định?  [DONE `5a32d0e`]

**Kết luận:** hệ bị giới hạn bởi **CUNG**, nhưng trục khan hiếm là **THỜI GIAN gate thị
trường mở** (`p15` là scalar mức-tick, `sd` trong tick = 0; `spearman(npass,p15)`=+0.454 vs
`spearman(npass,U)`=+0.021) — **không phải universe**: mục A không khử được confound
(`spearman(U,tháng)`=+0.995, mọi spec khử confound MDE80 ≥ 1.09 ⇒ **không kết luận được**),
và A7 cho thấy U to hơn cải thiện ĐIỂM của top-8 (t=−4.9) nhưng KHÔNG cải thiện kết quả
thực (`g1lite` +0.03 CI[−0.16,+0.22]) ⇒ **đóng hướng mở universe**. 86.6 coin good/giờ-gate-mở
nhưng chỉ 2.90 qua gate và **94.85% giờ-gate-mở có 0 cơ hội**; vị thế đang giữ = **6.275**
trong giờ-gate-mở (1.894 trên mọi giờ) ⇒ vốn KHÔNG nằm không lúc có cơ hội — lý do E1/F1/F2
đều null. B bác lại cách đọc "medP bất biến": `P(good)` 0.699→0.565 và `mean(g1lite|good)`
0.1778→0.1070 theo độ sâu rank (t=24.8); median là đại lượng trơ. D: hạ K=8→5 mất **33.54%**
nguồn cung good qua gate và **32.0%** khối lượng `g1lite` ⇒ khe K=8/K=5 là lỗ hổng
**fidelity** (`Q6.4`), không phải nguồn alpha. Chi tiết `docs/F3_SUPPLY.md`, script
`research/analysis/f3_supply.py`. **Không pre-reg** (đo offline thuần, không chạy sim).

---

## F4 — Tầng timing có phải nơi chứa alpha?  [DONE `0c649e0`]

**Kết luận:** NULL — nhưng là **null KHÔNG CÓ POWER**, và đó mới là kết quả chính. Dựng lưới tick
mở rộng **86,971 tick** DEV (từ `wfo_gate_pred.csv` + `predwf_G015x26` + `label_15m`, vì
`cand_dev.parquet` chỉ có 4,639/87,552 tick) rồi đo rank-IC với `Y_tick` = `mean(g1lite)` top-8:
`p15` **+0.1000**, `br_lag3` +0.1553, `p15_ma24h` +0.1088, `mkt_vol7` +0.0901, `mkt_dd7` +0.0186
(dấu LỆCH). **Không ứng viên nào đạt ngưỡng** (CI của hiệu, block 72h × 2000 rep × f=1.21, đều
chứa 0) ⇒ `p15` giữ nguyên. Lý do thật: `sd_boot = 0.033` ⇒ **`n_eff ≈ 908`, KHÔNG phải 86,615**
(hệ số phóng đại 95×) ⇒ **MDE80 của hiệu ≈ 0.13 > chính rank-IC của incumbent (0.100)** — cuộc thi
gần như không thể thắng. **Giả thuyết "chuyển sang mức tick sẽ phá tường power" là SAI**; `n_eff`
tỷ lệ với số khối 72h (tức độ dài lịch sử), không với tần suất lấy mẫu. Ứng viên khá nhất
`br_lag3` mất **38%** rank-IC khi bịt rò rỉ ~1 ngày (`br_lag4` +0.0973, 2022 sụt +0.138→+0.031)
và khi đó **thấp hơn** `p15`. Model tổ hợp 5-biến (XGB CPU, WFO quý, purge 72h) **THUA biến đơn**:
+0.0866 vs +0.1297 OOS. `mkt_dd7` bị loại dứt khoát (CI hiệu trên `Y2` nằm trọn dưới 0).
**False negative (cả 2 định nghĩa gate):** gate CÓ chọn lọc thật — `q = P(Y|ĐÓNG > median(Y|MỞ))`
= **0.3534** (Gate-A `p15>=0.008`) và **0.2277** (Gate-B `gate_dyn_ok`), giảm đơn điệu từ 0.5;
`mean(Y|MỞ)−mean(Y|ĐÓNG)` = +0.0224 / +0.0727; `P(good)` 0.669/0.544 và 0.782/0.549. NHƯNG khối
lượng tick trên-trung-vị ngoài gate = **29,115** (12.67× so mốc) / **19,694** (83.98×) vì tập ĐÓNG
lớn gấp 18×/184× ⇒ đây là bài toán **đặt ngưỡng**, không phải **chọn biến**. Cảnh báo: đếm TICK
chứ không phải cơ hội độc lập (~101 đợt sau khi khử chồng lấn 72h), `Y_tick` là danh mục KHÔNG
giao dịch được, không có xác nhận P&L. Hướng mở duy nhất: **sweep ngưỡng `p15`** trên lưới đã dựng
`/home/ubuntu/ledger/f4_ticks.parquet` — chi phí ~0, nhưng chỉ chạy nếu viết được công thức đánh
đổi precision/coverage TRƯỚC. Pre-reg `1fa042d`, chi tiết `docs/F4_TIMING.md`, script
`research/analysis/f4_timing.py`.

---

## G1 — Tầng đặt GIÁ TRỊ gate có nên chuyển sang horizon 72h?  [DONE]

**Kết luận:** NULL **có hướng NGƯỢC** — không phải null thiếu power. Train lại đúng recipe
G015 (45 feature, XGBClassifier, 10 cutoff, purge 72h, CPU, seed 42), đổi **duy nhất** nhãn
`maxFav_4h>=0.06` → `maxFav_72h>=0.07` (0.07 = đúng `SIM_RATE_PROFIT_STOP_MARKET`), được `G72`.
`G72` xếp hạng **KÉM HƠN** `G4_repro` **ngay trên outcome 72h mà nó được train**:
AUC **0.6259 vs 0.6558**, hiệu **−0.0299** CI95×1.21 **[−0.0459, −0.0145]** (nằm trọn dưới 0),
`P(d>0)=0.0000`, dấu nhất quán **3/3 năm** (2022 −0.0332 / 2023 −0.0326 / 2024 −0.0277).
spearman vs `Y72` −0.0498 [−0.0763, −0.0243]; vs `g1lite` −0.0290 [−0.0579, +0.0013].
`n=15,442,092` dòng OOS DEV, join nhãn **100.00%**, **304 khối 72h**, 2000 rep, seed 20260906.
**Cổng GO/NO-GO FAIL ⇒ 0/2 sim run đã chạy**; `PREREG_G1_SIM.md` không được thực thi, không có
số parity/PRIMARY/equity. **`predwf_G015x26` giữ nguyên, C2b không đổi gì.**
**Cổng REPRO PASS tuyệt đối:** `g72_train.py` với nhãn cũ ra **byte-identical 10/10** với
`predwf_G015_v2`, `spearman=1.00000000` trên 15,536,189 bản ghi, `rho=0.18991` khớp
`G015_PROVENANCE §0` ⇒ đổi nhãn là biến duy nhất. Đây cũng là **xác nhận độc lập thứ ba**
rằng pipeline G015 deterministic.
⚠️ Pre-reg §1 đã cảnh báo trước "H1 gần như hiển nhiên đúng vì G72 train trên chính họ nhãn
dùng để chấm" — **cảnh báo đó SAI ở dấu**, ghi lại nguyên vẹn.
Bác bỏ **đúng một mệnh đề**: "đổi nhãn G015 sang 72h/7% thì gate tốt hơn". **Không** bác bỏ
"horizon là trục có tác dụng" — mới chạm 1 họ nhãn / 1 ngưỡng / 1 kiến trúc.
Hướng gate còn mở vẫn là **hiệu chuẩn ngưỡng theo phân vị của chính S1** (`C2B_SPEC §1`).
⚠️ Caveat window overlap: bảng động cơ "so horizon trên 970 lệnh thật" bị nhiễm (ROI tới 168h),
`LABEL_ROI2 §2` đã retract vì đúng lý do đó — **không trích làm bằng chứng**.
Pre-reg `f931265` + `6519c22`, chi tiết `docs/G1_HORIZON.md`, script
`research/pipeline/g72_train.py`, `research/analysis/g1_repro_check.py`,
`research/analysis/g1_horizon_eval.py`.

---

## BD — Train ở đâu được: Oracle hay Kaggle?  [DONE]

**Kết luận:** **Kaggle CPU == Oracle CPU byte-for-byte** ⇒ được train ở bất kỳ đâu trên CPU,
vô điều kiện. 3 môi trường × 3 seed trên cùng một file đã đóng băng (`bench_s1.parquet`,
1,220,490 dòng, sha256 file + sha256 mảng X **khớp tuyệt đối** cả 3 nơi). Oracle (aarch64,
py3.10.12, numpy 2.2.6) vs Kaggle CPU (x86_64, py3.12.13, numpy 2.0.2): per-tick
`mean|ΔrankIC|` = **0.0 chính xác**, `ic_sha256` trùng cả 3 seed, cây đầu tiên trùng sha256.
Số cũ `0.17040 vs 0.1723` là **lệch dữ liệu/pipeline, không phải lệch máy** — không được dùng
để khoá vào Oracle. **GPU lệch thật nhưng vì lý do khác lệnh cấm cũ:** per-tick 0.02185 chỉ
**×1.07–×1.20** nhiễu seed và `edge5` 0.198pp chỉ **×1.21**, nhưng `|Δ mean rank-IC|` = 0.00448
là **×3.7** nền seed của CPU, và GPU **tự nó nhiễu gấp 4.8 lần** CPU (0.00586 vs 0.00121).
Nguyên nhân chỉ ra được từ cây đầu tiên: `Cover` lệch **31/31 node** (RNG `subsample`/
`colsample_bytree` khác) + `Split` lệch 11/31 (quantile sketch `hist` khác).
**`nthread` không ảnh hưởng gì:** `n_jobs=1` vs `4` cho tree1 trùng sha, `ΔIC` = 0.0.
**Cổng `spearman >= 0.999` bị bỏ:** đo lại đúng thống kê đó trên 774,270 dòng OOS —
CPU-vs-GPU cùng seed **0.9813**, CPU seed42-vs-seed43 **cùng máy cùng device 0.9817**. Đổi
device tốn đúng bằng đổi seed; ngưỡng 0.999 loại cả việc re-seed chính mô hình, nên nó đo
"có phải cùng một mô hình không" chứ không đo "môi trường có lệch không". Chính cổng này tạo
2 false positive, không phải GPU. Thay bằng: **hiệu ứng phải vượt CI multi-seed (≥3 seed) đo
trong cùng một môi trường**. Giữ nguyên: không ghép số từ 2 môi trường trong một so sánh;
GPU thì CẢ phép so phải trên GPU; parity/byte-identity chạy trên đúng device sinh ra neo;
Java sim ở lại Oracle (data host + neo 60390).
⚠️ Chưa đo: XGBClassifier (G015), Java sim, và GPU không phải T4 (chỉ đo T4 của Kaggle).
Chi tiết `docs/BENCH_DEVICE.md`, script `research/kaggle/bench_device/`,
Kaggle: dataset `chuyendinh/bench-device-pool`, kernel `bench-device-{cpu,gpu,pgpu}`.

---

## W1 — Quét các trục CHƯA TỪNG SWEEP trên nền C2b  [DONE]

**Kết luận lớn nhất KHÔNG phải một tham số tốt hơn — mà là một BUG.**
`SIM_TS_MAX_GAP` (trục A, 3 mức) và `SIM_TS_PNOPUMP_WEAK_THR` (trục C, 2 mức) cho
`printDone.csv` **byte-identical với parity ở cả 5 run**. Nguyên nhân:
`SimulatorMarketLevelTicker1MStopLoss.mergeOrder()` (dòng 730-777) tạo object cụm mới mà
**không chép `symbolPred`**, trong khi `trailRate()` chạy trên chính object cụm đó và có
fallback `pnp = (symbolPred != null) ? symbolPred : 1f`. ⇒ `1f > thres` luôn đúng ⇒
**100% lệnh đi nhánh WEAK, cap = 0.03; nhánh STRONG chưa bao giờ được gọi.**
⚠️ Vậy mô tả exit trong `AGENT_RUNBOOK §3` và `C2B_SPEC` ("cap 0.08 STRONG / 0.03 WEAK,
bản lề `symbolPred < 0.29`") **SAI cho sim**. Cột `symbolPred` trong printDone vẫn có số thật
vì `closeOrder()` ghi từ object LEG — nhìn CSV sẽ tưởng trailing đã dùng nó, nó chưa từng dùng.
`DumpConfig` đổi giá trị cho cả 2 key ⇒ **DumpConfig-đổi KHÔNG đủ để kết luận key sống**.

**Trục D và E không độc lập:** gate chỉ phụ thuộc TỈ SỐ `MIN_MOMENTUM_15M / PREDICT_SYMBOL_RATE_MAX`
(nhánh sàn `AI_DYNAMIC_MIN` không bao giờ chạy vì `symbolPred` min 0.0723). `E010` byte-identical
`D012`, `E012` byte-identical `D010` ⇒ 4 run = 2 điểm thông tin.

Phán quyết: **A, C = key chết** (đóng trục, chờ sửa `mergeOrder` rồi quét LẠI TỪ ĐẦU).
**B (`TS_MAX_GAP_WEAK`) = null** — 0/7 rate pre-reg đơn điệu (chỉ `medP` và `maxDD` đơn điệu,
cả hai đều ngoài danh sách pre-reg; `medP` đơn điệu là hệ quả số học của `exit = peak - min(peak/2, cap)`).
**D+E = đơn điệu mạnh nhưng bị ràng buộc cứng loại** (win% 85.26→85.56→86.90, TSloss% 15.15→15.06→13.29,
mean(profit|SM) 7.48→7.83→7.86 đều đơn điệu; nhưng underwater 93→172→223 ngày, cả 2 mức FAIL).
**F (`DCA_GRID_WEIGHTS`) = có tín hiệu nhưng CONFOUND sizing** — tổng trọng số giữ 1.0 nên leg đầu
tụt còn 0.5/0.4 lần budget, `mean(margin)` 971→593→497; maxDD −13.12→−9.12→−7.62 là thứ bất kỳ lệnh
nhỏ hơn nào cũng tạo ra, mà sizing KHÔNG đo được trên DEV (`RUNBOOK §4`). Mảnh duy nhất không giải
thích được bằng sizing: `mean(profit|STOP_LOSS_DONE)` −18.90→−18.09→−17.37 (đơn điệu, bớt lỗ 1.53pp)
— DCA hạ giá vốn của đúng nhóm time-stop, kênh mất tiền lớn nhất.
**G (`N4_a8s175`) = LOẠI**: underwater 140 > 120 và quý 2022Q4 = −5.3% < −5%. Arm 7%→8% đẩy thêm
4pp lệnh sang time-stop (TSloss 15.15→19.17). Số cũ 61,148/974 lệnh **không tái lập** (chạy lại:
61,592/918) vì khác jar + khác đường cấu hình — không được ghép 2 số này.

**Không đề cử ứng viên baseline mới** (quét khám phá). Hai thẻ mở:
(1) sửa `mergeOrder` chép `symbolPred` rồi quét lại A và C từ đầu — hiện là vùng trắng;
(2) pre-reg riêng cho DCA **tách khỏi sizing** (bù `DCA_GRID_SCALE` để `mean(margin)` không đổi),
chỉ kiểm một giả thuyết: DCA có hạ `|mean(profit|STOP_LOSS_DONE)|` không.
Parity OK (md5 `8f7afdfb27b15f5b6d4c886700def93c`, b:60390, 970 lệnh). 16 run, 1 dataset dùng chung.
Pre-reg `e606b76`, chi tiết `docs/W1_SWEEP.md`, script `research/analysis/w1_rates.py`.

---

## T1 — 3 chan C2b vs "maxfav6" 4h/72h, DI HET TOI SIM  [DONE]

`LABELH` dung o rank-IC va ket luan null; T1 di het luong (train S1 -> build_map -> bins -> sim
-> rate + equity). Pre-reg `26a45ee`, chi tiet `docs/T1_LABEL3.md`.

**Cong REPRO PASS**: `spearman(harness L_g1, pred_s1a2)` = **1.000000** / 774,270 dong.
**Parity PASS hai duong**: Oracle `T1_g1o` **byte-identical** `C2b` (b:60390, 970,
md5 `8f7afdfb…`); Kaggle `t1-g1` = neo 60395/970/`910f1aa6…`.

**Phan quyet**: `L_f4` (`1{maxFav_4h>=0.06}`, dung cau hoi user) **KHAC C2b theo huong XAU HON** —
2/4 rate PRIMARY ngoai CI cung huong o khoi 72h va 24h (`TSloss%` +2.53pp, `win%` -2.47pp;
o 168h chi con 1/4). `L_f4q` (ngu phan vi 4h = ban `LABELH`) va `L_f72` (`1{maxFav_72h>=0.06}`)
**KHONG PHAN BIET DUOC tren rate** (0/4). **Ca ba FAIL rang buoc cung**: maxDD -16.47 / -15.02 /
-15.12, underwater 161 / 187 / 95 ngay, quy min -5.0 / -6.0 / -4.1. => khong chan nao thay C2b.

**Ba thu hoc duoc, quan trong hon ket qua chinh:**
1. 🔴 **Bay #13 — bins KHONG di qua duong Kaggle.** `WFO_FUNDING_PRED_DIR` bi tieu thu o
   `ExportWfoDataset`, kernel Kaggle chi chay sim tren dataset DA BUILD => 3 chan bins khac nhau
   deu ra md5 printDone y het parity, **im lang khong loi**. Da bo 3 run do va chay lai o Oracle.
   `docs/KAGGLE_SIM.md §6`. Bay #14: `/kaggle/input` khong phang.
2. **"Null o rank-IC" KHONG dong nghia "vo hai".** `L_f4q` khong phan biet duoc o CA rank-IC lan
   rate, nhung underwater 93 -> **187 ngay** va maxDD -13.12 -> -15.02. `LABELH` dung o rank-IC
   nen khong the thay dieu do.
3. **rank-IC selector la proxy yeu cho rate**: `L_f4` khong phan biet duoc o moi tieu chi rank-IC
   (CI chua 0) nhung o sim thi khac that.

Cau hoi goc cua `CEIL_RESULT §3` (nhan **168h**) van nguyen — T1 chi kiem 4h va 72h.

---

## T2 — ghep selector C2b vao LUONG DAY DU (big_down + DCA)  [DONE]

Cau hoi user: "ghep c2b vao luong sim hien tai... thay c2b voi selector cu".
Pre-reg `8aa20e3`, chi tiet `docs/T2_FULLFLOW.md`. 4 run, Oracle, 2 dataset build.

**Kham pha (muc 1)** — `big_down` KHONG phai key config: no la `MarketLevelChange.BIG_DOWN`
(`rateDownAvg < MS_DOWN_BIG_AVG = -0.03157`), bat/tat bang **`SELECTOR_ONLY_ENTRY`**
(`Simulator...:271`). Leg BIG_DOWN **BO QUA gate AI** (`Simulator...:817`). DCA tat bang
**`DCA_GRID_WEIGHTS=1,0,0,0`** (cong `gridLegWeightRatio<=0` chan moi leg >= 2). **Hai co doc
lap** — dinh chinh `C2B_SPEC:73` (dong do ghi `SELECTOR_ONLY_ENTRY` tat ca BIG_DOWN lan DCA_LEVEL1).
"Luong day du" duoc **dinh nghia lai** = `c2b_min` tru 2 cong nghien cuu (delta 2 key), KHONG
dung `D0_full`/`G1_giveback5` lich su (khac jar, dataset da xoa — bay da dinh o `N4_a8s175`).
"Selector cu" = **`predwf_G015_v2`** (ban `G015x26` goc KHONG tai lap duoc), kem hieu chuan gate
`SIM_MIN_MOMENTUM_15M=0.014052` cua `c3.properties`.

**Parity PASS**: `T2_c2b_ref` byte-identical `C2b` (b:60390, 970, md5 `8f7afdfb…`).

**Phan quyet cau hoi user (`T2_full_c2b` vs `T2_full_old`): KHONG PHAN BIET DUOC** — 1/6 rate
PRIMARY ngoai CI (`mean(profit)` +2.05, CI [+0.06,+4.01]); can >= 2. `TSloss%` -4.46 va `win%`
+4.57 nghieng ve C2b nhung cham bien CI.

**Nhung phep so do duoc thuc hien o diem van hanh gan nhu vo hieu:** luoi DCA thiet ke `1,1,3,8`
lam leg dau chi con `1/13` suat budget ma `DCA_GRID_SCALE` van 1.5 (khong bu) =>
**`mean(margin)` 971 -> 9.21 (105 lan nho hon)**, `total margin deployed` 941,920 -> 9,908,
**CAGR 24.48% -> 0.36%** (`full_old` 0.32%). maxDD -0.1% cua chung **khong phai an toan** —
la khong co gi de mat. `T2_full_old` van **FAIL** rang buoc cung (underwater **147** > 120).

**Ket qua sach nhat cua batch — `T2_full_c2b_noDCA` (big_down BAT, DCA TAT):**
**0/6 rate ngoai CI** so voi `c2b_min`. 120 leg BIG_DOWN (11.7% so lenh, y het 120 o ca 3 chan
vi tin hieu market-level khong phu thuoc selector), maxDD -12.9 vs -13.1, underwater 93 = 93,
equity 61,287 vs 60,390 (trong mien nhieu 4.28pp cua N=4). => **bat big_down mot minh vo hai
va gan nhu vo ich** — dang chu y vi no bo qua gate.

Status moi duy nhat cua luong day du: **`REQUEST` 1/2709** o `T2_full_old` (lenh chua dong toi
`SIM_END_DATE`). Khong co status exit moi nao khac.

**Khong de cu ung vien baseline moi.** The mo: chay lai luong day du voi `DCA_GRID_SCALE` **duoc
bu** (~19.5 cho luoi 1,1,3,8) de giu `mean(margin)` ~971, kiem `CapacityProbe` truoc — dung the
ma `W1_SWEEP muc 10` da mo.

---

## T2b — luong DAY DU voi SIZE DUOC BU: C2b vs selector cu  [DONE]

Chua T2 de lai: `DCA_GRID_WEIGHTS=1,1,3,8` khong bu `DCA_GRID_SCALE` => `mean(margin)`
971 -> 9.21, ca hai chan chay o ~1% von nen phep so selector vo nghia.
Pre-reg `0058c35`, chi tiet `docs/T2B_FULLFLOW.md`. 3 sim run (parity tai dung `T2_c2b_ref`).

**🔴 BUG SIZING — tong trong so DCA bi chia HAI LAN.** `TradeUtils.managerBudget` da chia
`/dcaGridTotalWeight()` (comment: "chua cho du ladder DCA"), roi `DcaUtils.gridLegWeightRatio`
chia tiep `w[i]/total` => `margin(leg i) = 35000 x F_BASE x throttle x SCALE x w[i] / total^2`.
Voi `1,1,3,8` thi **`total^2` = 169, khong phai 13**. He so do duoc 106.19 = 169 / 1.59 (1.59 =
`throttle` noi lai tu 0.6165 -> 0.9812 vi gan nhu khong dung von) — **khop tuyet doi**.
`balanceBasic` la HANG SO 35000 => size khong compound. `getBudget()`/`BASE_BUDGET=700` la
**tham so chet** (`managerBudget` khong doc no).
=> **Dinh chinh `W1_SWEEP muc 10` va `T2_FULLFLOW muc 5`: scale bu dung la 253.5 (=1.5 x 169),
KHONG phai 19.5.**

**Hieu chuan PASS lan dau, khong dung quyen sua 1-lan**: `SCALE=253.5` cho `mean(margin)`
leg 1 = **947.00** vs muc tieu 971.05 (**-2.5%**, cong ±20%). Ap y het cho ca 3 chan.

**Parity PASS**: `T2_c2b_ref` byte-identical `C2b` (b:60390, 970, md5 `8f7afdfb…`); jar sha256
khong doi, `find src -newer <jar>` rong.

**PHAN QUYET CAU CHINH (`T2b_full_c2b` vs `T2b_full_old`): KHAC — selector C2b THANG.**
Hai duong doc lap: (1) **2/6 rate PRIMARY ngoai CI cung huong** (`mean(profit)` 3.79 vs 1.45,
+2.34 CI[+0.30,+4.39]; `mean(margin)` +192 CI[+57,+320]) — vuot nguong `>=2`; (2) `T2b_full_old`
**FAIL 4/4 rang buoc cung** (maxDD **-41.6%** @2022-11-10, UW **390 ngay**, nam 2022 **-29.7%**,
quy 2022Q2 **-27.3%**) => loai truc tiep. `T2b_full_c2b` PASS het (maxDD -11.5, UW 81, quy min
-1.4, n=1068). Equity 64,809 (CAGR 28.05%, Sharpe(q) 1.28) vs 42,687 (8.30%, 0.15) — **khong
phai tieu chi**, chan tren nam trong nhieu 4.28pp so voi ref.

**Bien so DUY NHAT doi so voi T2 la size.** T2 = 1/6 ngoai CI ("khong phan biet duoc"), T2b =
2/6 + FAIL 4/4. => **mot phep so o diem van hanh sai co the tra null ma khong phai vi hai vat
giong nhau.** Canh bao khi trich: `mean(margin)` la bien KIEM SOAT (lech vi `full_old` mo 2.5x
so lenh => `throttle` thap hon), nen bang chung CHAT LUONG chi la `mean(profit)`; "selector cu"
la **goi bins `G015_v2` + gate 0.014052** (2 bien, ghi truoc); va **uu the cua C2b van la hien
tuong 2022** — bo 2022 ra thi ban cu con cao hon (65.5+4.8 vs 41.5+6.8), dung hinh dang ma
`SELECTOR_LADDER_Q` da canh bao.

**PHAN QUYET CAU PHU (DCA co dang bat khong): KHONG DANG** — `T2b_dca_c2b` vs ref **0/6 rate
ngoai CI** (dieu kien `sum(pnl)` leg 2+ duong thi DAT: +3,177). Bat ca hai co che
(`T2b_full_c2b`) cung 0/6 vs ref. Ghep voi `T2_full_c2b_noDCA` (big_down mot minh, 0/6):
**khong co che nao trong luong day du phan biet duoc voi `c2b_min` tren rate.**

**PnL tach theo leg — dau DAO CHIEU theo selector** (tai lap leg index bang gom `(sym,end)`,
khop 100% so dong `DCA_LEVEL1`): leg 2+ lai **+3,398 USD / 21 leg** (`full_c2b`, mean profit%
**+17.9**) nhung **-4,239 USD / 45 leg** (`full_old`, **-3.3**). DCA chi no trong quy sap
(2022Q2 + 2022Q4 + 2024Q2, **0 leg suot 2023**) va cham rat it (1.7-2.0% so leg) vi luoi
`-50/-75/-90%`. Bu size KHONG lam DCA cham nhieu hon (21 leg o T2 = 21 leg o T2b).
`BIG_DOWN` = **dung 120 leg** o moi chan bat no (tin hieu market-level, khong phu thuoc selector).

**Khong de cu ung vien baseline moi.** The mo: `mean(profit|STOP_LOSS_DONE)` -18.90 -> -16.37
va maxDD -13.1 -> -11.6 / UW 93 -> 81 cua chan DCA **o cung muc size** (lech 1.1%) — lan dau
hieu ung nay khong giai thich duoc bang sizing, nhung van trong CI. Muon dong the nay phai
pre-reg rieng va co nhieu hon 21 leg.


---

## BUGS phat hien 2026-09-05 — sua = baseline MOI, can user quyet  [BLOCKED]

B1. `mergeOrder()` (`SimulatorMarketLevelTicker1MStopLoss.java:730-777`) KHONG chep `symbolPred`
    => `trailRate()` fallback `pnp=1f` => 100% lenh nhanh WEAK (cap 0.03). Nhanh STRONG (cap 0.08)
    CHUA BAO GIO chay. `SIM_TS_MAX_GAP` + `SIM_TS_PNOPUMP_WEAK_THR` la key chet. (W1 bd20e42)
B2. Sizing chia tong trong so DCA HAI LAN: `TradeUtils.managerBudget:62` /total va
    `DcaUtils.gridLegWeightRatio:53` /total nua => margin ~ w[i]/total^2. Voi weights 1,0,0,0
    total=1 nen vo hinh; bat DCA la sap size 169x. (T2b 16836eb)
B3. `balanceBasic` = hang so 35000 => size KHONG compound theo equity. `getBudget()`/
    `BASE_BUDGET=700` la tham so chet. Fitness hien tai khong phan anh he compound. (T2b)
Sua B1 hoac B3 se doi C2b (khong con byte-identical 60390) => phai pre-reg nhu baseline moi
va do lai toan bo. Khong tu quyet.

## T2b [DONE 16836eb] — ket qua dang chu y nhat hom nay
`full_c2b` (big_down + DCA bu size, selector C2b): 64,809 / CAGR 28.05% / maxDD -11.5 / UW 81d
vs `c2b_min` 60,390 / 24.48% / -13.1 / 93d. Trong nhieu N=4 (4.3pp) nhung PASS het rang buoc cung.
Selector C2b THANG selector cu trong luong day du (2/6 rate ngoai CI; cu FAIL 4/4 rang buoc).
DCA va big_down TU THAN khong phan biet duoc voi c2b_min (0/6 rate). Khong de cu baseline moi.
