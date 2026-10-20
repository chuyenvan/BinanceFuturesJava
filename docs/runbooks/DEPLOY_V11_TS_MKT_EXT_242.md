# Runbook — deploy gói v1.1 = v11b + TS_MKT_EXT X14 lên 242 (OWNER tự chạy)

Spec: `docs/plan/V11_TS_MKT_EXT_LIVE.md`. Kết quả kiểm offline: `docs/result/V11_TS_MKT_EXT_OFFLINE.md`.
Agent KHÔNG chạy gì trong runbook này (không đọc/ghi 242). Chạy từ **Oracle** (`bash`).

| | |
|---|---|
| Jar mới | `/home/ubuntu/claude_master/v11_tsx/jar/binance-java-sdk-1.2.4.jar_v11c_eea5adec` — md5 **`eea5adecaff93d3fc350e4d13b3ecb2a`**, nhánh `v1.1/ts-mkt-ext` (xem hash commit trong result) trên `66cb6196` |
| Jar đang chạy 242 | v11b `d7824f6d1a622d013c4579e70c85691a` (start 10-20 20:33:04) |
| Khác jar | đúng 9 class: `ShadowBookC3` (sửa) + `AltEwIndex*`, `TsMktExt*` (mới); mọi class/resource khác trùng CRC |
| Env thêm | **1 dòng** `export LIVE_TS_MKT_EXT=1` (không tham số khác; file cache mặc định `run/ts_ext_daily.csv`) |

## ⚠ Trạng thái 10-21 05:55:29 (đọc-only lúc 05:57)
Owner đã chạy bước 2–3 và restart, nhưng **bước 1 (scp jar) chưa chạy**: trên 242 không có `target/*v11c*`, jar đang chạy vẫn là
`d7824f6d` (v11b; key `LIVE_TS_MKT_EXT` bị bỏ qua ⇒ hành vi = v11b, an toàn). Backup `*.bak_v11b_d7824f6d_20261021` và
`conf/env.sh.bak_v11b_20261021` đã đúng, env đã có đúng 1 dòng mới. ⇒ Để hoàn tất: **chỉ chạy bước 1 rồi bước 4**
(KHÔNG chạy lại bước 2: ghi đè backup vẫn là d7824f6d nhưng không cần; KHÔNG chạy lại bước 3: sẽ nhân đôi dòng env).
Khi restart lúc 05:55 thì lần tự-restart ~05:57 ngày 10-22 rơi vào khung ±3' ⇒ restart lại ở giờ đề xuất dưới sẽ đặt lại chu kỳ.

## 0. Giờ restart hợp lệ (+07)
- CẤM: 00:50–01:20, 12:50–13:20; ±3' quanh mỗi giờ (xx:57–xx:03); **06:57–07:25 và 18:57–19:25** (07:03–07:20 là lúc tính cờ ngày, 12h sau là ảnh của nó).
- Tự-restart 12h chạy theo giờ START (+~1'/lần): ~~lần kế 10-21 08:33~~ — sau restart 05:55:29, lần kế ~**10-21 17:56** ⇒ KHÔNG deploy 17:45–18:05.
  Sau deploy lúc T, các lần tự-restart rơi vào T+12h, T+24h… (lệch +1'/lần) — các khung cấm ở trên đối xứng 12h nên chỉ cần T hợp lệ.
- Đề xuất: **10-21 09:10–11:50** hoặc **14:10–17:40** (ví dụ 10:10 ⇒ tự-restart ~22:11, ~10:12 hôm sau).

## 1. Lệnh
```bash
S="ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"
SCP="scp -P 2222 -o BatchMode=yes -i /home/ubuntu/.ssh/id_rsa_chuyennd"
A=/home/chuyennd/java/v_t_m
NJ=/home/ubuntu/claude_master/v11_tsx/jar/binance-java-sdk-1.2.4.jar_v11c_eea5adec
TS=$(date +%Y%m%d_%H%M)
# 0) kiểm trước (chỉ đọc) — md5 jar chạy = d7824f6d…; LIVE_TS_MKT_EXT chưa có (0); chưa có run/ts_ext_daily.csv
md5sum $NJ
$S "cd $A && md5sum target/binance-java-sdk-1.2.4.jar; cat run/*.pid; pgrep -fa BinanceOrderTradingManager | cut -c1-100; grep -c '^export LIVE_TS_MKT_EXT' conf/env.sh; ls run/ts_ext_daily.csv 2>&1; grep -c '^export LIVE_PROFILE=c3_shadow$' conf/env.sh; grep -c '^export SHADOW_NO_PUSH=true$' conf/env.sh; date '+%F %T'"
# 1) chép jar mới cạnh jar cũ (KHÔNG ghi đè) + kiểm md5
$SCP $NJ root@103.157.218.242:$A/target/binance-java-sdk-1.2.4.jar.v11c_eea5adec
$S "cd $A && md5sum target/binance-java-sdk-1.2.4.jar.v11c_eea5adec"        # eea5adec…
# 2) backup jar d7824f6d + env (\cp -f: tránh alias cp -i)
$S "cd $A && \cp -f target/binance-java-sdk-1.2.4.jar target/binance-java-sdk-1.2.4.jar.bak_v11b_d7824f6d_$TS && \cp -f conf/env.sh conf/env.sh.bak_v11b_$TS && md5sum target/binance-java-sdk-1.2.4.jar.bak_v11b_d7824f6d_$TS"
# 3) env: thêm đúng 1 dòng; diff phải chỉ có dòng này
$S "cd $A && echo 'export LIVE_TS_MKT_EXT=1' >> conf/env.sh && grep -c '^export LIVE_TS_MKT_EXT=1$' conf/env.sh && diff conf/env.sh.bak_v11b_$TS conf/env.sh"
# 4) KIỂM GIỜ (mục 0) rồi stop → thay jar → start (dừng ~vài giây)
#    [SỬA 10-21] CHẶN: thiếu file v11c hoặc md5 sai ⇒ KHÔNG stop (10-21 05:55 owner restart mà jar vẫn d7824f6d vì bước 1 chưa chạy)
$S "cd $A && [ \"\$(md5sum < target/binance-java-sdk-1.2.4.jar.v11c_eea5adec | cut -c1-32)\" = eea5adecaff93d3fc350e4d13b3ecb2a ]" || { echo "THIEU/SAI v11c - DUNG, chay lai buoc 1"; exit 1; }
$S "cd $A && bin/daemon.sh stop && \cp -f target/binance-java-sdk-1.2.4.jar.v11c_eea5adec target/binance-java-sdk-1.2.4.jar && md5sum target/binance-java-sdk-1.2.4.jar && bin/daemon.sh start && sleep 5 && pgrep -fa BinanceOrderTradingManager | cut -c1-100; date '+%F %T'"
```
Ghi lại giờ start (dòng `date` cuối, hoặc dòng `MainClass`/start đầu tiên trong `logs/full.log`) ⇒ điền vào addendum PREREG_SHADOW2_PROMOTION (cửa sổ chính thức).

## 2. Kiểm 15 phút (chỉ đọc qua pipe — KHÔNG ghi file tạm lên 242)
```bash
# [SỬA 10-21] log 242 dạng "21/10/2026 05:55:31.018" — lọc theo dòng MainClass CUỐI (= lần start này), không theo chuỗi giờ
$S "bash -s" <<'EOF'
cd /home/chuyennd/java/v_t_m
L=logs/full.log
N=$(grep -a -n 'MainClass: com.binance.chuyennd.trading.BinanceOrderTradingManager' $L | tail -1 | cut -d: -f1)
echo "== jar (PHAI eea5adec)"; md5sum target/binance-java-sdk-1.2.4.jar; P=$(pgrep -f BinanceOrderTradingManager); ps -o pid,lstart -p $P
echo "== env"; grep -n '^export LIVE_TS_MKT_EXT\|^export LIVE_PROFILE\|^export SHADOW_NO_PUSH' conf/env.sh
echo "== TS-EXT"; tail -n +$N $L | grep -a '\[TS-EXT\]' | grep -av '\] day 20' | tail -20 | cut -c1-260
echo "== TS-EXT day lines (n_min)"; tail -n +$N $L | grep -a '\[TS-EXT\] day ' | awk '{print $(NF-1)}' | sort | uniq -c | sort -rn | head
echo "== cache"; wc -l run/ts_ext_daily.csv; tail -2 run/ts_ext_daily.csv
echo "== profile/legacy"; tail -n +$N $L | grep -a 'LIVE_PROFILE=c3_shadow\] BAT' | tail -1 | cut -c1-200
tail -n +$N $L | grep -a '\[LEGACY\] managed' | tail -1 | cut -c1-80
echo "== errors"; tail -n +$N $L | grep -a -c ' ERROR '; tail -n +$N $L | grep -a 'Exception' | tail -5 | cut -c1-200
echo "== tick"; tail -n +$N $L | grep -a 'PASS-TIMING\] selector tick total' | tail -3 | cut -c1-160
EOF
```
PASS khi đủ:
1. `[TS-EXT] BAT LIVE_TS_MKT_EXT=1 profile=c3_shadow baseH=168 extH=336 thr=-0.3 minN=1296 file=/home/chuyennd/java/v_t_m/run/ts_ext_daily.csv days_loaded=0`.
2. Trong ~5–10': 30 dòng `[TS-EXT] day 2026-09-21 … 2026-10-20 … src=aero`, mỗi dòng `n_min ≥ 1296` (thường 1440; 2026-10-01 = 1439),
   rồi **một** dòng `[TS-EXT] flag day=2026-10-21 flag=ON|OFF dd=… altEwIdx=… P=… max30=… max30Day=… minN=… src=aero:30d final=…`.
   Thị trường hiện tại: kỳ vọng `flag=OFF` (dd ≈ vài %, không phải ≤ −30 %). `flag=NA` (WARN) ⇒ thiếu ngày trong kline_1m_opt 242 ⇒ cờ = OFF (an toàn) — báo MASTER.
3. `run/ts_ext_daily.csv` = 31 dòng (header + 30).
4. `[LIVE_PROFILE=c3_shadow] BAT … SHADOW_NO_PUSH=true`; `[LEGACY] managed 44` mỗi phút như trước; `[GATE] topk=24` như v11b.
5. 0 Exception mới, ERROR không tăng bất thường; không có `[TS-EXT] loi refresh`.
6. Nếu có cụm giấy chưa arm tuổi > 168h: trong 20' đầu (PENDING) có thể thấy `[TS-EXT] defer-START <sym> age_h=… flag=PENDING`; sau dòng
   `flag … OFF` phải thấy `[TS-EXT] defer-END <sym> … reason=FLAG_OFF -> CUT time-stop` và `[SHADOW] closed <sym> reason=TIME_STOP_168H`.
   Không bao giờ có symbol LEGACY trong dòng `defer-START` (nếu có dòng `[TS-EXT] … la LEGACY` ⇒ báo MASTER).
7. Hôm sau sau 07:03 (+07): `[TS-EXT] flag day=<hôm nay> … src=aero:1d` (chỉ đọc 1 ngày mới); `[TS-EXT] status …` mỗi giờ.

## 3. Rollback (về v11b đúng d7824f6d + env cũ)
```bash
$S "cd $A && bin/daemon.sh stop && \cp -f target/binance-java-sdk-1.2.4.jar.bak_v11b_d7824f6d_$TS target/binance-java-sdk-1.2.4.jar && \cp -f conf/env.sh.bak_v11b_$TS conf/env.sh && md5sum target/binance-java-sdk-1.2.4.jar && grep -c '^export LIVE_TS_MKT_EXT' conf/env.sh; bin/daemon.sh start && sleep 5 && pgrep -fa BinanceOrderTradingManager | cut -c1-100"
```
- md5 phải = d7824f6d…, grep = 0. Cụm giấy đang được kéo dài (> 168h) sẽ bị time-stop ở nhịp đầu sau rollback (đúng hành vi v11b).
- `run/ts_ext_daily.csv` để lại vô hại (v11b không đọc). Không xoá backup.
