# PHA 1 — BẢNG QUYẾT ĐỊNH (worksheet cho STEP 1.2)

> Sinh bởi STEP 1.1 (Claude đọc code, decision-neutral). Cột "GIÁ TRỊ HIỆN TẠI" chỉ để bạn THẤY
> đang có gì + cái nào đã nhiễm; **KHÔNG phải khuyến nghị**. Cột "QUYẾT (1.2)" bạn tự điền trên DEV.
> ⚠️ = đã nhiễm (range/giá trị rút ra từ nhìn kết quả) hoặc CHƯA chốt → phải quyết lại có ý thức.
> Điền xong bảng này → chép sang Phụ lục A của DATA_GOVERNANCE_PROTOCOL.md → hash → đóng băng.


> **CAP NHAT 2026-09-03** (`docs/LEAK_L1_REPORT.md` + `docs/CI_REAUDIT.md`): cot "QUYET (1.2)"
> da duoc dien cho nhung o ma cac bao cao hien co DA tra loi. Quy uoc:
> **CHOT DE-FACTO** = code that dang chay dung gia tri nay, da xac minh bang file:line (khong
> phai ai chon co y thuc - chi la ghi lai su that); **DINH CHINH** = cot "Gia tri HIEN TAI"
> ghi sai so voi code; **CHUA QUYET** = kem theo cai dang chan. Moi o can **danh doi gia tri**
> (A2f, C9, C12, B7) deu de CHUA QUYET - Claude khong tu quyet thay chu du an.
> Hai o **A2c** va **A2e** da duoc DONG (khac han nhan cu), va co **muc moi A2f**.

## A. TẦNG SELECTOR (thượng nguồn — pred là feature của sim)

| ID | Quyết định | Giá trị HIỆN TẠI | Nguồn | QUYẾT (1.2) |
|----|-----------|------------------|-------|-------------|
| A1 | Feature set | 45 feat = f0..f39 (Tool1 export Java; biết: f20 fundingRateTrend, f24 fundingSum24h, f26 volumeZCoin, còn lại opaque) + 5 OI (oi_delta24h, oi_z, ls_global, ls_toptrader, taker_buy). ⚠️ đã từng feature-select (featsel_gate15m.py) | tool1_col.py, train_funding_selector_wfo.py:FEAT | **CHUA QUYET.** Xac nhan bang code: dung la 45 feat = f0..f39 + 5 OI (LEAK_L1_REPORT bang 'Tham so THAT'). Cai dang chan: **tinh nhan qua cua f0..f39 KHONG TIM THAY BANG CHUNG** - day la lo hong leak DUY NHAT con mo (LEAK_L1_REPORT muc 'CON LAI CHUA DONG' #1). Khong duoc coi A1 la sach cho den khi doc duoc noi tinh 40 feature Tool1 |
| A2a | Label — kiểu | 2-sided triple-barrier: y=1 nếu chạm TP trước SL trong horizon | train_..._wfo.py:load_labels | **DINH CHINH:** model deployed **KHONG** dung 2-sided triple-barrier. Nhan that la **1 CHIEU** `maxFav_4h >= 0.06` (LEAK_L1_REPORT muc 4.1). => o nay het nghia; xem **A2f** |
| A2b | Label — TP (fav) | **0.06** (SEL_FAV_PCT) | idem | **CHOT DE-FACTO = 0.06**, hardcode `gen_funding_wf_predictions_1m.py:37` (`WIN = 0.06`), dang co hieu luc that. Chua ai chon co y thuc => phai quyet **cung A2f** (doi 0.06 = train lai 16 fold) |
| A2c | Label - SL (adv) | ~~**0.03** "SL placeholder, user chot sau"~~ => **0.03 VO HIEU LUC**: model G015 deployed **khong dung stop-loss nao**, `maxAdv` khong bao gio duoc doc. `SEL_ADV_PCT=0.03` chi ton tai trong 2 script **chua tung sinh bins dang chay** (`ml/training/gen_funding_wf_predictions.py:38`, `ml/funding_selector/train_funding_selector_wfo.py:38`) | LEAK_L1_REPORT muc 4.1-4.2 | **HET HIEU LUC - khong con gi phai chot o o nay.** Muc THAT can chot la **A2f** (duoi) |
| A2d | Label — horizon | train cả {4h,12h,24h,72h}; strategy DÙNG 4h (WFO_SEL_HORIZON_IDX=0) ⚠️ chọn 4h là 1 quyết định | runbook D2 | **CHOT DE-FACTO = 4h** (`H_BASE_MIN['4h']=240` / GRID 15 = 16 buoc), xac nhan bang code. **CHUA QUYET neu muon doi**: chua tung so 4h vs 12/24/72h o tang STRATEGY, chi so o tang offline |
| A2e | Label - lay mau | grid 15 phut (SELECTOR_GRID_MIN=15). ~~OVERLAP voi horizon>15m = L1 leak~~ => **OVERLAP cua so nhan = TUONG QUAN CHUOI, KHONG PHAI L1 LEAK**: purge that = 72h wall-clock, horizon dung = 4h => **du ra 68.25h o 16/16 vong**, con `assert tr.ts.max() < cutoff` chay that moi fold | LEAK_L1_REPORT muc Cau 2 b1-b3 | **KHONG PHAI LEAK - dong nghi van leak. Giu grid 15m.** He qua duy nhat: overlap lam **CI hep gia** - n hieu dung = **302 khoi 72h**, khong phai 15.44M dong; diem uoc luong KHONG lech (spearman mau khong chong lap 0.1718 vs moc 0.1675). Da do lai o `docs/PREREG_CI.md` + `docs/CI_REAUDIT.md` |
| A2f | **Label - chieu va co che exit** (MUC MOI, chua tung duoc ghi) | Nhan G015 deployed la **1 CHIEU**: `y = (maxFav_4h >= 0.06)`, **KHONG co stop-loss**. Nhan chi hoi "gia co tung cham +6% trong 4h", bo qua hoan toan viec truoc do co sut -X% hay khong => **LECH khoi cach strategy that exit** (arm 7% -> giveback min(50%, cap 8%) -> ratchet, `SIM_TS_GIVEBACK=1`, loser-time-stop 168h) | `gen_funding_wf_predictions_1m.py:37,293,304,310`; LEAK_L1_REPORT muc 4.3 | **CHUA QUYET.** Cai dang chan: doi sang nhan 2 chieu => train lai G015 16 fold => doi phan phoi P(win) => doi `dyn_thr` => **moi so DEV/VAL cua C2b phai chay lai** (LEAK_L1_REPORT muc 4.4). Day la danh doi GIA TRI - chu du an quyet, khong phai Claude |
| A3a | Selector model + hp | XGBoost n_est=400, depth=5, lr=0.05, subsample=0.8, colsample=0.8, min_child_weight=20, scale_pos_weight=(1-pos)/pos, seed=42 | train_..._wfo.py:run | **CHOT DE-FACTO** - xac nhan tung tham so bang code (`gen_..._1m.py:384-388`). Do ben theo seed da PASS (A7: seed 1/7 cho b:58483 / 59406 vs 59471) |
| A3b | Selector — purge | H_STEPS×15m wall-clock (4h→16 bước; 72h→288) | idem | **DINH CHINH:** purge deployed la **PURGE_STEPS=288 x 15m = 72h CO DINH**, KHONG phai H_STEPS x 15m (`gen_..._1m.py:53`, kernel dong 27). Voi horizon 4h => du ra 68.25h o 16/16 vong => **DU**. Coi nhu CHOT |
| A3c | Selector — Optuna? | có biến thể Optuna riêng (optuna_trials.json) ⚠️ nếu dùng, mọi Optuna-trial phải đếm vào n_trials | ml/training, train_market_xgboost_optuna.py | **CHUA QUYET.** Khong tim thay bang chung Optuna duoc dung cho G015 deployed (kernel exec `gen_..._1m.py`, khong co Optuna trong duong day). Neu ve sau dung thi moi trial phai dem vao n_trials |
| A4 | Universe + survivorship | CoinRank tier (WFO_STATIC_RANK + ExportCoinTierStatic), survivorship_bac0.py. ⚠️ cần xác định: symbol nào, tier tĩnh/động, xử lý delist | WfoWorker, survivorship_bac0.py | **CHUA QUYET.** Cai dang chan: universe **phinh 155 -> 265 -> 563 coin/gio** tu DEV sang 2025Q4, coin unique 171 -> 591 (AUDIT_APPLIED F2); khong tham so nao trong `profiles/c2b.properties` phan anh dieu do. Y tuong top-K theo ti le universe **chua tung kiem** (B9). Xu ly delist chua xac dinh |

## B. TẦNG STRATEGY

| ID | Quyết định | Giá trị HIỆN TẠI | Nguồn | QUYẾT (1.2) |
|----|-----------|------------------|-------|-------------|
| B5 | Gate | AIRejectFilter = predReturn15M ≥ MIN_MOMENTUM_15M (worker 0.008); risk4h ĐÃ BỎ (leaky); market-level | runbook §4 | **CHOT DE-FACTO va DA GHI VAO PROFILE**: `dyn_thr = MIN_MOMENTUM_15M x clamp(score/RATE_MAX x 1.28760, 0.26787, 2.14135)`; median score G015 0.47-0.70 => **luon clamp** => nguong hang **1.713%** (`profiles/c2b.properties:15-16`). **CANH BAO MOI** (`docs/CI_REAUDIT.md` #9): gate MO top8 vs gate DONG top8 = +0.0238, CI95 [-0.0053, +0.0442] => **gia tri gia tang cua GATE chua chung minh duoc**; gia tri cua XEP HANG thi DA chung minh (#8 SONG: +0.0182, CI [+0.0085, +0.0227]) |
| B6 | Selector rank-K | top-K = 8 (SELECTOR_RANK_TOPK) | runbook D5 | **MOT PHAN, CHUA DONG.** `profiles/c2b.properties:12` = **8**; live chay **5** (runbook_live_242 muc 12). A8 do: K=8 nhieu equity hon, K=5 maxDD/Sharpe tot hon. Venh sim<->live phai dong bang 1 quyet dinh + 1 vong parity |
| B7 | 17 gene + range | **TẤT CẢ range ⚠️ đã sweep-thu-hẹp** (comment "sweep cho thấy...", "TASK-139"). Phải vẽ lại RỘNG theo lý thuyết. Danh sách 17 gene: xem StrategyWfoTask.GENOME | StrategyWfoTask.java | **CHUA QUYET.** Cai dang chan: **GS wave-1 dang chay** (256 diem Sobol 15 chieu, `docs/PREREG_GS.md`) - phai doc theo dung luat muc 4 cua no. **CANH BAO MOI** (`docs/CI_REAUDIT.md` HE QUA (iii) he qua 2): voi sd(hieu CAGR) = 2.57pp cho thay doi tham so exit, **ky vong GIA TRI LON NHAT cua 256 phep thu THUAN NHIEU la +8.6pp CAGR** => khong duoc xep hang finalist bang CAGR DEV |
| B8 | Cost model | SIM_APPLY_FUNDING=true, breaker OFF, CAPITAL_START=35000. ⚠️ fee/slippage cần xác nhận giá trị | runbook D5, Configs | **CHOT DE-FACTO**: SIM_APPLY_FUNDING=true, SIM_BREAKER_MODE=OFF (co che breaker DA BI XOA o `5f40a90`), CAPITAL_START=35000, SIM_FUNDING_MARK=true. Stress da PASS: 1.5x/2x (D2, CAGR 18.51-19.19) va 2.3x (D3, 15.54). **CON THIEU**: gia tri fee/slippage BASE chua xac nhan tu `Configs.java` (o CHUA DOC muc 2 duoi) |

## C. TẦNG ĐÁNH GIÁ

| ID | Quyết định | Giá trị HIỆN TẠI | Nguồn | QUYẾT (1.2) |
|----|-----------|------------------|-------|-------------|
| C9 | Objective O | median(Calmar_net) − 0.5·std(Calmar_net) qua fold ⚠️ std 2 chiều phạt cả fold tốt bất thường | StrategyWfoTask.aggregate | **CHUA QUYET.** Doi objective = **pre-register v2** (danh doi: mat kha nang so voi moi ket qua truoc do). Day la quyet dinh GIA TRI - khong tu quyet thay chu du an |
| C10 | Ngưỡng pass | PBO<0.2 · DSR>0.95 · %fold+≥0.80 (PASS_POS_RATIO_V1) · maxDD-cap (SURVIVAL_MAX_DD_PCT) | preregistration_frame_v1 | **CHOT DE-FACTO** theo `preregistration_frame_v1`. **CANH BAO MOI** (`docs/CI_REAUDIT.md`): moi tieu chi tinh tren SO DONG (DSR / PBO) dang dung **n gia** - n hieu dung tren DEV la **302 khoi 72h**, khong phai 15.44M dong => nguong DSR>0.95 phai duoc tinh lai truoc khi dung lai |
| C11 | CPCV setup | N=8 block, k=2, 28 path, gap=purge+embargo=max(horizon,MAX_HOLD) | cpcv_harness.py | **CHUA QUYET.** DINH CHINH bat buoc truoc khi dung lai: don vi block cua CPCV phai la **khoi 72h** (cua so nhan `g1lite`), khong duoc gia dinh dong doc lap (`docs/LEAK_L1_REPORT.md` Cau 2a). Ngoai ra: `MAX_CONCURRENT` da duoc chung minh la **nut tro** (C13, VOID) nen khong duoc suy `MAX_HOLD` trong cong thuc gap tu no |
| C12 | Budget n_trials + stopping | ⚠️ CHƯA định — bắt buộc chốt trước Pha 2 | — | **CHUA QUYET** - van la muc bat buoc chot truoc Pha 2. **CANH BAO MOI** (`docs/CI_REAUDIT.md`): n_trials phai duoc chot **cung voi** nguong hieu toi thieu, vi `E[max cua N phep thu nhieu] ~ sd x sqrt(2 ln N)` = +7.2pp (N=50) / +8.6pp (N=256) / +9.6pp (N=1000) voi sd 2.57pp. Chon N ma khong chot nguong = tu bao dam se tim ra 'cai thien' gia |

## Tổng kết cái CHƯA/ĐÃ-NHIỄM phải quyết lại có ý thức (đừng để trôi)
1. ~~**A2c label SL** - chua tung chot (placeholder 0.03).~~ => **DONG: 0.03 VO HIEU LUC** - G015 deployed khong dung stop-loss nao (`LEAK_L1_REPORT` muc 4). Thay bang **A2f MOI**: nhan 1-chieu `maxFav_4h >= 0.06` khong SL, **lech khoi cach strategy that exit** - **CHUA QUYET**, doi = train lai 16 fold + chay lai moi so DEV/VAL cua C2b.
2. ~~**A2e lay mau grid 15m** - overlap = L1 leak; can nhac nonoverlap.~~ => **DONG: KHONG PHAI L1 LEAK** - purge that 72h vs horizon nhan 4h, du ra 68.25h o **16/16 vong** (`LEAK_L1_REPORT` Cau 2 b3). **Giu grid 15m.** He qua duy nhat la **CI hep gia**: n hieu dung = 302 khoi 72h, khong phai 15.44M dong => da do lai o `docs/PREREG_CI.md` + `docs/CI_REAUDIT.md`.
3. **B7 range 17 gene** — toàn bộ đã sweep hẹp; vẽ lại rộng.
4. **A3c Optuna selector** — nếu dùng, trial phải đếm vào n_trials.
5. **A4 survivorship** — chưa xác định rõ universe.
6. **C12 budget/stopping** — chưa có.
7. **C9 objective** — cân nhắc downside-std thay std 2 chiều (nhưng đổi = pre-register v2).

## Ô CHƯA ĐỌC (nếu 1.2 cần, Claude đọc tiếp — vẫn decision-neutral)
- Tên đầy đủ f0..f39: Tool1ColSink.java (bên exporter Java).
- Giá trị fee/slippage chính xác: Configs.java.
- Bộ dựng maxFav/maxAdv (nguồn LABEL_CSV): ml/lib/funding_label_pb.py.
