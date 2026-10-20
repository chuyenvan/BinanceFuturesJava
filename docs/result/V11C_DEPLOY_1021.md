# V11C_DEPLOY_1021 — kiểm sau restart owner 10-21 05:55 (chỉ đọc 242 qua ssh+pipe)

Kết luận: **gói v1.1 (v11c) CHƯA được deploy.** Owner đã restart, nhưng jar đang chạy vẫn là **v11b `d7824f6d`**. Lý do: file `target/*v11c*`
không có trên 242, tức bước 1 của runbook (scp jar) chưa chạy. Key `LIVE_TS_MKT_EXT=1` đã có trong env, nhưng v11b bỏ qua key này
⇒ hành vi hiện tại = v11b, an toàn, không cần rollback. **Cửa sổ promotion chính thức CHƯA bắt đầu.**

## 1. Xác minh (05:56–05:58 +07)
| mục | kết quả |
|---|---|
| jar chạy (`target/binance-java-sdk-1.2.4.jar`, fd của PID mở đúng file này) | md5 **d7824f6d…** (mtime 10-20 20:32:55) — **KHÔNG phải eea5adec** |
| file v11c trên 242 | **không có** (`target/*v11c*`) |
| backup | `target/…jar.bak_v11b_d7824f6d_20261021` md5 d7824f6d ✔; `conf/env.sh.bak_v11b_20261021` ✔ (05:55:09) |
| diff env | chỉ `+export LIVE_TS_MKT_EXT=1` ✔ |
| PID / start | **26221**, `ps lstart` **2026-10-21 05:55:29**; log `MainClass` 05:55:31.018; `ThreadAutoRestartProgram` 05:55:41.626 |
| env process | `LIVE_TS_MKT_EXT=1`, `LIVE_PROFILE=c3_shadow`, `SHADOW_NO_PUSH=true`, 6 key v11b; `JAVA_TOOL_OPTIONS=-Xms1g -Xmx3g -Xlog:gc:file=logs/gc.log…` ✔ (RSS 3,19G lúc 1' sau start) |
| profile | `[LIVE_PROFILE=c3_shadow] BAT … SHADOW_NO_PUSH=true (hardcode)` ✔ |
| LEGACY | `[LEGACY] managed 44` trước (05:55:10) và sau (05:57:10) ✔ |
| sổ giấy | sau start: open=4 realized=88,0877. Trước đó, lúc deploy v11b, là open=5 / 112,18. Chênh lệch giải thích được: 10-20 22:21 time-stop `SUSDT` pnl −24,09 (ledger + log) ✔ |
| gate buffer | nạp 662 040 record, armed ✔ |
| v11b | `[FEAT-PIPE] LIVE_FEAT_INPUT=snapshot … md_died=[BTCDOMUSDT, USDCUSDT]`, seed 2000' 738 symbol ✔; `[S1-DUMP]` mở file ✔; S1 warm-up đọc kline_1m_opt 242 (như v11b) |
| PASS-TIMING | tick đầu 28,8 s (warm-up, như các lần trước 22–28 s), tick kế 1,29 s ✔ |
| lỗi | 0 ERROR, 0 Exception sau start ✔ |
| `[TS-EXT]` | 0 dòng (đúng với jar v11b) |

**Giờ restart:** 05:55:29 hợp lệ (ngoài mọi khung cấm, nhưng chỉ cách khung xx:57 có 1,5'). Tự-restart 12h:
- lần 1 ~**10-21 17:56**: hợp lệ;
- lần 2 ~**10-22 05:57**: **rơi vào khung ±3'**, và các lần sau trôi sâu hơn (05:58, 17:59…).

Deploy v11c lại ở giờ đề xuất sẽ đặt lại chu kỳ này.

## 2. Checklist TS-EXT
**Không áp dụng được** vì jar v11c chưa chạy: không có `[TS-EXT] BAT`, không có dòng `day`, không có `run/ts_ext_daily.csv`.

Runbook đã sửa (`docs/runbooks/DEPLOY_V11_TS_MKT_EXT_242.md`):
- thêm mục trạng thái: chỉ cần chạy bước 1 rồi bước 4;
- thêm chốt chặn: không stop app nếu file v11c thiếu hoặc md5 sai;
- §2 lọc log theo dòng `MainClass` cuối, vì log 242 có dạng `21/10/2026 05:55:31`, không phải `2026-10-…` như lệnh cũ giả định (lệnh cũ sai).

## 3. Đối chiếu cờ — Vision (giá trị kỳ vọng cho log live khi v11c chạy)
Nguồn: Kaggle monthly cho 2026-08/09, Vision UM 1m **daily** (data.binance.vision, file tĩnh) cho 10-01..10-19. Tải 16 611 file ×200, 71 ×404
(symbol không có trong tháng). Tính bằng code live (`AltEwIndex`, jar eea5adec).
- Cờ ngày 2026-09-20 → 10-20: **0 ngày ON**. dd(EOD 10-19) = −0,1648 (cờ ngày 10-20); đỉnh 30 ngày là EOD 2026-09-19; dd đang giảm dần (10-13 −0,092 → 10-19 −0,172).
  Universe kiểu live (bỏ symbol không có ở 242) cho |Δdd| ≤ 0,0025, cờ trùng.
- **Cờ 2026-10-21 = "chưa có"**: file Vision 10-20 chưa phát hành (404 lúc 05:58 +07).
- **Store 242 vs Vision cùng ngày**, dùng record kline_1m_opt 242 đã cache từ trước trên Oracle (không đọc 242 mới):

  | ngày | S_j 242 | S_j Vision (float32, universe live) | Δ |
  |---|---|---|---|
  | 10-14 | −0,038786676 | −0,038786676 | 0 |
  | 10-15 | +0,001176837 | +0,001176837 | 1e-16 |
  | 10-16 | −0,014789719 | −0,014789719 | 0 |

  ⇒ giá 242 = Vision float32 **bit-exact** trên 3 ngày. Chênh lệch chỉ đến từ universe: thêm 140 symbol có trong Vision 10-2026 mà 242 không có,
  phần lớn không có volume; với universe Vision đầy đủ, |ΔS| 1,6e-4…6,1e-4 mỗi ngày.
- 30 dòng `[TS-EXT] day` của live: chưa có (v11c chưa chạy). Bảng trên là giá trị để so khi có.

## 5. Đề xuất parity feature định kỳ KHÔNG đọc Aerospike 242 (chưa chạy)
1. **Dữ liệu:** dựng cache phút (`TreeMap<Long, Map<String, KlineObjectSimple>>`, đúng format `cache_*.ser.gz` mà `V11FeatHarness.load` đọc)
   từ Vision UM 1m daily (phát hành D+1), ép float32, universe = danh sách symbol của live lấy qua pipe từ `s1_dump`/`feat_dump` của 242
   (738). Bằng chứng §3: giá và tập phút có qv>0 khớp bit-exact với store 242 trên 3 ngày. Sai khác còn lại:
   - (a) `totalUsdt` chưa kiểm từng giá trị (EW chỉ dùng điều kiện qv>0);
   - (b) symbol mới niêm yết sau ngày lấy danh sách;
   - (c) phút collector ghi lại sau quyết định (PARITY_1020: 2/88 phút) — Vision là dữ liệu cuối, không tái lập được "unsettled".
2. **Chặn cứng mọi đọc Aerospike trong harness:**
   - chạy với `AEROSPIKE_READ_CLUSTER=226` giả;
   - đặt trước jar trên classpath một stub `DataManagerAerospikeFloatSim` / `AerospikeClient` ném lỗi ngay khi được tạo client (fail-closed). Lần chạy đầu sẽ liệt kê đúng các chỗ đọc còn lại.
3. **Thay 3 nguồn đang đọc 242 bằng file cục bộ:**
   - `SimpleSymbolMapper`: snapshot mapper từ log/`sel_dump` hoặc map cố định theo thứ tự symbol;
   - `FundingFeeManager.getAllFundingMap`: lịch sử funding từ Vision `fundingRate` monthly + daily;
   - OI #41–45 (`oi_feat_*` 242): tính lại từ Vision `metrics` 5m daily, hoặc bỏ khỏi phạm vi parity như PARITY_1020.
   Cần sửa harness: inject 3 provider này qua flag (ví dụ `HARNESS_OFFLINE=1`).
4. **So sánh:** đọc `feat_dump`/`sel_dump`/`s1_dump` của 242 qua pipe (`ssh … zcat …`, không ghi file lên 242), so feature 33 cột/p15/rank
   theo thước của PARITY_1020. Lịch chạy: mỗi ngày D+1 sau khi Vision phát hành.

## Ghi chú
Mục 1–3 không có lệnh nào ghi file lên 242. Không chạy harness hay Java nào trỏ vào 242; không đọc Aerospike 242.
