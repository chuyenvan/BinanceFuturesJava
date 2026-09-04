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
