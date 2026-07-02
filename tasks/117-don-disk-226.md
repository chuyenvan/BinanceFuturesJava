# TASK-117: Dọn disk server 226 (97% → mục tiêu ≤85%) — HEADLESS, master giám sát

- **status:** doing (headless CCD, launch bởi master 2026-07-02 tối)
- **resource:** SSH 226 (`ssh -i /c/Users/pc/.ssh/id_rsa_chuyennd -p 2222 root@103.157.218.226`)
- **touches_live_process:** KHÔNG ĐƯỢC PHÉP (Aerospike 226 là nguồn dữ liệu backtest đang dùng)

## ⛔ HÀNG RÀO CỨNG (vi phạm = hỏng dữ liệu không hồi được)
1. CẤM TUYỆT ĐỐI đụng: mọi thư mục/file của Aerospike (`/opt/aerospike*`, `/etc/aerospike*`, mọi path chứa
   `aerospike`, file `.dat`), `/var/lib/`, database files, file <7 ngày tuổi, bất kỳ process nào đang chạy.
2. CẤM `rm -rf` thư mục chưa `du -sh` + `ls` liệt kê nội dung trong log TRƯỚC khi xoá.
3. Xoá >1GB: PHẢI ghi vào log path + size + lý do TRƯỚC. Không chắc chắn → GHI `NEEDS_HUMAN: <câu hỏi>`
   vào phần Kết quả file này và DỪNG mục đó, làm tiếp mục khác.
4. Ưu tiên REVERSIBLE: nén (`gzip`) log cũ thay vì xoá khi phân vân; xoá thẳng chỉ với whitelist mục 5.
5. WHITELIST xoá thẳng: `*.log`/`*.log.*` cũ >30 ngày ngoài thư mục aerospike · `~/.cache/pip` `~/.npm/_cacache`
   · `/tmp/*` cũ >7 ngày · `journalctl --vacuum-size=200M` · jar/bin trùng lặp cũ trong `~/java` (giữ jar mới nhất
   mỗi tên + jar nào được process đang chạy dùng — kiểm `lsof`/`ls /proc/*/cwd` trước).

## Việc làm
1. Đo: `df -h /` + `du -xh --max-depth=2 / 2>/dev/null | sort -rh | head -25` → ghi bảng vào log.
2. Dọn theo whitelist, đo lại sau mỗi cụm, ghi log từng lệnh.
3. Kết thúc: `df -h /` + xác nhận Aerospike sống (`asinfo -p 3222 -v status`) → ghi Kết quả.

## Output bắt buộc
- Log đầy đủ: `/d/claudedata/task117_don226.log`
- Phần Kết quả file này: bảng top-du trước/sau, danh sách đã xoá/nén (path+size), df cuối, trạng thái asinfo.

## Kết quả
<headless điền>
