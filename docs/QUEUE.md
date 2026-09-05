# QUEUE — hang doi thi nghiem DEV, theo thu tu

Doc `docs/AGENT_RUNBOOK.md` truoc. Moi job phai co `docs/PREREG_*.md` commit TRUOC khi chay.
Lay job DAU TIEN co status `READY`. Job `BLOCKED` phai cho user duyet trong chat.
Sau khi xong: doi status thanh `DONE <commit>`, ghi ket qua vao doc rieng, commit.

---

## Q1 — Chot horizon time-stop  [BLOCKED: can user duyet mo lai quota]

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

## Q2 — Ban le STRONG/WEAK `TS_PNOPUMP_WEAK_THR`  [READY]

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

## Q3 — Siet momentum gate  [READY, chay sau Q2]

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
