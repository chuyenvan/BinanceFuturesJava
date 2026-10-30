# v1.2/c3-live — Round 4k: 242 không có python3 (chỉ ops, KHÔNG đổi Java/jar)

**Phát hiện (2026-10-31, `DRY=1 FORCE=1 deploy_v12_dry_r4.sh` trên 242 thật):** PRE `FAIL thieu_python3` + `FAIL exchangeInfo_nguon … python3: command not found`.
242 là CentOS 7 (EOL), glibc 2.17, chỉ có `/usr/bin/python` 2.7.5. Deploy dry dừng ở bước kiểm (fail-closed, không đổi gì).

## Rà phụ thuộc python3 (chạy TRÊN 242)
| file:dòng (trước 4k) | dùng |
|---|---|
| `deploy_v12_dry_r4.sh:192` | PRE `command -v python3` |
| `deploy_v12_dry_r4.sh:199` | PRE chạy `exinfo_validate.py` từ nội dung (`python3 -I -c`) |
| `deploy_v12_dry_r4.sh:303` | bước chuẩn bị `python3 -I ops/exinfo_validate.py` |
| `deploy_v12_dry_r4.sh:397` → `exinfo_refresh_242.sh:48` | làm mới lần đầu (4c) + **cron** làm mới exchangeInfo mỗi ≤ 23′ |

Không phụ thuộc trên 242: `rollback_v12.sh`, `c3live_status.sh`, `killsw_reset.sh`, `ws_soak_242.sh`, watchdog/health 242.
Script canary (`ops/c3live/canary/*`) gọi python3 **trên Oracle** (dữ liệu 242 đọc qua ssh) — không đổi.

## Hướng chọn: (b) python độc lập `/opt/c3py`
- **Lý do:** cron làm mới bắt buộc chạy trên 242. (a) cần viết lại bộ kiểm JSON bằng bash/awk (giòn) hoặc thêm main Java vào jar (đổi jar ⇒ pin canary/dry/soak + A1 lại), hoặc chuyển cron sang Oracle (live phụ thuộc Oracle + ssh: Oracle chết ⇒ file cũ > 45′ ⇒ R7 STALE). (b) giữ nguyên bộ kiểm `exinfo_validate.py` (đã audit, md5 pin không đổi), chỉ đổi trình thông dịch sang đường dẫn tuyệt đối.
- **Bản pin:** python-build-standalone `20241016`, CPython **3.10.15** `x86_64-unknown-linux-gnu-install_only`, sha256 `3db2171e03c1a7acdc599fba583c1b92306d3788b375c9323077367af1e9d9de` (SHA256SUMS của release; tải lại trên Oracle khớp). `readelf`: GLIBC tối đa **2.17**, `$ORIGIN` (di chuyển được). 3.10 = cùng nhánh Oracle (3.10.12) nơi bộ kiểm + fake242 chạy.
- **`ops/c3live/c3py_install_242.sh`** (owner, trên Oracle): `DRY=1` / cài (YES) / `MODE=status` / `MODE=remove`. Tải về cache Oracle, kiểm sha256 Oracle **và** 242, giải nén vào `/opt/.c3py_new_<TS>`, kiểm python chạy đúng phiên bản + `import json`, ghi marker `C3PY_INSTALLED`, đổi tên nguyên tử ⇒ `/opt/c3py`. Không yum, không đụng python hệ thống / PATH / ld.so.conf / v_t_m / crontab. Gỡ: chỉ khi có marker; từ chối khi cron làm mới còn cài (trừ `FORCE=1`).
- **deploy:** `PY242=${PY242:-/opt/c3py/python/bin/python3}`; PRE kiểm `"$PY" ≥ 3.8` (`OK python3_rieng …` / `FAIL thieu_python3_rieng … (owner chạy c3py_install_242.sh)`); PRE + chuẩn bị + làm mới lần đầu dùng `$PY242`; dòng cron thêm `C3PY=$PY` (tuyệt đối). `EXR_MD5` pin lại.
- **exinfo_refresh_242.sh:** `PY=${C3PY:-/opt/c3py/python/bin/python3}`; thiếu python ⇒ tính 1 lần lỗi (giữ file cũ, Telegram lần 3) — hành vi cũ.

## Test (fake242 §22–27) — TEST PASS 232/232 (`~/claude_master/v12/r4l_fake.log`)
Mọi lệnh "trên 242" của deploy/cron chạy với PATH có `python3`/`python` GIẢ (`command not found`, rc 127) + python riêng giả lập `/opt/c3py`.
§27: c3py DRY/sha sai/không YES/cài/chạy lại/gỡ (cron còn ⇒ từ chối; không marker ⇒ không xoá); PRE thiếu python riêng ⇒ FAIL; có ⇒ DRY PASS; cron thiếu python ⇒ giữ file cũ, fails=1; kiểm tĩnh: deploy + cron không còn gọi `python`/`python3` theo PATH.

## Phạm vi
Chỉ ops/test/docs. **Không đổi Java, không đổi jar** (r4j `ba71eab2` giữ nguyên), không đổi `exinfo_validate.py` (`EXV_MD5` giữ nguyên).
