# PREREG_PARITY_V12_DRY — ADDENDUM 21 (CHỐT 2026-11-14, MASTER duyệt sau A1_FIN_PAIR_V2 PASS-WITH-MINOR): đo lại G-MICRO (ii) + smoke cho cặp jar FIN-A (2026-11-14, TRƯỚC deploy)

**Trạng thái:** CHỐT bởi MASTER 2026-11-14 TRƯỚC deploy cặp vòng 2 (A1_FIN_PAIR.md + A1_FIN_PAIR_V2.md: PASS-WITH-MINOR, 0 FAIL).
Nguồn: nháp vòng 2 do agent DEV soạn (sau A1_FIN_PAIR, sửa M1–M9); MASTER thêm §3.5 (lệch dây chuyền) và đổi sha8 token.
Token Telegram đã rotate 11-14 (owner revoke token cũ sha8 4f49bded): sha8 kỳ vọng mới = `bdee1480` ở mọi chỗ của addendum này.
Mọi con số dưới đây chốt TRƯỚC khi có dữ liệu trên cặp jar mới; không đổi sau khi thấy số.

## 0. Lý do
- Lỗ hổng "live quyết định trên nến chưa chốt": `KLINE-CHOT-THIEU` 11-10 21:03 (397/752 có nến final lúc chốt), 11-13 10:55
  (535/752). Guard đếm (ADD14) chỉ đếm symbol CÓ dữ liệu nên không bắt; p15 lệch tới 1,56 %, `LIVE-KLINE decided_on_unsettled`.
- **11-06 (đã tra log collectData 242, M9c):** dòng `[KLINE-CHOT-THIEU] phut=20261106 21:28 thieu_luc_chot=752 ws_mat=752` lúc
  21:29:10 là **ARTEFACT KHỞI ĐỘNG** (deploy QF4b, JVM mới start 21:29:09). JVM CŨ đã chốt phút 21:28 lúc 21:29:04.006 với
  `ws_final=752/752` ⇒ v_t_m đọc ở +6 s thấy nến final; KHÔNG phải sự cố dữ liệu ⇒ không đưa vào replay, không tính là sự cố.
  Hệ quả cho FIN-A: lần restart ingestor fin sau này, phút đầu của JVM mới ghi `fin` qua `MinuteFin.merge` (không gỡ symbol khi
  không có nến mới) ⇒ fin do JVM cũ ghi được GIỮ. Riêng lần deploy QF4b → fin: phút đầu JVM mới có fin = {} (JVM cũ không ghi fin)
  — vô hại vì lúc đó v_t_m vẫn là r4u3 (deploy ingestor TRƯỚC).
- Sửa theo phương án A (quyết định MASTER 11-12: bắt buộc trước PILOT; 11-14 owner duyệt xử lý ngay): ingestor ghi bin `fin`,
  guard live đếm theo `fin`. Sim dùng Vision (luôn final) ⇒ fix chỉ kéo live về gần sim, KHÔNG đổi logic chiến lược.

## 1. Cặp jar đích (thay đích ADD19 errata r4u3; thay cặp vòng 1 c38e476c / 39d998fa — cặp vòng 1 KHÔNG deploy)
| Thành phần | Nhánh / commit code | md5 jar |
|---|---|---|
| collectData (ingestor) | `qf/fin-bin` 1e8f26e4 (ops 2845d2c7) | `5e78ac0663b4a765551eac1c362bf194` |
| v_t_m (r4u3fin, file `jar_v12_r4u3fin2`) | `v1.2/fin-guard` 5e10325b (ops 2375c0e1) | `641803565297d4065d90245e04a00f11` |
- Thứ tự deploy: **ingestor trước**, v_t_m sau (`deploy_chain.sh fin_pair`, owner chạy 1 lệnh `owner_deploy_fin_pair.sh`
  với `EXPECT_SHA8=bdee1480 TG_SHA8=bdee1480`). Jar r4u3 cũ chỉ đọc bin `data` ⇒ chạy an toàn với ingestor mới.
- Trước chain: token Telegram vào env (owner script tự chạy `set_telegram_env_242.sh` nếu chưa có; sha8 `bdee1480`); MASTER đặt
  `parity_v12w/gmicro_target.json` = `{target_jar: "r4u3fin", target_md5: "641803565297d4065d90245e04a00f11", smoke_start_ms: null}`
  (ĐÃ ĐẶT 11-14, backup `gmicro_target.json.bak_r4u3_*`).

## 2. Hành vi mới ở live (cố định trước)
- Phút ĐỦ theo guard đếm (ADD14, không đổi) ⇒ đọc NGUYÊN TỬ record phút (bin `data` + `fin`), merge vào cache.
  U = symbol có nến phút đó trong cache, thuộc universe A1, bỏ `diedSymbol`. Phút ĐÃ CHỐT ⇔ |fin ∩ U| ≥ ceil(99 % × |U|)
  (cùng ngưỡng 99 % của guard đếm).
- Thiếu ⇒ đọc lại mỗi 2 s tới **giây +45** sau khi phút đóng; đủ ⇒ `[MINUTE-FIN-WAIT] … tre_sau_dong=<ms> … => DU sau khi cho`.
- Vẫn thiếu ⇒ fail-closed như MI: `[MINUTE-INCOMPLETE] phut=… fin=a/U … ly_do=FIN_THIEU => KHONG mo lenh moi …`.
- Record không có bin `fin` ⇒ `ly_do=FIN_KHONG_BIN` (ingestor cũ): fail-closed; ERROR 1 lần/60′. Rollback tạm: `LIVE_FIN_GUARD=0`
  (code + script nhận cờ tắt `0/false/no/off`, không phân biệt hoa thường).
- **MỚI vòng 2 (M2, quyết định MASTER): fail-closed THEO COIN.** Phút ĐÃ CHỐT nhưng còn ≤ 1 % U chưa có trong `fin` ⇒ các coin đó
  KHÔNG được vào lệnh / DCA ở phút đó (mọi leg: selector, BIG_DOWN, DCA level/big-loss, DCA grid; sổ giấy + thật). Coin vẫn nằm trong
  tính market level / feature / p15. Selector: coin vẫn được đếm hạng + qua gate (nạp r p15 như sim, giống LEGACY) rồi mới bị chặn;
  KHÔNG lấy coin hạng K+1 thay. Log: `[MINUTE-FIN-EXCL] phut=… loai=n universe=U fin=a ds=…` (1 dòng/phút khi n ≥ 1) và
  `[MINUTE-FIN-EXCL] chan leg <LEVEL> <SYM> …` (mỗi leg bị chặn). ĐÂY LÀ THAY ĐỔI TẬP ĐỦ ĐIỀU KIỆN Ở LIVE ⇒ ghi nhận ở đây.
- **M1 (ingestor):** repair khởi động + `TickerGapRepairTool` ghi qua `writeFinal`: nến REST chưa settle (đóng < 20 s) ⇒ GỠ khỏi fin;
  đã settle ⇒ vào fin. Không còn writer nào ghi đè bin `data` mà không cập nhật `fin` (trừ bản nến phút đang mở — không thuộc fin).
- Thước LIVE-KLINE: khi guard fin thay nến của phút quyết định, ảnh chụp quyết định được chụp lại (xem §3.4).

## 3. Cách tính trong parity
1. Phút `ly_do=FIN_THIEU` / `FIN_KHONG_BIN` = **phút MI** theo ADD14 §2 (loại khỏi K5, đếm `mi_minutes`, báo cáo). Báo cáo tách thêm
   `mi_fin_thieu`, `mi_fin_khong_bin`, `fin_wait_recovered` (số dòng `[MINUTE-FIN-WAIT]`).
2. **(M3 + M9d)** Phút `[MINUTE-FIN-WAIT]` (thiếu rồi đủ trong hạn) **không** loại, tính K5 như thường, NHƯNG báo cáo THÊM một dòng
   K5 RIÊNG chỉ trên các phút này (`k5_fin_wait`, n phút) + phân bố độ trễ quyết định `tre_sau_dong` (min / p50 / max, ms) đọc từ dòng
   log. Phút thường quyết định ~+6 s; phút chờ tới ≤ +45 s ⇒ giá vào có thể lệch sim — chỉ báo, không đổi kết luận K5 tổng.
3. **(M2)** Leg bị chặn theo coin (`[MINUTE-FIN-EXCL] chan leg`) = lệch CÓ NGUYÊN NHÂN (attributed): báo riêng `fin_excl_legs`
   (số leg, danh sách sym/phút), KHÔNG tính TRƯỢT; entry sim tương ứng ghi `ly_do=fin_excl`. Phút có leg bị chặn vẫn tính K5 cho phần
   còn lại.
4. **(M9a) Thước LIVE-KLINE ĐỔI ĐỊNH NGHĨA tại swap r4u3 → r4u3fin ⇒ GÃY CHUỖI:** trên r4u3fin ảnh chụp quyết định được chụp LẠI sau
   khi guard fin merge bản chốt (`LiveTickerWindow.readFinal` → `audit.onDecisionRead` khi overwritten > 0) ⇒ `decided_on_unsettled`
   của r4u3fin KHÔNG so được với chuỗi r4u3; báo cáo tách 2 đoạn, ngày swap XÁM. Phút `FIN_THIEU`/`FIN_KHONG_BIN` (không quyết định)
   loại khỏi mẫu số `decided_on_unsettled` và báo riêng. Sai số dư đã biết: `tickerWindow.read` sau guard (đọc lại KFIX-B) có thể merge
   dữ liệu mới hơn mà không chụp lại ⇒ ảnh chụp có thể cũ hơn dữ liệu thật dùng một chút; ghi rõ, không sửa trong vòng này.
5. **(MASTER, theo A1 V2) Lệch dây chuyền do M2:** từ phút có leg bị chặn (`fin_excl`), mọi khác biệt live↔sim về vị thế / DCA / exit /
   budget-slot truy được về leg đó ghi `fin_excl_cascade` (attributed, kèm sym + phút gốc), KHÔNG tính TRƯỢT. Ngày có ≥ 1 leg
   `fin_excl` hoặc cascade còn mở ⇒ nhãn tối đa SẠCH-T (vẫn tính cho (i)/(ii) như SẠCH-T). Cascade còn mở > 3 ngày, hoặc khác biệt
   không truy được về leg gốc ⇒ báo MASTER; MASTER quyết re-seed (harness không tự re-seed).
6. Không đổi K1–K6, tie_split, ngưỡng nào khác.

## 4. (ii) và smoke — ĐO LẠI cho cặp jar vòng 2
- (ii) cần ≥ 1 ngày SẠCH hoặc SẠCH-T chạy trọn trên **cả cặp vòng 2** (ingestor `5e78ac0663b4a765551eac1c362bf194` + v_t_m
  `641803565297d4065d90245e04a00f11`). Ngày swap của bất kỳ jar nào trong cặp = XÁM, không tính. Ngày trên cặp vòng 1 (nếu lỡ có)
  KHÔNG tính cho (ii).
- Điều kiện FIN thêm cho ngày (ii): 0 `ly_do=FIN_KHONG_BIN`; 0 `[KLINE-FIN] loi ghi` (collectData); `FIN_THIEU` được phép nhưng ghi số.
- Smoke ≥ 24 h từ `SMOKE_START` (giờ start thật r4u3fin vòng 2, chain ghi vào `gmicro_target.json`):
  - **v_t_m** (`v_t_m/logs/full.log` từ SMOKE_START): 0 dòng mức `ERROR`, 0 `LATCH`, 0 `KHAN`, 0 `FIN_KHONG_BIN`,
    0 `[TELEGRAM] thieu env`; có `[MINUTE-FIN] BAT`.
  - **collectData** (`collectData/logs/full.log` từ start JVM fin): 0 `[KLINE-FIN] loi ghi`, 0 `[TELEGRAM] thieu env`; có
    `[KLINE-FIN] bin fin BAT`. Dòng `ERROR` khác của collectData KHÔNG là điều kiện smoke (chỉ ghi số) — M9e.
  - Cả 2 process: env `TELEGRAM_BOT_TOKEN` sha8 = `bdee1480` (đo bằng sha256 qua /proc/PID/environ, không in token).
- md5 trong `jars.json` của jar đích khác `641803565297d4065d90245e04a00f11` ⇒ (ii) = false, có ghi chú (như ADD19).

## 5. (i)
- Giữ ADD11 §3 / ADD19 §2: ngày SẠCH/SẠCH-T trên r4u3 vẫn tính; ngày trên r4u3fin vòng 2 tính bình thường; ngày swap XÁM.

## 6. Kỳ vọng ghi trước (kiểm sai) — M9b: chốt số
- "Ngày thường" = ngày collectData KHÔNG có dòng `[KLINE-CHOT-THIEU]` (trừ phút đầu sau restart JVM ingestor). Trên ngày thường:
  - `FIN_THIEU` = **0**.
  - `[MINUTE-FIN-WAIT]` **≤ 3 phút/ngày** (thay "≈ 0").
  - `[MINUTE-FIN-EXCL] phut=` **≤ 10 phút/ngày** và tổng coin bị loại **≤ 20 coin-phút/ngày**; `chan leg` **≤ 2 leg/ngày**.
  - Vượt BẤT KỲ ngưỡng nào ⇒ báo MASTER (nghi ingestor không ghi fin cho REST settle / WS final về muộn hệ thống / ngưỡng quá chặt),
    KHÔNG tự nới ngưỡng, KHÔNG tự đổi hạn +45 s.
- Lần `KLINE-CHOT-THIEU` kế tiếp: phút đó phải là `[MINUTE-FIN-WAIT] DU sau khi cho` (nến final về +4…+30 s < +45 s) hoặc
  `FIN_THIEU` fail-closed; `decided_on_unsettled` của phút đó ≤ 1 % |U| VÀ mọi coin chưa chốt lúc quyết định phải nằm trong
  `[MINUTE-FIN-EXCL] ds=` (0 leg vào coin chưa chốt). Phút guard fin cho qua mà `decided_on_unsettled` > 1 % |U|, hoặc có leg vào
  coin ngoài fin ⇒ coi là BUG ⇒ rollback v_t_m về r4u3, báo MASTER.
- Chi phí: phút đủ ngay = 1 lần đọc record thêm (~21 KB), không ngủ.

## 7. Rollback
- v_t_m về r4u3 (an toàn với cả 2 ingestor): lệnh in trong log chain và cuối `owner_deploy_fin_pair.sh`
  (`OLD_TAG=r4u3fin NEW_TAG=r4u3 OLD_MD5=641803565297d4065d90245e04a00f11 … NEED_FIN=0 swap_v12_dry_jar.sh`).
- Ingestor về QF4b: `rollback_ingest_fin.sh <TS>` — script **TỪ CHỐI** (M4) khi v_t_m còn chạy jar fin-guard (md5 39d998fa/641803…
  hoặc jar có class `MinuteFin`) với guard BẬT; chỉ chạy sau khi v_t_m đã về r4u3 (hoặc `LIVE_FIN_GUARD=0`); ép: `FORCE=1`.
- Token: jar cũ (QF4b, r4u3, r4t…) có token cũ hard-code ĐÃ REVOKE 11-14 ⇒ rollback về jar cũ = Java MẤT Telegram (Oracle health242 +
  watchdog 242 vẫn báo). Env file vô hại với jar cũ.
