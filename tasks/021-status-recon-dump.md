# TASK-021: Dump trạng thái THỰC (reconcile sau mất log CCD) → file cho Desktop đọc

- **status:** TODO — chạy NGAY, nhẹ. Giao CCD bất kỳ đang rảnh.
- **owner:** CCD-recon · **status:** DONE · **updated:** 2026-06-14 (output: `docs/STATUS_RECON.md`)
- **Lý do:** reset IDE mất log CCD; AGENTS + task file (013/015/019) chưa được cập nhật → Desktop KHÔNG biết các task thực sự tới đâu. CCD có shell (git/Aerospike/fs) → **dump trạng thái thực ra 1 file**, Desktop đọc & reconcile. KHÔNG đoán.

## IN
- Git repo, Aerospike (226 + 242 qua 226), thư mục `outputs/`, log live (jar đang chạy 242).

## OUT
- **MỘT file: `docs/STATUS_RECON.md`** — Desktop sẽ đọc. Mỗi mục: `[XONG / DỞ / CHƯA]` + **bằng chứng cụ thể** (commit hash / đếm record / ts range / tên file). Không kết luận chung chung.

## ⚠️ CHỈ ĐỌC — KHÔNG sửa code, KHÔNG commit, KHÔNG deploy, KHÔNG chạy backfill/builder.

## Nội dung file OUT (điền hết)
### 1. Git
- `git log --oneline -15`, branch hiện tại, các commit SAU `3704b6e` (016).
- `git status -s` (file đang sửa/chưa commit) — đặc biệt có file 013/015 nào uncommitted không.

### 2. Theo từng task
- **019 funding live:** `FundingFeeManager` (có `startProductionRefresh`/`refreshCache`?) + `FundingIngestor` (heartbeat idle?) — commit hash nào chứa? Jar đang chạy 242 build lúc nào? Log live còn dòng `OI-History-Crawl` không (còn = jar cũ 106baee, chưa deploy bản gỡ-crawl+016+019)?
- **013 OI metrics:** set OI/LS/taker trên Aerospike (226 và 242) — CÓ data chưa? Mỗi set: #record, vài symbol + range ts (vd BTCUSDT từ…đến…). Class backfill + verify B1 (granularity/đơn vị/dedup) commit chưa? File coverage trong `outputs/`?
- **015 feature A:** `outputs/` có file feature nhóm A chưa (tên + #dòng + #cột)? Class export commit chưa? Validate từng group có log/file?
- **010 lifecycle:** set `symbol_lifecycle` (226+242) có data chưa? #record + #LIVE/#DATA_INCOMPLETE/#DEAD. Builder đã CHẠY trên 226 chưa (log/PID)? Validate recompute chạy chưa?

### 3. Khác
- **009 forward-rolling:** live có đang cập nhật nến 15m/4h mới không (đọc set kline_15m/4h_btceth ts mới nhất)?
- Task DOING/chưa-đóng nào khác còn sót.

## Acceptance
- [ ] `docs/STATUS_RECON.md` có: git log/status + 4 task (019/013/015/010) với trạng thái + bằng chứng + 009 forward.
- [ ] Đủ để Desktop reconcile AGENTS và quyết task nào cần chạy/chạy-lại.
- [ ] KHÔNG sửa gì.
