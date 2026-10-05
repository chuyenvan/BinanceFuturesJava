HOÃN — shadow #2 dùng cho K24+skipFull (owner 10-05), GEOM xét sau. Xem docs/runbooks/SHADOW2_K24_SKIPFULL_PLAN.md.

# SHADOW2_GEOM_PLAN — kế hoạch shadow #2 (S1 + GEOM) chạy song song shadow #1 (S1 KEEP9)

- **Ngày:** 2026-10-03. **Trạng thái:** KẾ HOẠCH — **owner duyệt 2026-10-03**. Chưa tạo thư mục/service nào, chưa deploy. Không chạm 242.
- **Nguồn:** `docs/audit/GEOM_LIVE_IMPL_20261003.md` (branch `feat/geom-live`, từ `origin/module` cf5c90e4) §9–§10; chấm A/B theo `RESULT_S1_FEAT_GEOM.md`.
- **Bản chất:** `RESULT_S1_FEAT_GEOM` = **NO-GO** theo pre-reg (dCAGR +2,46 pp, CI [−0,20; +5,09] < +3,3 pp). Shadow #2 là **quan sát A/B**, KHÔNG phải bước promote. Theo `RISK_APPETITE` §9-AMENDMENT A-20261003 (A.5): B1 = S1+GEOM là ứng viên chưa chứng minh; baseline nghiên cứu vẫn là S1 KEEP9.
- **GEOM live làm gì:** thay model S1 (9→18 input) + thêm 9 cột GEOM (`pos24, pos7d, dist_high24, dist_low24, atr_ratio, range7d, rk_pos24, rk_dist_low24, rk_atr_ratio`). `LiveBuildMap`/net015 KHÔNG đổi. Cờ `LIVE_S1_GEOM_ENABLED` (unset = OFF = hành vi cf5c90e4, đã chứng minh byte-identical class, xem GEOM_LIVE_IMPL §7).

## 1. Điều kiện TIÊN QUYẾT (tất cả phải xong TRƯỚC khi bật #2)

| # | điều kiện | tiêu chí xong | ghi chú |
|---|---|---|---|
| (i) | **Mốc 2026-10-07 17:15 của shadow #1**: bật gate rolling (`LIVE_GATE_ROLLING_*`) + jar `jar_nowrite` f282581a + `LIVE_IS_SHADOW_HOST=true` | #1 chạy ổn sau mốc; `[GATE-RATIO]` có log; B7/B8 của `PARITY_LIVE_VS_SIM_CHECKLIST` đo lại | #2 chỉ bật SAU mốc để hai shadow cùng cấu hình gate. GEOM_LIVE_IMPL ghi 17:01 (giờ arm 242), checklist ghi 17:15 — **lấy 17:15, tức muộn hơn** |
| (ii) | **Sim DEV 1 kernel cho model live `s1geom_g42_cut20251231`** | có kết quả sim DEV của đúng model live (train CPU, 6 911 775 dòng tới 2025-12-27 16:30) | model live ≠ model đã sim (retrain CPU vs GPU G42: spearman 0,991, top-16 overlap TB **0,90**, min 0,625) và cut20251231 CHƯA có sim DEV riêng. Không bật nếu chưa có — nếu không có, mọi A/B sau này không quy được về vòng GEOM đã NO-GO |
| (iii) | **Shadow #1 chuyển sang CÙNG jar với GEOM OFF** | #1 chạy jar `binance-java-sdk-1.2.4.jar` sha256 `c1f6838baf63225eebbf70ac681a3d595eac764a11351a7536a36ae6a3e674ea`, `LIVE_S1_GEOM_ENABLED` unset | A/B sạch: khác biệt duy nhất #1/#2 = cờ GEOM + model. Hiện #1 chạy jar build 10-02 (≠ cf5c90e4) ⇒ nếu không đổi, A/B bị nhiễu jar. Có thể gộp vào lần restart mốc 10-07 |
| (iv) | **`SIM_F_BASE` theo kết quả Q1** (sizing leg đầu, xem `PARITY_LIVE_VS_SIM_20261003` E2) | nếu fix `LIVE_APPLY_GRID_RATIO` ĐÃ merge: `SIM_F_BASE=0.015` + `LIVE_APPLY_GRID_RATIO=true`. Nếu CHƯA merge: `SIM_F_BASE=0.09` (= 0.015 × `DCA_GRID_SCALE` 6.0, bù đường paper không nhân grid ratio) | #1 và #2 PHẢI cùng giá trị; nếu #1 đổi thì #2 đổi theo. Checker `parity_check.py` coi 0.09 là lệch giải thích được |
| (v) | **Thước so A/B hàng tuần** chốt trước (mục 3) | bảng mục 3 được ghi vào pre-reg/nhật ký trước ngày bật | không đổi thước sau khi thấy số |
| (vi) | **Rủi ro mục 4 đã đọc** và kiểm được: `totalUsdt` ghi trên 242, warm-up WAN, giờ thủng | probe `totalUsdt` ≠ 0 trên 242 (chỉ đọc); đo warm-up WAN | xem mục 4 |

## 2. Các bước dựng (theo GEOM_LIVE_IMPL §9; chỉ làm sau khi (i)–(vi) xong)

1. `~/shadow_c3b/app` = bản sao CẤU HÌNH của `~/shadow_c3/app`: `bin/`, `conf/env.sh`, `config.properties`, `logback.xml`, `redis.config`. **KHÔNG** copy `logs/ feat_dump/ run/ storage/ ledger` (sổ/vị thế riêng, bắt đầu rỗng).
2. Jar `~/claude_master/1003/geom_live/jar/binance-java-sdk-1.2.4.jar` (sha `c1f6838b…`) → `app/target/`. Model: copy `s1geom_g42_cut20251231.onnx` (sha256 `7166583b…a5066`) → `/home/ubuntu/s1_model/`, đối chiếu sha với manifest.
3. `conf/env.sh` = env của #1 tại thời điểm copy, **thêm**: `LIVE_S1_GEOM_ENABLED=true`, `S1_GEOM_MODEL_ONNX=/home/ubuntu/s1_model/s1geom_g42_cut20251231.onnx`; **giữ** `SHADOW_NO_PUSH=true`, `LIVE_IS_SHADOW_HOST=true`, `LIVE_WRITE_242_ENABLED` unset/false (KHÔNG ghi 242), `JAVA_TOOL_OPTIONS=-Xms3g -Xmx3g`; `SIM_F_BASE` theo (iv). Lưu ý `LIVE_S1_GEOM_ENABLED` có tiền tố `LIVE_` ⇒ nếu dùng `TRADING_PROFILE` phải khai trong profile.
4. Redis/cổng RIÊNG: `shadow-c3b-redis.service` (cổng khác, sửa `redis.config`); `ss -ltn` kiểm cổng app không trùng #1. Aerospike: chỉ ĐỌC 242 (S1/OI/GEOM).
5. Service `shadow-c3b` = clone `shadow-c3.service`, `WorkingDirectory=/home/ubuntu/shadow_c3b/app`, `Requires=shadow-c3b-redis.service`, journald.
6. **RAM:** Oracle 23 G; #1 RSS ~3,9 G + asd ~3 G + node ~1 G ⇒ thường trực ~6–8 G; #2 thêm ~4 G ⇒ ~11–12 G. Job research nặng hạ trần (ulimit) ≤ 8 G khi #2 chạy, để còn ≥ 2 G đệm.
7. **Kiểm ngày đầu:** log `[S1-GEOM] BAT` (model `[?,18]`); `[GEOM] warm-up … ms` (WAN); `grep -c "ERROR.*S1-GEOM"` = 0 sau warm-up; số symbol có GEOM/giờ ≈ số coin `[S1] score`.

## 3. Thước so A/B hàng tuần (cùng thước cho #1 và #2)

Tuần T2 00:00 → CN 23:59 GMT+7, **chỉ lệnh MỞ trong tuần**.

| chỉ số | nguồn | ghi chú |
|---|---|---|
| n lệnh vào | ledger mỗi shadow | |
| PnL giấy (% vốn, gộp + TB/lệnh) | ledger | cùng `PAPER_EQUITY` |
| SL% (tỷ lệ thoát bằng SL) | ledger | tham chiếu sim: GEOM 13,41 % vs CTRL 13,83 % |
| top-16 overlap #1 vs #2 mỗi tick | `sel_dump` / `LATEST_SEL_RANK` | tham chiếu sim: G vs ORIG 0,80 |
| tick bị bỏ do GEOM chưa sẵn | log `ERROR [S1-GEOM]` | phải ≈ 0 ngoài warm-up |

**Giới hạn đọc:** 1 tuần ≈ vài chục lệnh, không đủ lực thống kê. **Không kết luận promote** trước khi có pre-reg riêng; theo `RISK_APPETITE` A.3, sự kiện cụm báo theo ngày, không coi lệnh độc lập. #1 và #2 chia sẻ cùng thị trường nên so ghép cặp theo tick/ngày, không so như hai mẫu độc lập.

## 4. Rủi ro (đọc trước khi bật)

1. **`totalUsdt` trên 242 chưa kiểm:** `GeomFeatProvider` bỏ bar giờ có `Σ totalUsdt == 0` (`REQUIRE_VOLUME`). Parity chỉ làm trên bản sao Oracle `test`. Nếu 242 ghi `totalUsdt = 0` ở mọi bản ghi ⇒ không có bar ⇒ #2 **bỏ MỌI tick** (fail-safe, lộ qua `ERROR [S1-GEOM]`, không lệch âm thầm). Probe chỉ-đọc trước khi bật.
2. **Warm-up qua WAN:** ~10 200 bản ghi phút (~87 MB) **chặn** `scoreAll` (synchronized) lần đầu; local 2,4–4 s, **WAN chưa đo**. Thường trực 60 bản ghi/giờ + đọc lại giờ chưa chốt (~0,5–1,5 MB/giờ). Đo ở lần bật đầu; nếu chặn lâu, #2 bỏ tick giai đoạn đầu (không ảnh hưởng #1).
3. **Giờ thủng dữ liệu:** symbol không có key KEEP9 offline (18 cột NaN khi train) nhận GEOM một phần ở live (0,06 % dòng ứng viên trong 7 ngày parity); `REQUIRE_VOLUME` xấp xỉ lineage (giờ qv=0 trong vùng sống ≈ 0,08 % store). Nhỏ nhưng làm A/B lệch không-thuần-GEOM.
4. **Model live ≠ model đã sim** (điều kiện (ii)); ONNX↔XGB sai số 1,3–2,9e-6 (> 1e-6 tuyệt đối, cùng cỡ model KEEP9 đang chạy; top-16 345/345 trùng).
5. **Rank GEOM trên toàn thị trường** (đúng offline) khác quy ước rank KEEP9 live (trong universe selector) — có sẵn, không đụng.
6. `LIVE_FEAT_DUMP`/`sel_dump` KHÔNG ghi 9 cột GEOM ⇒ chưa có vết audit feature cho #2 (thêm sau nếu cần).
7. **Tài nguyên:** RAM (mục 2.6); `oracle_heavy.lock` mồ côi (GEOM_LIVE_IMPL §10.9) — kiểm trước khi chạy job nặng.
8. **Rủi ro diễn giải:** thấy #2 hơn #1 vài tuần ≠ GEOM tốt (nhiễu, lực yếu, vòng sim đã NO-GO). Không đổi cấu hình 242 dựa trên shadow #2.

## 5. Artifact tham chiếu

`~/claude_master/1003/geom_live/` (`jar/`, `model/` + manifest, `parity/`, `cls_diff.txt`, `mvn_test_full.log`). Parity offline↔live-replay: max|Δ| = 0,0 cả 9 cột (88 940 dòng); top-16 341/345 trùng tuyệt đối (345/345 sau khi lọc 106 dòng giờ thủng).
