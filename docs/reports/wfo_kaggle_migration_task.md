# TASK — Migrate WFO full-16-window sang Kaggle (config đầu: offset10)

**Tạo:** 2026-07-24 · **Mục tiêu:** chạy WFO 16-window trên Kaggle (song song, tận dụng Kaggle rảnh, Oracle chậm/treo). Config đầu = **offset10** (24h + DCA) để lấy pre-reg verdict. Deliverable = `wfo_report` verdict + so với baseline sl15.

> Nguyên tắc: mọi bước qua CE nút/pipeline (R1 ce-buttons), KHÔNG bash driver ad-hoc. Việc VERBOSE → agent `oracle-runner`. Upload lớn/job dài → `bg_run`/pipeline detached, KHÔNG poll tay.

## ✅ BLOCKER-0 — ĐÃ GIẢI bằng REBOOT (user, 2026-07-24)
Oracle reboot → 4 process treo bị clear. Còn lại: jobstore 226 có thể còn job offset10 với owner CHẾT (lease treo) → **reset-stale / fanout reset** sẽ dọn trước khi chạy mới (Step 5). Xác nhận `ce wfo_status` RUNNING=0 sau khi Oracle sống lại.

> ⛔ LUẬT MỚI (đã ghi CORE.md): **tối đa 3 job java đồng thời trên Oracle** — `wfo_fanout` oracle_workers **≤3**. Chính 4 worker gây treo lần này.

<details>
<summary>(cũ) quy trình stop nếu treo lại</summary>

4 process java offset10 treo, bão hoà Oracle → CE/SSH không phản hồi. `ce wfo_stop` đã gửi nhưng **chưa confirm**.
- PID đã spawn (chỉ kill đúng các PID này — CORE.md, KHÔNG pkill java, KHÔNG đụng 2 process live/Aerospike): controller `3801759-3801762`; owner `3801788/3801765/3801768/3801766`.
- Thứ tự: `ce wfo_stop` → nếu còn RUNNING: `ce sys_zombies kill=true` → chỉ khi fail: kill tay đúng 8 PID trên.
- **Acceptance:** `ce wfo_status` RUNNING=0 + jobstore 226 sạch (không lease treo) trước khi push bất kỳ fanout mới. Nếu SSH không vào được Oracle → **cần user tay** (restart = người, CORE.md).
- (Nếu box đơ do CPU thì upload ticker ở Step 1 KHÔNG bị chặn — 226 là box khác 103.157.218.226, không phải Oracle 161.118.212.3.)

</details>

## Hạ tầng ĐÃ có (không xây lại)
- `wfo_fanout` mặc định push tối đa 5 Kaggle kernel (6-node, cùng jobstore 226) — ce-buttons §47,§53.
- Profile `java-kaggle` verified 2026-07-14; `wfo-fanout` (merge oracle+kaggle) verified null (chờ run đầu).
- Kaggle CPU: Java 17 sẵn, 31GB/4CPU, slot ≤5, kill 12h (KAGGLE_RULES §1,§2,§3c).

## GAP cần đóng (Full scope)
### Step 1 — Ticker vào Kaggle dataset file (gỡ giới hạn 2024-04 + trần 2 worker)
- Hiện Kaggle đọc ticker từ 226 chỉ tới ~2024-04, ≤2 worker (KAGGLE_RULES §3d). Đóng ticker thành **1 TAR → dataset** (§5b) → đủ 16 window + >2 worker.
- Làm **TỪ 226** (§0b: `source ~/envs/xgb-env/bin/activate`; upload thẳng, không kéo về local). Bug CLI 1.7.4.5 → venv riêng `kaggle==1.6.17` (§5b).
- Range ticker phải phủ toàn bộ window của `oiz2022_75` (2022→2026-06 theo export ev2). Verify range trước khi TAR.
- **Acceptance:** dataset `status ready`, md5 manifest MATCH (kiểu `wfo-env-test` ENV_TEST_PASS, §3c). Kernel glob recursive `/kaggle/input/**` (§3b — KHÔNG hardcode slug).

### Step 2 — Bump jar Kaggle sang v43 sanitized
- Jar baked trên `chuyendinh/java-run-lc` là bản cũ (chưa có SELECTOR_OFFSET). Rebuild v43 → **sanitize** (PrivateConfig → placeholder, bỏ key live — CORE.md §secret) → `kaggle datasets version` (§5).
- **Acceptance:** `kaggle datasets files chuyendinh/java-run-lc` thấy jar mới + md5; KHÔNG còn secret trong jar (grep).

### Step 3 — WFO dataset oiz2022_75 trên Kaggle + re-validate fingerprint
- Kaggle mới có `wfo-dataset-wf-leakfree` — **verify** nó có phủ đúng oiz2022_75 (bin+pred 0.75+funding+manifest) hay phải upload riêng.
- **RE-VALIDATE theo fingerprint env Kaggle** (CORE.md: ValidationStamp khoá theo (md5, env) — KHÔNG tin stamp Oracle cho Kaggle).
- **Acceptance:** ValidationStamp Kaggle PASS.

### Step 4 — Kernel + test 1 (bắt buộc, §6)
- kernel-metadata: `dataset_sources=[ticker-ds, java-run-lc(v43), wfo-ds]`, `enable_internet=true`, `is_private=true`.
- Env baked = offset10: `SELECTOR_INVERT=1, SELECTOR_TOPN=3, SELECTOR_OFFSET=10, SELECTOR_SCORE_MAX=0.5, TIME_STOP_HOURS=24, WFO_DISABLE_DCA=0, WFO_MAX_WINDOWS=16, WFO_STATE_HOST=<226>` (jobstore). Copy `config.properties` vào CWD (§3b-bis). `System.exit(0)` cuối main (§4).
- **Test 1 kernel** range nhỏ → COMPLETE + DONE hợp lý + exit đúng giờ (không kéo 12h). Chỉ sau PASS mới fleet.

### Step 5 — Fanout Kaggle + monitor
- `ce kaggle_slots` (FREE=5-USED, DỪNG nếu 0). Push ≤ FREE (tối đa 5). Tag `offset10_kaggle`.
- Monitor: `ce wfo_status` + `ce kaggle_status <ref>`. 12h kill → reset-stale + repush (§2), idempotent.

### Step 6 — Report + verdict
- `ce wfo_report offset10_kaggle` → %OOS-dương, WFE median, worst maxDD, đếm SUCCESS/BURN/…
- **Acceptance pre-reg:** WFE median ≥ 0.5 & %OOS-dương ≥ 70% (không nới post-hoc). So với baseline sl15 (3/16, 7 BURN, maxDD 16.6%) + offset10 mục tiêu.

## Rủi ro / cảnh báo
- **Edge phân rã:** 2026 flat/âm, trade-weighted ~+0.5%/kèo sau phí (`docs/insights/sl4h_label_experiment.md` §11-13). Hạ tầng tái dùng được nên vẫn đáng, nhưng đừng kỳ vọng số đẹp từ chính edge offset này.
- **Secret:** sanitize jar là bước bắt buộc, review kỹ trước khi upload public-ish dataset.
- **12h kill + slot 5:** job WFO 16-window/ nhiều kernel phải idempotent + reset-stale.
- **Provenance:** đổi jar/data = bump version dataset Kaggle (profile java-kaggle note).

## HÀNG ĐỢI TEST — exit-horizon frontier cho offset10 (Bước 4 WFO)
Gate: chỉ chạy khi Oracle sống lại + jobstore 226 sạch. **oracle_workers ≤3** (CORE.md). Ưu tiên chạy trên Kaggle sau migration để song song; trước đó Oracle ≤3 worker/lần, tuần tự.

Chung: `SELECTOR_INVERT=1,SELECTOR_TOPN=3,SELECTOR_OFFSET=10,SELECTOR_SCORE_MAX=0.5,WFO_DISABLE_DCA=1` (KHÔNG set `SIM_HARD_SL_PCT` → hard-SL OFF).

| tag | TIME_STOP_HOURS | ý nghĩa |
|---|---|---|
| `off10_ndca_4h` | 4 | REF: chốt cứng 4h (khớp horizon audit) — **user yêu cầu chạy trước** |
| `off10_ndca_24h` | 24 | nuôi 24h |
| `off10_ndca_72h` | 72 | nuôi 72h |

Mục tiêu: oversold-bounce thì exit ngắn (4h) thắng hay nuôi thắng? (momentum EV2 đã biết nuôi thắng — oversold có thể ngược). So 3 tag + baseline offset10 (24h+DCA). Verdict theo ngưỡng pre-reg (WFE≥0.5, OOS+≥70%), KHÔNG nới.

## Trạng thái hiện tại
- Code offset (`SELECTOR_OFFSET`) đã ở HEAD + build vào `preflight-v43.jar` (Oracle, md5 b1aacbda...). Chưa có trên Kaggle.
- offset10 trên Oracle: treo, đang dọn (blocker-0).
- Bước kế: xác nhận Oracle sạch → Step 1 (ticker upload từ 226).
