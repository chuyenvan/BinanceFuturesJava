# HANDOFF 2026-07-20 — PHÁT HIỆN LỚN: SELECTOR BỊ DÙNG NGƯỢC DẤU CHO LONG

## TL;DR (đọc cái này trước)
Selector KHÔNG vô dụng — nó **rất mạnh nhưng train sai mục tiêu**. Label = `P(maxFav_H >= 6%)` = **P(coin PUMP lên ≥6%)**, chỉ nhìn upside, bỏ qua downside/đuôi. Gate long hiện MUA coin điểm cao nhất = coin dễ pump nhất → pump xong DUMP → với chiến lược long-giữ-không-SL = maxDD khổng lồ (đúng ghi chú gốc "chọn coin pump → đuôi lớn maxdd"). **Đảo lựa chọn (mua coin ÍT pump nhất) biến quý cháy thành quý lời.**

## BẰNG CHỨNG ĐO ĐƯỢC (probe in-sample, best-N vs worst-N cùng số N cùng gate)
| Quý | mức | BEST-N (model chọn) | WORST-N (đảo) |
|---|---|---|---|
| 2024Q1 | 0.5% | +341 (DD8.4%) | +748 (DD1.3%) |
| 2025Q2 | 0.5% | -6898 (DD27.6%, CHAY) | +832 (DD2.7%, SUCCESS) |
| 2025Q2 | 1.0% | -1553 (CHAY) | +242 (calmar 1.6) |
| 2023Q4 | 0.5% | +491 | +46 (ngoai le: best>worst quy nay) |

Tong 3 quy (0.5%): BEST -6065 vs WORST +1626. Cu lat KHONG tuyet doi (2023Q4 nguoc), phu thuoc regime, nhung ap dao ve tong.
Caveat: probe fixed-config IN-SAMPLE per-quy — CHUA walk-forward. WFO dang chay de xac nhan OOS.

## DANG CHAY (Oracle, qua CE)
- `long_invsel` WFO (jar alphaprobe.jar, SELECTOR_INVERT=1) tren wfo_ds_oiz2022_75. Luc ghi: 14/16 DONE, 2 RUNNING, 0 FAILED — gan xong.
- DOC VERDICT: `ce wfo_report long_invsel` → pass-criteria: %OOS-duong>=70% · WFE median>=0.5 · maxDD<=50%. Hoi: dao-dau-selector co pass OOS noi long_full/softgate da FAIL khong.

## NEXT (song song sau khi long_invsel xong — thu tu dung)
Rang buoc: Oracle chi 1 WFO/luc (chung jobstore 226 + 4core/23GB). KHONG chay 2 WFO song song. Nhung retrain KHONG dung jobstore → song song that voi 1 WFO.

1. **Doc verdict long_invsel** (`ce wfo_report long_invsel`). Neu PASS → dao-dau la loi that; neu FAIL → chi la hack, di thang retrain.
2. **SHORT WFO** (dung jobstore, chay khi long_invsel nha). Dung chinh selector pump cho short (pump→dump = dung thu short can). Lenh da verify env san:
   ```
   ce wfo_fanout wfo_ds_oiz2022_75 /home/ubuntu/java/simulator/alphaprobe.jar 30 42 2 0 short_pump "ABLATION_MODE=A,WFO_DISABLE_DCA=1,ENABLE_SHORT=true,SHORT_SL_PCT=0.25,SHORT_TIME_STOP_HOURS=24,APPLY_FUNDING_FEE=true"
   ```
   (ENABLE_SHORT dao selector thanh SELL; hard-SL BAT BUOC; funding ON bat buoc cho short.)
3. **RETRAIN long (fix goc, song song voi short)** — Kaggle/CPU, khong dung jobstore. Sua label o `ml/funding_selector/train_funding_selector_wfo.py` (`load_labels`): thay label chi-upside `(maxFav>=6%)` bang label **downside-aware** (vd loai/penalize coin co maxAdv sau, hoac target = HIT +N% TRUOC khi cham -X%, giong logic short HIT path-aware). Re-export label (Java, nhanh) → train (nhanh) → predict (hoi cham) → build ds → WFO. User xac nhan retrain KHONG nang.

## CODE DA SUA SESSION NAY (CHUA COMMIT — commit thuoc quyen Uni)
Branch `module`, working tree:
- `Configs.java`: them `SELECTOR_INVERT` (env "1"=on, default false=byte-identical). (Ngay canh SELECTOR_SCORE_MAX.)
- `SimulatorMarketLevelTicker1MStopLoss.java`: khoi chon candidate (~L262) refactor: dem nPass qua nguong → BEST-N (dau mang) hoac WORST-N (cuoi mang) theo SELECTOR_INVERT. INV=false = BEST-N = byte-identical (da verify: INV=0 khop baseline tung so).
- `Mom15SweepProbe.java` (research probe): sweep={0.005,0.007,0.010}, periods=4 quy (2023Q4/2024Q1/2025Q2 zero + 2025Q4 succ).
- Jar deploy: `/home/ubuntu/java/simulator/alphaprobe.jar` (co ca SELECTOR_INVERT + ENABLE_SHORT). Build: corretto-17 target-11, chay tren java-11 Oracle OK.

## CHUOI PHAT HIEN DAN TOI KET LUAN (context)
1. `long_softgate` WFO = FAIL (%OOS 18.8%). Confidence-sizing nang return +31% cung maxDD, nhung KHONG tao frequency — 12/16 quy ZERO/TOO_FEW. Nut that = opportunity frequency, khong phai edge.
2. Gate MOM15 = bo loc REGIME toan thi truong: `wfo_gate_pred.csv` chi co (timestamp, predReturn15M, predRisk4H), KHONG co symbol → predReturn15M la 1 gia tri/phut dung chung moi coin. Median ~0.4-0.9%, nguong genome 1-2.28% → chan gan het cac phut chop → ca quy ZERO. (Genome floor MIN_MOMENTUM=0.03 o WFORunner; framework toi ~0.01 — vung <1% chua ai test.)
3. Ha gate (Mom15SweepProbe): REGIME-DEPENDENT. 2023Q4/2024Q1 co edge long o 0.5-1% (gate bo lo tien); 2025Q2 chop CHAY moi muc (-1553..-7018). Ha cung = tham hoa.
4. Margin-breaker (BREAKER_MODE=MARGIN mac dinh, halt 0.50): siet ve 0.10 cat 2025Q2 tu -6897/DD28% xuong -1721/DD6.8%, GIU nguyen loi 2023Q4; nhung CUN — bop chet upside 2024Q1 (khong phan biet margin-cao-vi-thang vs vi-thua). → guard nen theo DD thuc te, khong theo gross-margin. (Chua lam.)
5. Test selector: dao THU TU trong tap qua-nguong = giong het (budget khong bo). → PHAI test best-N vs worst-N cung N (fix da lam) → ra cu lat o muc 2 (TL;DR).

## BAI HOC HA TANG / CE (QUAN TRONG — dung lap lai loi session nay)
- DUNG CE cho moi viec Oracle. Raw ssh qua PowerShell hong lien tuc: `|` (alternation grep) bi tach → remote treo cho stdin; `\r`/`sed`/`tr` an mat ky tu (vd "mom15probe.jar"→"mom15pobe.ja"). Ghi script len Oracle = base64 (echo <b64> | base64 -d), KHONG scp file Windows (CRLF) roi sed.
- `bg_run` co RAM-guard: can req_gb + 3GB dem <= free. Dat ram_gb hop ly, 1 JVM/job.
- `bg_stop` CHI giet script (child), KHONG giet java chau → orphan JVM tich luy (co luc 5 con) → ngon RAM/CPU, lam OOM job sau + ssh cham. Sau moi stop: `pkill -9 -f <MainClass>`.
- 2 JVM 8-14g noi tiep trong 1 script hay OOM giua chung → chay 1 JVM/job rieng.
- `wfo_fanout`: (a) jar phai DUONG DAN TUYET DOI (worker cd worker_cwd, -cp tuong doi → ClassNotFound); (b) dataset phai symlink vao worker_cwd: `ln -sfn /home/ubuntu/claudedata/<ds> /home/ubuntu/claudedata/.run/oracle_worker_cwd/<ds>` (worker doc theo duong tuong doi tu worker_cwd — thieu → "Thieu manifest").
- Oracle chi java-11 (/usr/bin/java). Jar build corretto-17 nhung target Java-11-compat → chay OK.

## PASS-CRITERIA (pre-registered, Uni chot)
WFE median >= 0.5 · %OOS-duong >= 70% · maxDD-OOS xau nhat <= 50% von.

## FILE/LOG session nay (Oracle /home/ubuntu/claudedata/.run/)
bw_inv_0.log (best-N baseline), bw_inv_1.log (worst-N), mc5_inv_*.log, mom15_halt_*.log, wfo_report_long_softgate.md. Jar: /home/ubuntu/java/simulator/alphaprobe.jar.
