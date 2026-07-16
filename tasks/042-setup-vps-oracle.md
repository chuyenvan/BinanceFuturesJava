---
id: 042
status: CANCELLED
owner: CCD
touches_live_process: true   # phan B sua firewalld 242 (production)
writes_242_data: false       # chi MO READ Aerospike cho IP moi, khong ghi
resource: vps_oracle_new(161.118.212.3) + 242
report: docs/reports/042.md
require_review: true
---

# TASK-042: Setup VPS Oracle mới (161.118.212.3) + mở 242 cho đọc Aerospike

VPS mới: **161.118.212.3**, user **ubuntu** (KHÁC 226/242 dùng root → cần `sudo`). Mới toanh.
Key SSH: **giống 226/242** (`id_rsa_chuyennd`). Mục tiêu: node compute giống 226 + được 242
cho phép đọc Aerospike, + xử lý MTU/timezone đặc thù Oracle Cloud.

## Đã ĐO THỰC TẾ (không đoán — dùng làm chuẩn)
- SSH 242 trực tiếp từ ngoài: `ssh -i id_rsa_chuyennd -p 2222 root@103.157.218.242` → OK (cùng key/port như 226). 242: root, Java 11.0.22, **timezone đã GMT+7**.
- 226 đọc Aerospike 242 qua **cổng 3222** (KHÔNG phải 3000). Firewall 242 = **firewalld** (rich rules).
- Rule hiện có cho 226: `rule family="ipv4" source address="103.157.218.226/32" port port="3222" protocol="tcp" accept`. Đã có sẵn rule tương tự cho `161.118.206.1/32` ở 3222.
- MTU 242: ens192 và tun0 đều **1500**.

## PHẦN A — Setup VPS mới (chắc chắn)
SSH: `ssh -i <key_chuyennd> ubuntu@161.118.212.3` (thử port 22 trước; nếu refused thử 2222). Mọi lệnh cài dùng `sudo`.

1. **Java 11**: `sudo apt update && sudo apt install -y openjdk-11-jdk` → verify `java -version` = 11.
2. **Node.js 20** (cho Claude Code): `curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs` → `node -v`, `npm -v`.
3. **Claude Code**: `sudo npm install -g @anthropic-ai/claude-code` → `claude --version`. (Login/API key: GHI rõ trong report bước nào user phải tự làm.)
4. **Python + venv + kaggle**: `sudo apt install -y python3 python3-pip python3-venv`; tạo `~/envs/xgb-env` (giống 226); `pip install kaggle xgboost pandas numpy python-snappy`.
5. **Kaggle creds**: copy `~/.kaggle/kaggle.json` từ 226 sang `~/.kaggle/` (chmod 600). KHÔNG in nội dung ra log.
6. Verify: `java -version`, `node -v`, `claude --version`, `python3 -c "import kaggle"`.

## PHẦN B — Timezone + MTU (đặc thù Oracle Cloud, user dặn)
1. **Timezone GMT+7**: `sudo timedatectl set-timezone Asia/Ho_Chi_Minh` → verify `date` ra +07. (242 đã GMT+7, đồng bộ cho khớp.)
2. **MTU đồng bộ 1500** (242 dùng 1500; Oracle hay mặc định 9000 → treo gói khi nói với 242):
   - Xem hiện tại: `ip link | grep mtu`.
   - Set tạm: `sudo ip link set dev <iface> mtu 1500` (iface thường `ens3`/`enp0s3` trên Oracle — kiểm trước).
   - Set cố định qua netplan: sửa `/etc/netplan/*.yaml` thêm `mtu: 1500` cho interface, `sudo netplan apply`.
   - **MSS clamping** (phòng path-MTU treo TCP tới 242): cân nhắc
     `sudo iptables -t mangle -A POSTROUTING -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu`.
   - Verify path tới 242 không phân mảnh: `ping -M do -s 1472 103.157.218.242` (1472+28=1500) phải thông; nếu rớt → giảm MTU.

## PHẦN C — Mở 242 cho 161.118.212.3 đọc Aerospike (cổng 3222)
⚠️ touches_live_process — chạy trên 242 (production). Nhân bản ĐÚNG rule của 226.
SSH 242: `ssh -i <key> -p 2222 root@103.157.218.242`. Thêm rich rule + reload:
```
firewall-cmd --permanent --zone=public --add-rich-rule='rule family="ipv4" source address="161.118.212.3/32" port port="3222" protocol="tcp" accept'
firewall-cmd --reload
firewall-cmd --zone=public --list-rich-rules | grep 161.118.212.3   # xac nhan
```
KHÔNG xóa/sửa rule khác. KHÔNG mở cổng ghi — chỉ 3222 (client đọc) giống 226.

## VERIFY tổng (từ VPS mới)
- `nc -zv 103.157.218.242 3222` → succeeded.
- `ping -M do -s 1472 103.157.218.242` → thông (MTU ok).
- 1 query đọc Aerospike 242 từ VPS mới ra dữ liệu (vd build/scp tool đọc, host=103.157.218.242 port=3222; hoặc `asadm`/`aql -h 103.157.218.242:3222`).
- Report: bảng version Phần A + kết quả timezone/MTU + xác nhận rich rule + query đọc thành công. KHÔNG in secret.

## Lưu ý
- Aerospike namespace `ticker`, port client 3222 (KHÔNG 3000).
- Build Java vẫn làm ở LOCAL rồi scp (226 không tự compile; VPS mới cũng nên vậy nếu chỉ Java 11 JDK runtime đủ — nhưng cài JDK để chạy được tool).
- User cần tự làm: đăng nhập Claude Code (OAuth/API key).
