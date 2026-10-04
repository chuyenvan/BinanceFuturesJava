# DISK_INVENTORY_20261004 — kiểm kê đĩa Oracle (đọc-only, KHÔNG xoá gì)

Máy: Oracle 161.118.212.3, `/dev/sda1` 194G, đã dùng 188G, còn 6,2G (97%). Đo 2026-10-04 ~19:20 (UTC+7). Đơn vị GB = GiB (MiB/1024).
`/home/ubuntu` = 180G; ngoài home 8G (`/usr` 3,2G, `/var` 3,9G gồm docker 1,4G + snapd 0,9G + journal 0,49G, `/tmp` 0,34G, `/opt` 0,34G).
Top home: aerospike-data 56G · claude_master 27G · java 21G · claudedata 14G · tickexport 13,6G · simbundle_x1_t170 5,2G (hardlink) · wfo_ds_x1_2021 4,3G.
Phương pháp: `du`/`find -links` (đếm hardlink đúng: nhiều cặp `ds_sim_X`/`map_X` là CÙNG inode, xoá một nửa không giải phóng gì), `lsof +D` (0 tiến trình mở file ở mọi đường dẫn đề xuất xoá), `kaggle datasets list/status`, grep repo (docs/result, docs/prereg, research/analysis).
Tiến trình đang sống đáng chú ý: java shadow_c3 (3,9G RSS), aerospike `asd` (docker `aerospike-wfo`, 2,9G), openclaw gateway, cron `collect_derivs.py` mỗi 5', cron `shadow_c3/bin/health.sh` mỗi giờ. Không có `oracle_heavy.lock`.

## 1. XOÁ-AN-TOÀN (tổng 30,8 GB)
Điều kiện (a) tái sinh bằng script/Kaggle, (b) vòng tạo ra đã có RESULT commit, (c) không file nào đang mở.

| Đường dẫn | GB | Ngày | Nguồn / vòng | Bằng chứng + lý do |
|---|---:|---|---|---|
| `claude_master/1003/sa/bins/{R1,R2,R3,R13,R42,R7,L}` | 6,43 | 10-03 | SELECTOR_ABLATION (RESULT `33d8fc17`, prereg `5f357d3f`) | 7 × 941M bins `predict_wf_*.bin`, links=1. Tái sinh: `research/analysis/selector_ablation_scores.py gen --arm <R42/R7/R13/L/R1..>` (RNG seed 42/7/13, sha đối chiếu `sa/bins/sha256.json` GIỮ lại); kernel Kaggle tự gọi lại `gen_arm` (RESULT: "bins sha Kaggle == Oracle"). R1/R2/R3 chỉ là pilot seed không vào verdict. GIỮ `sa/bins/P0` (941M, bins gốc sha 407e2aba; `label_firsthit_sim.py:36` copy từ đây). |
| `claude_master/1003/sa50/bins/{R50s42,R50s7,R100s42,R100s7}` | 3,67 | 10-03 | SELECTOR_ABLATION_R50 (RESULT `b7fedef4`, prereg `e7fe24bd`) | 4 × 941M, links=1. Tái sinh: `selector_ablation_topm.py` (+ driver `selector_ablation_r50_driver.py`); sha trong `sa50/bins/sha256.json` GIỮ. |
| `claude_master/1003/fh/{ds_sim_CTRL,ds_sim_FH,map_CTRL,map_FH}` | 1,73 | 10-03 | LABEL_FIRSTHIT (RESULT `c6bb9c75`, KHÔNG GO) | 2 cặp hardlink (ds_sim_X = map_X, đã kiểm inode), mỗi cặp 888M. Bản Kaggle: dataset `chuyendinh/fh-sim-bins-ctrl`, `fh-sim-bins-fh` (status ready). Tái sinh: `label_firsthit_sim.py`. |
| `claude_master/1003/fh/{out_CTRL,out_FH}` | 1,73 | 10-03 | LABEL_FIRSTHIT | 2 × 888M, links=1; output kernel Kaggle `chuyendinh/label-firsthit-g015-gpu` (tải lại bằng `kaggle kernels output`). Trước khi xoá copy `net_train_summary.json` (xem khối lệnh). GIỮ `fh/labels`, `fh/fh_all.parquet` (input của `s1_fhrank_prep.py:17`), `fh/ds`, `fh/moc21`. |
| `claude_master/1003/fhr/{ds_sim_FH*,map_FH*}` (FHL42, FHL7, FHP42, FHP7) | 3,47 | 10-03 | S1_FIRSTHIT_RANK (RESULT `06818fa6`, NO-GO) | 4 cặp hardlink × 888M. Bản Kaggle: `chuyendinh/fhr-bins-fhl42/fhl7/fhp42/fhp7` (ready). Tái sinh: `s1_fhrank_sim.py`. GIỮ `fhr/pred`, `fhr/kout`, `fhr/kds`. |
| `sm_pwsoft/sm/PW_t15_E10_S{13,42,7}` | 2,60 | 10-01 | SHORT_PATHEXIT_PSOFT (RESULT_SHORT_PATHEXIT_PSOFT.md, NO-GO) | 3 × 888M links=1. Output kernel Kaggle `chuyendinh/sm-pw` (sinh bởi `research/kaggle/short_model/make_sm_pw_kernels.py`, ~1h55 GPU). Log `sm-pw.log` + `smcode/` GIỮ. Chỉ driver của chính vòng này đọc `BINS=/home/ubuntu/sm_pwsoft`. |
| `tickexport/up_zip/ticker_{2022,2023,2024,2025}.zip` + `tickexport/up5/2021/ticker_2021.zip` + `tickexport/up5/2022/ticker_2022.zip` (hardlink của up_zip) | 10,03 | 08-22 | export tick staging để upload Kaggle (D1_DATA_AUDIT dòng 361-391) | Kaggle có `chuyendinh/wfo-ticker-2021, -2022, -2023, -2024h1/h2, -2025h1/h2` (list -m, sim dùng đúng các dataset này). Nguồn gốc xuất lại từ Aerospike `test.kline_1m_opt` bằng job tickexport. 0 file mở. LƯU Ý: sau khi xoá, bản Kaggle là bản duy nhất; không xác nhận được md5 Kaggle==local (chỉ khớp kích thước ~). |
| `java/cpcv.jar`, `java/cpcv_trailing_20260829.jar` | 0,19 | 08-25/29 | CPCV (Aug) | Kaggle `chuyendinh/cpcv-jar`, `cpcv-jar-trailing` (94M); 0 tham chiếu trong research/tools/docs result+prereg. |
| `/tmp/closes_by_sym.npy` | 0,08 | 09-17 | cache tự tạo, > 7 ngày | file tạm; tái sinh từ `CLOSES_1H*.bin`. |
| journal (`sudo journalctl --vacuum-size=100M`) | 0,38 | — | systemd | 489M -> 100M. |
| apt cache (`sudo apt-get clean`) | 0,17 | — | apt | 178M. |
| snap bản disabled: core18 3002, core20 2870, core22 2438, lxd 40574, snapd 27740 | 0,33 | 05-03..09-07 | snapd | `snap list --all` đánh dấu disabled; bản mới hơn đang chạy. |

## 2. CHƯA-RÕ (owner quyết; tổng ~19,2 GB)

| Đường dẫn | GB | Ngày | Là gì / bằng chứng | Vì sao chưa chắc |
|---|---:|---|---|---|
| `sm_pathexit/sm` (+ OLD/PA hardlink trong `sm_pwsoft/sm`) | 2,60 | 10-01 | bins SHORT_PATHEXIT (NO-GO), kernel Kaggle | `PA_t15_E10_S42` còn là input của SHORT_GATECLOSED (NO-GO 10-03, `97e5daec`). Cả mạch SHORT đã NO-GO 4 vòng; nếu owner đóng hẳn hướng SHORT thì xoá được. |
| `tickexport/up2026/ticker_2026.tar` | 3,12 | 08-21 | tick 2026 (niêm phong) | Kaggle `wfo-ticker-2026pf` (2GB) là bản cắt `up26pf` tới 2026-08-13, khác tar; D1_DATA_AUDIT ghi "cần md5sum". |
| `java/simulator/features_oi_percoin_v1/oi_percoin_20210101_to_20260701.bin.gz` | 3,0 | 08-05 | OI per-coin dạng nén | Trùng nội dung `claudedata/oi/oi_percoin_full.bin` (4,2G, cấm) + Kaggle `funding-oi-percoin` (3GB); nhưng là nguồn feature OI cho vòng gate sắp tới, config Java có thể trỏ vào. |
| `simbundle` (phần unique) | 1,9 | 09-05 | bundle sim cũ (funding.bin 1,8G, market.bin, pred.bin, prof_*) | Bị thay bởi `sim-x1-2021-bundle` (Kaggle) / `simbundle_x1_t170`; 11 file docs còn nhắc; predict_wf trong đó là hardlink (không giải phóng). |
| `f0_repro` | 1,9 | 09-29 | bins tái dựng g015x26 + CLOSES_1H.bin | Bằng chứng A1 của S1_RETRAIN_NOISE (bins khác deploy md5 0160dcec vs a71cb93c); `label_firsthit_score.py` còn đọc. |
| `envs/` (1,2G) ~ trùng `xgb-env` (1,1G) | 1,2 | 06-22 | venv xgboost trùng thư viện | 15 file repo nhắc `envs/xgb-env`; cần kiểm script nào còn dùng trước khi bỏ một bản. |
| `lab_ctl` | 0,90 | 08-13 | `funding_label_*.pb` bản ctl | 0 tham chiếu repo; Kaggle `funding-label-15m` (864M) có nhưng chưa xác nhận trùng. |
| `kaggle_bdchain` + `bdchain_pf000` | 0,84 | 10-01 | vòng BDCHAIN (market f000..f100, gate_store_patched.csv.gz 340M) | Kaggle có `bdchain-market-f*`, `bdchain-gate-store`; chưa tra RESULT. |
| `java/devrun/` (373 thư mục log sim cũ) | 0,59 | 09-02..09-22 | log/ket qua Java sim DEV cũ | không tái sinh trên Oracle (cấm Java sim); đã tóm trong docs? chưa đối chiếu từng cái. |
| `val_pred_net015`, `sel_models_net015` | 1,2 | 08-13/14 | model/pred selector net015 (Aug) | refs repo 1 và 4; chưa tra vòng kết luận. |
| `java/{fs,fs_oracle,fs_win_backup}.jar`, `java/simulator/gatecount*.jar.bak`, `exbuild/shaded_*.jar` | 0,66 | 08-06..09-02 | jar backup | md5 3 jar fs khác nhau; không có bản Kaggle tương ứng. |
| `src_wt_{nowrite,c3live2,geom}`, `wt_crashpen` | 0,71 | 09-29..10-04 | git worktree các vòng đã merge/NO-GO | dùng `git worktree remove` thay vì rm; `c3live2` sửa ngày 10-04. |
| docker image `aerospike/aerospike-server:5.7.0.17` | 0,28 | — | image không container nào dùng | container đang chạy dùng `:latest`; chỉ xoá nếu chắc không cần quay lại 5.7. |
| `kaggle_sim/jar_gdv2_ref` | 0,09 | 09 | jar trùng md5 với `jar_gdv2` (32bb0225) | trùng, nhưng prof .properties riêng; nằm trong cây kaggle_sim. |
| `shadow_c3/app.bak_20261002_1743`, `app.bak_20261003_225901` | 0,19 | 10-02/03 | rollback app shadow | < 7 ngày + gắn với 242/shadow: KHÔNG đụng tới khi chưa tới 10-10. |

## 3. GIỮ / CẤM (chỉ ghi kích thước)
aerospike-data 56G (test.dat 47,4G dùng/90G file, ticker.dat 8,5G/15G) · claudedata 14G · wfo_ds_x1_2021 4,3G · ledger 2,2G · ds_feat15m 1,7G + ds_feat15m_r24 1,2G · ds_label15m 1,9G · s1hpo 0,9G · java/simulator/kaggle_data_hpo 15G · java/fsrun 0,6G · derivs_store 0,2G · shadow_c3 1,8G · kaggle_sim/out 1,0G (+ jar_*: 4 × 96M) · claude_master/1003/s1rn 3,8G · claude_master/1004/{gsb 0,3G, gabl 0,27G, s1k24 0,46G} · predwf_* ~9,3G tổng (t1_f4/t1_f4q/t1_f72/map_s1a2/G015_v2/c4_maxfav30 6 × 386M; s1a2_x1/c4_parity/c4_regen 3 × 888M; s1a2_x1_2021/oi12_2021 2 × 941M; s1a2_x1_5m 2,6G; nhiều file là hardlink).
Không có lợi khi xoá (hardlink toàn phần): `simbundle_x1_t170` (5,2G, unique 0 — chung inode với `wfo_ds_x1_2021` và predwf), `kbak` (0,39G, links=3).
Đang dùng: `kaggle_latest_venv` (1,0G, CLI kaggle), `.npm-global` 0,75G + `.openclaw` 0,46G (openclaw gateway đang chạy), `.m2` 0,13G, `.local` 1,4G (site-packages xgboost/nvidia), `.cache` 0,17G, `~/src/BinanceFuturesJava` 0,36G.

## 4. Dữ liệu cho gate feature (đọc-only; không scan Aerospike)
Ràng buộc nhắc lại: DEV <= 2025-12-31, 2026 niêm phong. Mọi nguồn "live" bên dưới từ 2026-09-12 nằm trọn trong vùng niêm phong nên KHÔNG dùng cho DEV.

| Dữ liệu | Nguồn | Độ phân giải | Phạm vi | Symbol | Định dạng / kích thước | Ghi chú |
|---|---|---|---|---|---|---|
| OI (open interest) lịch sử | Aerospike `test.open_interest` (19.987 obj, 1,94G) và `ticker.open_interest` (18.501 obj, 1,81G) | suy ra 5' (blob tháng ~90-107KB/coin ≈ 8.640 điểm x ~12B; CHƯA xác nhận bằng đọc record) | 2021-01 .. ~2026-08 (2021: 1 coin/tháng 01-11, từ 12/2021 137 coin) | ~130-290 coin theo tháng | key `SYMBOL_YYYYMM`, 1 record = blob tháng/coin | `oi_percoin_full.bin` (claudedata/oi, 4,23G, sha e3887f63) là bản dẫn xuất, đã dùng bởi `feat_v2_build.py:93`; bản nén 3,2G ở `java/simulator/features_oi_percoin_v1`. Bin names không liệt kê được (`asinfo -v bins/<ns>` trả "unrecognized" ở asd 8.1.2.3); đọc qua loader Java/Python hiện có. |
| Taker buy/sell volume | Aerospike `test.oi_taker_vol` (19.297 obj, 1,99G), `ticker.oi_taker_vol` (17.811, 1,84G) | như OI (khoá tháng) | như OI | như OI | như OI | đã từng đo `taker_buy` trong RESULT_LS_TAKER (NO-GO, 09-24) và REAUDIT_S1_FEATURE_ROUNDS (CHẾT trên S1); chưa dùng cho GATE. |
| Long/short ratio | Aerospike `oi_ls_global_acc` (19.818), `oi_ls_toptrader_acc` (18.591), `oi_ls_toptrader_pos` (18.610) | như OI | như OI | như OI | như OI | live mới hơn: derivs_store (dưới). |
| Giá/volume phút | Aerospike `test.kline_1m_opt` (2.952.455 obj, 25,3G), `kline_15m_opt` (189k, 1,05G) | 1' / 15' | 2021 .. 2025-12 (+2026) | toàn universe | blob theo ngày/coin | nguồn của 33 feature gate (GATE_INVENTORY_20261004); phút vol=0 sau khi coin chết (xem DATA_AUDIT). |
| Funding lịch sử | Aerospike `test.funding_data` (831 obj, 22MB); `claudedata/funding_lf.bin` 0,45G; `simbundle*/funding.bin` | theo kỳ funding | 2021-01 .. 2026-08-05 12:00 (funding_data) | ~84 coin @2021-01 -> 132 @2021-12 -> nay | blob/coin-tháng | `funding_data` phủ dư 2021-01..11 (D1_DATA_AUDIT A.4). |
| OI realtime | `~/derivs_store/<YYYYMMDD>/oi.csv.gz` (`cycle_ts,cycle_iso,symbol,openInterest,time`) | 5' (cron */5, `collect_derivs.py`) | 2026-09-12 .. nay (23 ngày, tích luỹ) | 528 (universe PERPETUAL USDT TRADING; 152.065 dòng/ngày = 288 x 528) | CSV gz ~2,1MB/file/ngày, cả kho 199MB | chỉ 2026 => niêm phong. |
| Funding realtime + mark/index | `derivs_store/<ngày>/funding.csv.gz` (`markPrice,indexPrice,lastFundingRate,nextFundingTime`) | 5' | như trên | 528 | CSV gz ~2,4MB/ngày | premium/basis tính được = (markPrice - indexPrice)/indexPrice; KHÔNG có chuỗi premiumIndex riêng, KHÔNG có lịch sử trước 2026-09-12. |
| LSR realtime | `derivs_store/<ngày>/lsr_global.csv.gz`, `lsr_top.csv.gz` | 5' | như trên | 528 | CSV gz ~2,06MB/ngày mỗi file | |
| Liquidation | `collector/liq_ws.py` (WS `!forceOrder@arr`) + `run_liq.sh` | sự kiện | — | — | **0 dòng**: không có `liquidations.csv` trong derivs_store; chỉ có `liq_ws.log` (reconnect/watchdog, 09-12..10-01) | tiến trình còn chạy (1 PID) nhưng chưa ghi được dữ liệu; KHÔNG có liquidation nào dùng được. Cần điều tra riêng nếu gate cần. |
| Premium index / basis lịch sử | không có | — | — | — | — | không thấy set/file nào; chỉ mark/index live từ 2026-09-12. |
| Close/OHLCV 1h | `java/fsrun/CLOSES_1H_v2.bin` (140MB) + `_mask.bin`, `OHLCV_1H_v2.bin` (300MB, manifest json) | 1h | tới 2025-12 DEV (+2026) | universe v2 (`symbol_lineage_v2.csv`) | bin nhị phân | chỉ giá; không chứa OI/taker. |

Kết luận ngắn cho vòng gate sau: OI + taker + LSR có lịch sử dài (2021 -> 2026-08) chỉ trong Aerospike (dạng blob tháng, cần loader), derivs_store chỉ có 23 ngày 2026 (niêm phong); basis/liquidation không có lịch sử. Độ phân giải 5' của Aerospike OI là suy luận từ kích thước blob, cần 1 lần đọc 1 record để chốt trước khi pre-reg.

## 5. Lệnh xoá (owner chạy; tổng 30,8 GB giải phóng; sau đó còn trống ~37G)
Khối A — XOÁ-AN-TOÀN (đã kiểm: 0 file đang mở; cặp hardlink nằm trọn trong danh sách):
```bash
set -e
K=/home/ubuntu/claude_master/1003; mkdir -p $K/_keep_json
for d in $K/fh/out_CTRL $K/fh/out_FH /home/ubuntu/sm_pwsoft/sm/PW_t15_E10_S13 /home/ubuntu/sm_pwsoft/sm/PW_t15_E10_S42 /home/ubuntu/sm_pwsoft/sm/PW_t15_E10_S7; do cp -n $d/net_train_summary.json $K/_keep_json/$(basename $(dirname $d))_$(basename $d)_net_train_summary.json || true; done
cd $K
rm -rf sa/bins/R1 sa/bins/R2 sa/bins/R3 sa/bins/R13 sa/bins/R42 sa/bins/R7 sa/bins/L                 # 6,43G (giữ sa/bins/P0 + sha256.json)
rm -rf sa50/bins/R50s42 sa50/bins/R50s7 sa50/bins/R100s42 sa50/bins/R100s7                          # 3,67G
rm -rf fh/ds_sim_CTRL fh/ds_sim_FH fh/map_CTRL fh/map_FH fh/out_CTRL fh/out_FH                       # 3,47G
rm -rf fhr/ds_sim_FHL42 fhr/ds_sim_FHL7 fhr/ds_sim_FHP42 fhr/ds_sim_FHP7 fhr/map_FHL42 fhr/map_FHL7 fhr/map_FHP42 fhr/map_FHP7   # 3,47G
rm -rf /home/ubuntu/sm_pwsoft/sm/PW_t15_E10_S13 /home/ubuntu/sm_pwsoft/sm/PW_t15_E10_S42 /home/ubuntu/sm_pwsoft/sm/PW_t15_E10_S7  # 2,60G
rm -f /home/ubuntu/tickexport/up_zip/ticker_2022.zip /home/ubuntu/tickexport/up_zip/ticker_2023.zip /home/ubuntu/tickexport/up_zip/ticker_2024.zip /home/ubuntu/tickexport/up_zip/ticker_2025.zip /home/ubuntu/tickexport/up5/2021/ticker_2021.zip /home/ubuntu/tickexport/up5/2022/ticker_2022.zip   # 10,03G
rm -f /home/ubuntu/java/cpcv.jar /home/ubuntu/java/cpcv_trailing_20260829.jar /tmp/closes_by_sym.npy   # 0,27G
sudo journalctl --vacuum-size=100M; sudo apt-get clean
sudo snap remove core18 --revision=3002; sudo snap remove core20 --revision=2870; sudo snap remove core22 --revision=2438; sudo snap remove lxd --revision=40574; sudo snap remove snapd --revision=27740
df -h /home/ubuntu
```
Khối B — CHƯA-RÕ (KHÔNG chạy cả khối; chọn từng dòng, owner quyết):
```bash
# rm -rf /home/ubuntu/sm_pathexit/sm /home/ubuntu/sm_pwsoft/sm/OLD_ndown_S42 /home/ubuntu/sm_pwsoft/sm/PA_t15_E10_S42   # 2,60G (hướng SHORT đóng hẳn)
# rm -f  /home/ubuntu/tickexport/up2026/ticker_2026.tar                                                              # 3,12G (sau khi chốt md5 vs wfo-ticker-2026pf)
# rm -f  /home/ubuntu/java/simulator/features_oi_percoin_v1/oi_percoin_20210101_to_20260701.bin.gz                   # 3,0G (sau vòng gate OI)
# rm -rf /home/ubuntu/simbundle /home/ubuntu/f0_repro /home/ubuntu/lab_ctl /home/ubuntu/val_pred_net015 /home/ubuntu/sel_models_net015   # ~6,5G
# rm -rf /home/ubuntu/kaggle_bdchain /home/ubuntu/bdchain_pf000 /home/ubuntu/java/devrun                              # ~1,4G
# sudo docker rmi aerospike/aerospike-server:5.7.0.17                                                                 # 0,28G
```
