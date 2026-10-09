# Runbook — cứng hoá host 242 (autostart + healthcheck + Redis persistence + đóng 53/8002)

Owner duyệt 2026-10-09: autostart Aerospike/Redis/app, healthcheck cảnh báo khi app chết, sửa Redis persistence, đóng 53 và 8002.
Khảo sát CHỈ ĐỌC 2026-10-09 07:00–07:16 +07 (agent; không đổi gì trên 242/Oracle). Người thực thi: **MASTER**, theo đúng thứ tự R6.
Script khảo sát + output thô: Oracle `~/claude_master/1003/h242_k{1..9}.sh|.out`. Healthcheck: `research/ops/health_242.sh`.

Quy ước lệnh (chạy từ Oracle; khối nhiều dòng ⇒ ghi file, scp lên `/root/harden_$TS/` rồi `bash` trên 242):
```bash
S="ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"
SCP="scp -P 2222 -o BatchMode=yes -i /home/ubuntu/.ssh/id_rsa_chuyennd"
# trên 242:
R=/opt/setup/redis-7.0.8/src/redis-cli; H=103.157.218.242
OLD=/opt/setup/redis-7.0.8/utils/create-cluster; NEWR=/var/lib/redis-cluster
TS=$(date +%Y%m%d_%H%M); B=/root/harden_$TS; mkdir -p $B
```
**Cửa sổ cấm**: 12:50–13:20 và 00:50–01:20 +07 (auto-restart 12h của trading/ingest đang ở ~01:06/13:06 và ~01:21/13:21; lệch dần — đọc
`grep 'Restart: ' logs/full.log | tail -1` trước khi làm). Không làm 2 mục cùng lúc.

---
## K. Kết quả khảo sát (lệnh + output rút gọn)

### K1 Hệ thống
- `cat /etc/redhat-release; systemctl --version` → CentOS 7.9.2009, kernel 3.10.0-1160, **systemd 219**. TZ Asia/Bangkok (+07).
- `uptime; who -b` → up 2 ngày, boot `Oct 7 05:56`. `free -m` → 7 821 MB, available ~2 800, swap dùng 593 MB. `df` → `/` 92G, **87 %** (13G trống).
- `systemctl list-unit-files` → enabled: crond, firewalld, iptables-openvpn, openvpn-server@, mongod, sshd, NetworkManager(-wait-online),
  network. **disabled: aerospike, docker, containerd**. Không có unit redis/app. Default target multi-user.
- `crontab -l` root → *no crontab*; user `chuyennd` **không tồn tại** (mọi tiến trình chạy root); `/etc/cron.d` chỉ 0hourly;
  `rc.local` chỉ `touch /var/lock/subsys/local` (không exec bit).
- `ps` → asd (pid 8800, start 10-07 08:10), 6 redis-server (10-07 08:12), ingest JVM 10812 (10-09 01:21), trading JVM 28123 (10-09 01:06),
  cả hai JVM `ppid=1`, cgroup `user.slice/user-0.slice/session-{10,66}.scope` (không thuộc unit nào), `Max open files 4096`.

### K2 Aerospike
- `systemctl cat aerospike` → `/usr/lib/systemd/system/aerospike.service`: `After=network-online.target`, `Wants=network.target`,
  `ExecStartPre=/usr/bin/asd-systemd-helper`, `ExecStart=/usr/bin/asd … --fgdaemon`, `ExecStartPre=-/bin/systemctl start aerospike_telemetry`,
  `TimeoutSec=600`, `WantedBy=multi-user.target`; drop-in `/etc/systemd/system/aerospike.service.d/aerospike.conf` (rỗng). `is-enabled` → **disabled**.
- Config: service `127.0.0.1:3000` + `103.157.218.242:3222`; ns `ticker` storage-engine device `/opt/aerospike/data/ticker.data` 50G,
  `data-in-memory false`. Không có asinfo/asadm trên 242.
- Thời gian nạp 10-07 (log GMT): `01:10:24 {ticker} beginning cold start` → `01:10:51 read complete: UNIQUE 3302622` →
  `01:10:51 service ready: soon there will be cake!` ⇒ **cold start 27 s** (không phải ~2 phút như ghi chép cũ).

### K3 Redis cluster — NGUYÊN NHÂN MẤT STATE 10-07 (đã chứng minh)
- `/opt/redis_cluster_config.sh start`: vòng 30001–30006 chạy `redis-server --port $P --cluster-enabled yes --cluster-config-file nodes-$P.conf
  --appendonly yes --appendfilename appendonly-$P.aof --dbfilename dump-$P.rdb --logfile $P.log --daemonize yes --protected-mode no
  --bind 103.157.218.242 --maxmemory 2048mb` — **không có `--dir`** ⇒ mọi file (AOF, RDB, nodes.conf, log) nằm ở **thư mục hiện hành (cwd)**
  của người gõ lệnh. Không requirepass (`CONFIG GET requirepass` rỗng), `enable-protected-configs=no`.
- `CONFIG GET dir` cả 6 node hiện tại → `/opt/setup/redis-7.0.8/utils/create-cluster`; `/proc/<pid>/cwd` cùng giá trị.
- Trước sự cố cluster chạy với cwd **`/opt`**: `/opt/appendonlydir/appendonly-3000{1,2,5,6}.aof.*.incr.aof` 41–63 MB, mtime
  **2026-10-07 00:45:06–00:45:10** (= lúc host sập), `/opt/nodes-300*.conf`, `/opt/dump-300*.rdb` (00:44), `/opt/300*.log` dừng 00:44.
- 10-07 08:12 cluster được start từ cwd `create-cluster` (thư mục cũ từ 11/2024): log `30001.log` →
  `08:12:03 Node configuration loaded, I'm b21999c2…` (nodes.conf 2024) → `Creating AOF base file appendonly-30001.aof.1.base.rdb on server start`
  (= không tìm thấy AOF nào ⇒ DB rỗng; base 88 byte) → `08:12:06 Cluster state changed: fail` → 08:47:40 `IP address for this node updated to
  103.157.218.242`, `Address updated for node … now 103.157.218.242:3000x` (nodes.conf 2024 lưu địa chỉ peer khác IP public) → `08:47:46 ok`.
- ⇒ **Nguyên nhân gốc: đường dẫn dữ liệu tương đối theo cwd + start từ thư mục khác** ⇒ nạp nodes.conf/AOF của cluster 2024 (rỗng) thay vì
  dữ liệu `/opt` 10-07 00:45. Giả thuyết cũ "6 node dùng chung appendonlydir" **KHÔNG phải nguyên nhân**: tên file khác nhau theo port
  (`appendonly-<port>.aof.*`, manifest riêng), dùng chung thư mục vẫn an toàn. Lịch sử lặp lại: `/opt/setup/redis-7.0.8/` (dữ liệu tới 2024-11-10),
  `create-cluster/appendonlydir-3000x` (2024-11-10), `/opt` (2024-11 → 2026-10-07) — mỗi lần đổi cwd là một "đời" cluster mới.
- Phụ: ở `/opt`, node 30004 đã chết từ **2026-02-23** (`/opt/30004.log`, aof dừng 02-23; nodes.conf các node có `:0@0 master,fail,noaddr`) —
  không ai phát hiện ⇒ shard 0–5460 chạy không replica 7 tháng. Dữ liệu `/opt` vẫn còn nguyên (lưu trữ, KHÔNG xoá, KHÔNG khôi phục — cũ 2 ngày).
- Hiện trạng (`INFO`, `CLUSTER INFO/NODES`): `cluster_state:ok`, 16384 slots, 6 node, epoch 6. Master 30001 (0–5460), 30002 (5461–10922),
  30003 (10923–16383); replica 30004→30001, 30005→30002, 30006→30003, `master_link_status:up`. Mọi node: `appendonly=yes`,
  `appendfsync=everysec`, `appenddirname=appendonlydir`, `save 3600 1 300 100 60 10000`, `cluster-announce-ip` rỗng, `bind 103.157.218.242`
  (127.0.0.1:30001 → *Connection refused*), `aof_last_write_status:ok`, `rdb_last_bgsave_status:ok`.
- Dữ liệu (nhỏ): `redis.key.symbol.order.info` hash **47** field (trạng thái order/SL của 47 vị thế legacy — đây là state bị mất 10-07),
  `redis.key.educa.all.symbols.running` hash 47, `redis.key.educa.all.symbols` hash 734, `redis.key.last.time.check.market` string.
  DBSIZE 2/1/1. File AOF incr 30002/30005 ≈ 11 MB, còn lại < 0,3 MB.
- Log 10-07 10:10/10:34 có `Possible SECURITY ATTACK … POST or Host:` (trước khi chặn firewall 11:03) — bằng chứng redis từng bị quét từ internet.
- `vm.overcommit_memory=0` (redis cảnh báo khi start; dữ liệu nhỏ nên BGSAVE vẫn ok — không xử lý trong runbook này).

### K4 App trading + ingest
- Trading `/home/chuyennd/java/v_t_m`, ingest `/home/chuyennd/java/collectData`; cả hai: `bin/daemon.sh start` = source `conf/env.sh`
  (`APP_PID_DIR=./run` tương đối ⇒ phải cd), `nohup bin/start.sh … > logs/nohup.out &`, `echo $! > ./run/<MainClass>.pid`;
  `start.sh` = `cd $(dirname $0)/..; exec java -server -Xms5g -Xmx5g -Dfile.encoding=UTF-8 … -cp target/binance-java-sdk-1.2.4.jar <Main>`
  (ingest `-Xms2048m -Xmx2048m`, không -Dfile.encoding). `daemon.sh stop` = SIGTERM, chờ ≤ 60 s rồi `kill -9`.
- Auto-restart (repo Oracle HEAD f8a925d2): trading `BinanceOrderTradingManager.startThreadAutoRestartProgram` — `Thread.sleep(12h)` rồi
  `Utils.reset("Reset by Schedule")` (12h từ FIX 10-01; ghi chú "4h" trong `LiveGateRollingRatio`/`GateRatioPersist`/infra_ops đã lỗi thời).
  Ingest: mỗi phút `checkAndComparePriceDiff`; > 50 symbol lệch ⇒ `Utils.reset("Reset by Price Error Count …")`; đếm phút > 720 ⇒ reset 12h.
  Ngoài ra `Reporter.buildReport` reset nếu `redis.key.last.time.check.market` cũ > 15 phút.
- `Utils.reset`: chờ giây 30–45 của phút → `ProcessBuilder(java.home/bin/java, "-cp", java.class.path, sun.java.command)` (MẤT -Xms/-Xmx và
  -Dfile.encoding), copy env, `inheritIO()`, `start()` rồi **`System.exit(0)`**. JVM con không detach (không setsid) ⇒ cùng cgroup với cha,
  được init nhận làm con (ppid 1). JVM con gọi `Utils.writePid2File()` (ghi đè pidfile, shutdown hook xoá pidfile khi thoát).
  Log thực: `08/10 08:52:39 Restart: Reset by Schedule`, `09/10 01:06:31 Restart: Reset by Schedule` → `01:06:41 Start thread ThreadAutoRestartProgram`.
- Shutdown hook: `GateRatioPersistFlush` (LiveGateRollingRatio), `LiveFeatureDump`, xoá pidfile (Utils), `WebSocketWatchDog`.
- Phụ thuộc: `RedisConst` đọc `./redis.config` (`Redis.Address` = 6 node `103.157.218.242:30001..30006`), thiếu file ⇒ `System.exit(0)`;
  `JedisCluster` dựng lúc dùng đầu tiên. 10-07 trading start 08:51 SAU khi cluster ok 08:47 ⇒ không có log lỗi "thiếu redis" để đối chiếu;
  KHÔNG dựa vào app tự chịu được — gate bằng ExecStartPre (R3). Thread `ThreadListenQueueOrder2ManagerNew` (blpop) bắt mọi Exception và lặp
  lại (không sleep) ⇒ chịu được failover redis (MOVED/UNBLOCKED), nhưng spam log nếu redis chết lâu.
- Env tiến trình: trading `LANG=C.UTF-8` (**locale này không có trên CentOS 7**: `locale -a` chỉ `en_US.utf8`; JVM con sau reset không có
  -Dfile.encoding), ingest `LANG=en_US.UTF-8`. Unit R3 đặt `LANG=en_US.UTF-8`.

### K5 Cổng
- `ss -tulpn` → **không tiến trình nào nghe 53 (tcp/udp) và 8002**; cũng không có gì nghe 80/443. Đang nghe: 1194/udp openvpn, 2222 sshd,
  3222 (127.0.0.1 + IP) / 3001 / 3003 / 9918-mcast asd, 30001–30006 + 40001–40006 redis (IP public), **27017 mongod (`*:27017`, mongod enabled)**.
- `firewall-cmd --zone=public --list-all` → ports `8002/tcp 1194/udp 80/tcp 443/tcp 53/tcp 53/udp 2222/tcp`; services `dhcpv6-client openvpn ssh`;
  masquerade yes; sources `10.8.0.0/24 103.157.218.242/32`; rich rules redis chỉ Oracle + 242 (sửa 10-07), 3222 cho danh sách IP,
  27017 cho `192.168.10.0/24`. Runtime = permanent (chỉ khác dòng `interfaces: ens192` — interface gán qua NM, default zone public).
- OpenVPN `/etc/openvpn/server.conf`: `push "dhcp-option DNS 8.8.8.8"`, `push "dhcp-option DNS 8.8.4.4"`, redirect-gateway ⇒ **client VPN
  dùng DNS Google, không dùng DNS của 242**; `status.log` 0 client đang kết nối. Không có dnsmasq/named/unbound (chỉ `bind-export-libs`).
  ⇒ 53 mở mà không ai phục vụ, không ai dùng ⇒ đóng hẳn (không cần rich rule cho 10.8.0.0/24).
- Docker: `vigilant_chatterjee` (pcko1/tvcs, `0.0.0.0:8002->6666`) **Exited (255) 47h** (chết theo host 10-07, `restart=no`), `jolly_cray` Exited 2 năm.
  Không service nào khác cần docker ⇒ đóng 8002, giữ docker **disabled** (không bật lại container).

### K6 Kênh cảnh báo
- Repo có 2 nơi gửi Telegram với **bot token + chat id hardcode trong source** (không in giá trị): `Utils.sendSms2Telegram` (dùng bởi
  `Reporter.buildReport` và `DetectEntrySignal2TradeNormal:1426`) và `P2PTelegramNotifier`. `OracleMonitor` có nhánh Telegram nhưng bị comment.
  `config.properties` 242 có biến `TELE_CLAW` (không được code HEAD dùng). Shadow Oracle `bin/health.sh` không gửi gì ra ngoài.
- Oracle → `https://api.telegram.org/` trả HTTP 302 (ra được internet). Không có mail/sendmail/msmtp trên Oracle.
- ⇒ Kênh khả dụng kỹ thuật: Telegram. **Cần owner quyết**: dùng lại bot/chat của `Utils.sendSms2Telegram` (owner đang nhận báo cáo Reporter)
  hay tạo bot riêng; healthcheck đọc token từ file `~/.config/health242/tg.env` (chmod 600, KHÔNG commit). Chưa có file ⇒ script ghi
  `ALERT_PENDING_NEED_OWNER_CHANNEL.txt` (đã kiểm). Token hardcode trong repo là rủi ro bảo mật riêng (đề xuất owner xoay token).

---
## R1 Autostart Aerospike (0 phút dừng app)
```bash
# trên 242
systemctl is-enabled aerospike                      # trước: disabled
mkdir -p /etc/systemd/system/aerospike.service.d
printf '[Unit]\nWants=network-online.target\n\n[Service]\nRestart=on-failure\nRestartSec=10\n' > /etc/systemd/system/aerospike.service.d/10-harden.conf
systemctl daemon-reload
systemctl enable aerospike
systemctl is-enabled aerospike; systemctl is-active aerospike     # PASS: enabled / active (không restart asd)
systemctl show aerospike -p Wants -p After -p Restart | tr '\n' ' '  # PASS: Wants chứa network-online.target, Restart=on-failure
```
- Rủi ro: thấp — `enable` chỉ tạo symlink; drop-in chỉ hiệu lực ở lần start sau. `Restart=on-failure`: asd crash ⇒ tự lên (cold start ~27 s).
- Rollback: `systemctl disable aerospike; mv /etc/systemd/system/aerospike.service.d/10-harden.conf $B/; systemctl daemon-reload`.
- KHÔNG enable docker/containerd (không cần; tvcs bỏ).

## R2 Redis — dir tuyệt đối riêng từng node + systemd, chuyển cuốn chiếu KHÔNG dừng app

Phương án chọn: **rolling theo cặp master/replica** (replica trước; master: `CLUSTER FAILOVER` có kiểm soát từ replica rồi mới chuyển).
Lúc nào cũng có 1 bản sống giữ dữ liệu ⇒ không mất state; app **không dừng** (JedisCluster tự theo MOVED; thread blpop bắt lỗi và lặp).
Gián đoạn ghi: < 1–2 s mỗi lần failover × 3. Phương án dừng app toàn bộ (stop app → stop 6 node → copy → start) cho 3–5 phút 47 vị thế
không quản lý — chỉ dùng nếu rolling hỏng giữa chừng.

Đích: `/etc/redis-cluster/<port>.conf`, dữ liệu `/var/lib/redis-cluster/<port>/{nodes-<port>.conf, dump-<port>.rdb, appendonlydir/, <port>.log}`;
giữ nguyên tên file (copy thẳng), `cluster-announce-ip 103.157.218.242` tường minh, `bind` giữ IP public (KHÔNG thêm 127.0.0.1: không cần —
app + Oracle dùng IP public; thêm bind phụ có rủi ro nguồn cluster-bus sai IP như sự cố 10-07). Lên đúng sau reboot nhờ: dir tuyệt đối +
nodes.conf toàn `103.157.218.242` + `After/Wants=network-online.target` (NetworkManager-wait-online **enabled**, ens192 static, ONBOOT=yes).

### R2.0 Snapshot + backup (chỉ đọc + BGSAVE, 2 phút)
```bash
for p in 30001 30002 30003 30004 30005 30006; do echo "$p $($R -h $H -p $p ROLE | head -1) dbsize=$($R -h $H -p $p DBSIZE)"; done | tee $B/pre_roles.txt
$R -h $H -p 30001 --cluster check $H:30001 | tail -3 | tee $B/pre_check.txt          # [OK] All 16384 slots covered.
for k in redis.key.symbol.order.info redis.key.educa.all.symbols.running redis.key.educa.all.symbols; do echo "$k $($R -c -h $H -p 30001 HLEN $k)"; done | tee $B/pre_hlen.txt
$R -c -h $H -p 30001 HGETALL redis.key.symbol.order.info > $B/order_info.hgetall; chmod 600 $B/order_info.hgetall   # lưới an toàn (47 field)
for p in 30001 30002 30003; do $R -h $H -p $p BGSAVE; done; sleep 3
tar czf $B/redis_createcluster_before.tgz -C $OLD nodes-30001.conf nodes-30002.conf nodes-30003.conf nodes-30004.conf nodes-30005.conf nodes-30006.conf \
  dump-30001.rdb dump-30002.rdb dump-30003.rdb dump-30004.rdb dump-30005.rdb dump-30006.rdb appendonlydir
cp -p /opt/redis_cluster_config.sh $B/
```

### R2.1 Chuẩn bị config + unit (không ảnh hưởng gì đang chạy)
```bash
mkdir -p /etc/redis-cluster
for p in 30001 30002 30003 30004 30005 30006; do
  mkdir -p $NEWR/$p/appendonlydir
  cat > /etc/redis-cluster/$p.conf <<EOF
port $p
bind 103.157.218.242
protected-mode no
daemonize no
dir $NEWR/$p
logfile $NEWR/$p/$p.log
cluster-enabled yes
cluster-config-file nodes-$p.conf
cluster-node-timeout 2000
cluster-announce-ip 103.157.218.242
appendonly yes
appendfilename appendonly-$p.aof
appenddirname appendonlydir
appendfsync everysec
dbfilename dump-$p.rdb
save 3600 1 300 100 60 10000
maxmemory 2048mb
EOF
done
cat > /etc/systemd/system/redis-cluster@.service <<'EOF'
[Unit]
Description=Redis cluster node %i (242)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/opt/setup/redis-7.0.8/src/redis-server /etc/redis-cluster/%i.conf
Restart=on-failure
RestartSec=5
StartLimitInterval=300
StartLimitBurst=10
LimitNOFILE=65536
TimeoutStopSec=60

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl show redis-cluster@30006 -p ExecStart -p Restart -p After -p LimitNOFILE | cut -c1-160   # PASS: ExecStart …/etc/redis-cluster/30006.conf, Restart=on-failure
grep -c . /etc/redis-cluster/3000*.conf      # 17 dòng mỗi file; systemctl is-active redis-cluster@3000x = inactive (chưa start)
```
- `systemctl stop` gửi SIGTERM ⇒ redis tự lưu RDB + fsync AOF rồi thoát 0 (không cần ExecStop). `daemonize no` bắt buộc với Type=simple.

### R2.2 Script chuyển 1 node (chỉ chạy cho node đang là REPLICA) — `$B/mv_node.sh <port>`
```bash
#!/bin/bash
set -u
P=$1; R=/opt/setup/redis-7.0.8/src/redis-cli; H=103.157.218.242
OLD=/opt/setup/redis-7.0.8/utils/create-cluster; N=/var/lib/redis-cluster/$P
role=$($R -h $H -p $P ROLE | head -1); [ "$role" = slave ] || { echo "ABORT $P role=$role (phải là slave)"; exit 1; }
[ -e $N/nodes-$P.conf ] && { echo "ABORT $N đã có nodes.conf"; exit 1; }
[ "$($R -h $H -p 30001 CLUSTER INFO | tr -d '\r' | awk -F: '/^cluster_state/{print $2}')" = ok ] || { echo "ABORT cluster không ok"; exit 1; }
$R -h $H -p $P SHUTDOWN 2>/dev/null                    # replica: lưu RDB + fsync AOF + ghi nodes.conf, thoát
for i in $(seq 1 20); do pgrep -f "redis-server $H:$P" >/dev/null || break; sleep 0.5; done
pgrep -f "redis-server $H:$P" >/dev/null && { echo "ABORT $P chưa tắt"; exit 1; }
cp -p $OLD/nodes-$P.conf $OLD/dump-$P.rdb $N/ && cp -p $OLD/appendonlydir/appendonly-$P.aof.* $N/appendonlydir/ || { echo "COPY FAIL"; exit 1; }
systemctl start redis-cluster@$P
for i in $(seq 1 30); do [ "$($R -h $H -p $P INFO replication 2>/dev/null | tr -d '\r' | awk -F: '/^master_link_status/{print $2}')" = up ] && break; sleep 1; done
echo "$P active=$(systemctl is-active redis-cluster@$P) dir=$($R -h $H -p $P CONFIG GET dir | sed -n 2p)" \
     "$($R -h $H -p $P INFO replication | tr -d '\r' | grep -E '^(role|master_port|master_link_status)' | tr '\n' ' ')" \
     "dbsize=$($R -h $H -p $P DBSIZE) $($R -h $H -p $P CLUSTER INFO | tr -d '\r' | grep cluster_state)"
```
PASS mỗi node: `active`, `dir=/var/lib/redis-cluster/<P>`, `role:slave master_link_status:up`, `dbsize` = DBSIZE master của nó, `cluster_state:ok`,
và `readlink /proc/$(pgrep -f "redis-server $H:<P>")/cwd` không còn là `$OLD`. Thời gian ≈ 10 s/node (node replica tạm vắng, slot không ảnh hưởng).

### R2.3 Thứ tự (cặp: 30001↔30004, 30002↔30005, 30003↔30006 — kiểm lại bằng `ROLE` trước mỗi bước)
```bash
bash $B/mv_node.sh 30006; bash $B/mv_node.sh 30005; bash $B/mv_node.sh 30004       # 3 replica trước (an toàn nhất)
# master 30003: failover có kiểm soát từ replica 30006 (đã chạy systemd), rồi chuyển 30003 (nay là replica)
$R -h $H -p 30006 CLUSTER FAILOVER; sleep 3
$R -h $H -p 30006 ROLE | head -1; $R -h $H -p 30003 ROLE | head -1                  # PASS: master / slave
bash $B/mv_node.sh 30003
$R -h $H -p 30005 CLUSTER FAILOVER; sleep 3; $R -h $H -p 30005 ROLE | head -1; $R -h $H -p 30002 ROLE | head -1; bash $B/mv_node.sh 30002
$R -h $H -p 30004 CLUSTER FAILOVER; sleep 3; $R -h $H -p 30004 ROLE | head -1; $R -h $H -p 30001 ROLE | head -1; bash $B/mv_node.sh 30001
```
- Sau mỗi failover: trên app `grep -c 'ERROR during ThreadListenQueuePosition2ManagerNew' logs/full.log` tăng ít (vài dòng) là chấp nhận;
  `[LEGACY] managed 47` + `Update all position:47` vẫn mỗi phút. Nếu lỗi tăng liên tục > 1 phút ⇒ DỪNG, xem R2.6.
- Tuỳ chọn (gọn topology, không bắt buộc): failback `$R -h $H -p 30001 CLUSTER FAILOVER` (tương tự 30002, 30003). Không cần cho an toàn.
- Cuối cùng: `systemctl enable redis-cluster@30001 redis-cluster@30002 redis-cluster@30003 redis-cluster@30004 redis-cluster@30005 redis-cluster@30006`.

### R2.4 Kiểm sau chuyển
```bash
for p in 30001 30002 30003 30004 30005 30006; do echo "$p $(systemctl is-enabled redis-cluster@$p)/$(systemctl is-active redis-cluster@$p) $($R -h $H -p $p ROLE | head -1) dbsize=$($R -h $H -p $p DBSIZE) dir=$($R -h $H -p $p CONFIG GET dir | sed -n 2p) cwd=$(readlink /proc/$(pgrep -f "redis-server $H:$p")/cwd)"; done
$R -h $H -p 30001 --cluster check $H:30001 | tail -3                                   # [OK] All 16384 slots covered.
for k in redis.key.symbol.order.info redis.key.educa.all.symbols.running redis.key.educa.all.symbols; do echo "$k $($R -c -h $H -p 30001 HLEN $k)"; done   # ≈ pre_hlen (47/47/734, lệch chỉ do app)
grep -h -c '127.0.0.1' $NEWR/*/nodes-*.conf | paste -sd' '                            # PASS: 0 0 0 0 0 0
awk '$2 ~ /:/ {print $2}' $NEWR/30001/nodes-30001.conf | sort -u                       # PASS: chỉ 103.157.218.242:3000x@4000x
ls -la $NEWR/*/appendonlydir/ | grep -c incr.aof                                        # 6; mtime incr của master mới tăng theo thời gian
```
Trên app: `[LEGACY] managed 47`, `Update all position:47` mỗi phút; **không** có dòng `New order 2 redis because order null` mới (dấu hiệu mất state).

### R2.5 (b) Mô phỏng restart 1 node (chỉ replica; chứng minh tự lên + Restart=on-failure)
```bash
RP=$(for p in 30001 30002 30003 30004 30005 30006; do [ "$($R -h $H -p $p ROLE | head -1)" = slave ] && echo $p && break; done); echo replica=$RP
systemctl restart redis-cluster@$RP; sleep 5
$R -h $H -p $RP INFO replication | tr -d '\r' | grep -E '^(role|master_link_status)'; $R -h $H -p 30001 CLUSTER INFO | grep cluster_state   # slave/up/ok
systemctl kill -s SIGKILL redis-cluster@$RP; sleep 10
systemctl is-active redis-cluster@$RP; systemctl show redis-cluster@$RP -p NRestarts 2>/dev/null; journalctl -u redis-cluster@$RP -n 5 --no-pager
# PASS: active trở lại sau ~5 s (systemd 219 không có NRestarts — xem journal "Service hold-off time over, scheduling restart"), link up, cluster ok
```
Mô phỏng nguyên cụm sau reboot = R6 checklist (không reboot thật). Bằng chứng cấu trúc: dir tuyệt đối (không phụ thuộc cwd), nodes.conf mỗi node
toàn IP public = đúng IP bind, unit chờ network-online ⇒ 6 node đọc lại đúng nodes.conf/AOF và tự bắt tay như sau mỗi `systemctl restart`.

### R2.6 Rollback
- Một node (trong lúc chuyển): `systemctl stop redis-cluster@$P; cp -p $NEWR/$P/nodes-$P.conf $OLD/nodes-$P.conf;`
  `cd $OLD && /opt/setup/redis-7.0.8/src/redis-server --port $P --cluster-enabled yes --cluster-config-file nodes-$P.conf --cluster-node-timeout 2000 --appendonly yes --appendfilename appendonly-$P.aof --dbfilename dump-$P.rdb --logfile $P.log --daemonize yes --protected-mode no --bind 103.157.218.242 --maxmemory 2048mb`
  (chỉ khi node đó là replica; nó full-sync lại từ master). File ở `$OLD` không bị xoá/sửa trong R2 trừ nodes.conf khi rollback.
- Mất dữ liệu nghiêm trọng (cả cặp chết): dừng app (`cd /home/chuyennd/java/v_t_m && bin/daemon.sh stop`), khôi phục từ
  `$B/redis_createcluster_before.tgz` vào `$OLD`, start bằng script cũ **từ cwd `$OLD`** (`cd $OLD && /opt/redis_cluster_config.sh start`),
  kiểm `HLEN redis.key.symbol.order.info`=47 rồi mới start app. `$B/order_info.hgetall` là bản text để đối chiếu/HSET tay.

### R2.7 Khoá script cũ (tránh ai đó start trùng từ cwd khác)
```bash
sed -i '2i [ "$1" = start ] && { echo "DEPRECATED 2026-10: dung systemctl start redis-cluster@<port> (dir /var/lib/redis-cluster)"; exit 1; }' /opt/redis_cluster_config.sh
bash /opt/redis_cluster_config.sh start; echo rc=$?      # PASS: in DEPRECATED, rc=1, không spawn redis
```
Rollback: `cp -p $B/redis_cluster_config.sh /opt/redis_cluster_config.sh`.

### R2 (d) Cửa sổ + rủi ro
- App KHÔNG dừng. Tổng ~20 phút thao tác; mỗi node replica vắng ~10 s; 3 failover, mỗi lần ghi bị chặn < 2 s (client pause của FAILOVER).
  47 vị thế legacy: không có khoảng không quản lý (app sống suốt; tệ nhất vài lỗi blpop/ghi Redis trong 1–2 s, vòng `Update all position` kế tiếp
  chạy lại mỗi phút). Ngoài cửa sổ cấm (đầu runbook). Rủi ro chính: failover lỗi ⇒ dừng ở bước đó, cluster vẫn ok vì master cũ chưa bị đụng.
- Phương án dự phòng (nếu rolling không khả thi): dừng app → stop 6 node bằng `SHUTDOWN` → copy → `systemctl start` 6 unit → `cluster_state:ok`
  → start app. Ước lượng 3–5 phút không quản lý (stop ≤ 60 s + copy < 10 s + cluster ok ~5 s + app init ~10 s + thao tác).

---
## R3 Autostart app trading + ingest (0 phút dừng app — chỉ enable, áp dụng từ lần boot sau)

### Phân tích (systemd 219 + code)
- `Utils.reset` spawn JVM con (không setsid) rồi `System.exit(0)` ⇒ JVM con nằm **cùng cgroup**; tiến trình ban đầu (pid trong pidfile cũ) chết.
- `Type=simple/forking` (theo dõi main PID/PIDFile): main PID thoát ⇒ unit vào stop, với `KillMode=control-group` (mặc định) systemd
  **SIGTERM toàn cgroup ⇒ giết luôn JVM con** sau mỗi lần auto-restart 12h; `Restart=` sẽ start thêm bản thứ hai ⇒ nguy cơ 2 JVM cùng quản 47 vị thế.
  ⇒ KHÔNG dùng simple/forking.
- Chọn **`Type=oneshot` + `RemainAfterExit=yes` + `KillMode=none`**: systemd chỉ chạy `daemon.sh start` (trả về ngay sau `nohup … &`), unit
  ở trạng thái `active (exited)`, không theo dõi PID ⇒ JVM cha/con thay nhau bao nhiêu lần cũng không bị đụng. Tài liệu systemd 219
  (`man systemd.service`/`systemd.kill`): *RemainAfterExit= "service shall be considered active even when all its processes exited"*;
  *KillMode=none: "no process is killed … only the stop command will be executed"*. `ExecStop=daemon.sh stop` (đọc pidfile — JVM con tự ghi
  đè pidfile) ⇒ SIGTERM ⇒ shutdown hook (GateRatioPersistFlush, LiveFeatureDump) chạy; dùng khi `systemctl stop` và khi tắt máy.
- Không có tự restart khi JVM chết (oneshot) — cố ý: healthcheck R4 cảnh báo, người quyết (lý do ở R4).
- Kiểm chứng trên chính 242 trước khi enable (unit giả, không đụng app) — R3.1.

### R3.1 Thí nghiệm KillMode (5 phút, unit giả)
```bash
cat > /etc/systemd/system/h242-kmtest.service <<'EOF'
[Unit]
Description=TEST oneshot+RemainAfterExit+KillMode=none (mo phong Utils.reset)
[Service]
Type=oneshot
RemainAfterExit=yes
KillMode=none
ExecStart=/bin/bash -c 'nohup /bin/bash -c "sleep 20; (exec -a h242_child_test sleep 900) & exit 0" >/dev/null 2>&1 &'
ExecStop=/usr/bin/pkill -f [h]242_child_test
EOF
systemctl daemon-reload; systemctl start h242-kmtest; sleep 35
pgrep -fa '[h]242_child_test'                         # PASS A: con còn sống sau khi cha thoát
systemctl status h242-kmtest --no-pager | sed -n '1,12p' # PASS: active (exited), CGroup liệt kê h242_child_test
systemctl stop h242-kmtest; sleep 1; pgrep -fa '[h]242_child_test' || echo STOPPED_BY_EXECSTOP   # PASS
# Đối chứng B (chứng minh cơ chế giết): đổi RemainAfterExit=no + KillMode=control-group, daemon-reload, start, sleep 35
#   ⇒ pgrep rỗng (cgroup bị dọn ngay khi ExecStart thoát). Xong: mv unit sang /root/harden_$TS/, systemctl daemon-reload.
```
Nếu PASS A không đạt ⇒ DỪNG R3, không enable unit app.

### R3.2 Script chờ phụ thuộc `/usr/local/sbin/h242-prestart.sh` (ExecStartPre)
```bash
#!/bin/bash
# $1 = app dir, $2 = main class. Chờ Aerospike + Redis cluster ok (≤ 10 phút); đổi tên pidfile stale; KHÔNG start gì.
APP=$1; MC=$2; R=/opt/setup/redis-7.0.8/src/redis-cli; H=103.157.218.242
if pgrep -f -- "-cp target/binance-java-sdk-1.2.4.jar $MC" >/dev/null; then echo "$MC dang chay - khong start lan 2"; exit 1; fi
PF=$APP/run/$MC.pid
[ -f "$PF" ] && { echo "pidfile stale $(cat $PF) -> $PF.stale_$(date +%s)"; mv -f "$PF" "$PF.stale_$(date +%s)"; }
for i in $(seq 1 120); do
  a=down; timeout 3 bash -c "</dev/tcp/$H/3222" 2>/dev/null && timeout 3 bash -c "</dev/tcp/127.0.0.1/3000" 2>/dev/null && a=up
  s=; for p in 30001 30002 30003 30004 30005 30006; do
        s=$(timeout 3 $R -h $H -p $p CLUSTER INFO 2>/dev/null | tr -d '\r' | awk -F: '/^cluster_state/{print $2}'); [ -n "$s" ] && break; done
  [ "$a" = up ] && [ "$s" = ok ] && { echo "deps ok sau $((i*5))s"; exit 0; }
  sleep 5
done
echo "deps KHONG san sang sau 600s (aerospike=$a redis=${s:-noreply})"; exit 1
```
`chmod 755`. Mẫu `-cp target/… $MC` không khớp chính cmdline của script (đã tránh lỗi `java.*` khớp đường dẫn `/home/chuyennd/java/`).
Kiểm khô (app đang chạy): `/usr/local/sbin/h242-prestart.sh /home/chuyennd/java/v_t_m com.binance.chuyennd.trading.BinanceOrderTradingManager; echo rc=$?`
⇒ PASS: `… dang chay - khong start lan 2`, rc=1, pidfile KHÔNG bị đổi tên.

### R3.3 Unit
`/etc/systemd/system/h242-ingest.service`:
```ini
[Unit]
Description=242 BinanceDataIngestor (boot starter; app tu restart - systemd KHONG theo doi PID)
After=network-online.target aerospike.service redis-cluster@30001.service redis-cluster@30002.service redis-cluster@30003.service redis-cluster@30004.service redis-cluster@30005.service redis-cluster@30006.service
Wants=network-online.target aerospike.service

[Service]
Type=oneshot
RemainAfterExit=yes
KillMode=none
WorkingDirectory=/home/chuyennd/java/collectData
Environment=LANG=en_US.UTF-8
LimitNOFILE=65536
ExecStartPre=/usr/local/sbin/h242-prestart.sh /home/chuyennd/java/collectData com.binance.chuyennd.websocket.BinanceDataIngestor
ExecStart=/home/chuyennd/java/collectData/bin/daemon.sh start
ExecStop=/home/chuyennd/java/collectData/bin/daemon.sh stop
TimeoutStartSec=900
TimeoutStopSec=150

[Install]
WantedBy=multi-user.target
```
`/etc/systemd/system/h242-trading.service`: giống hệt, thay `collectData`→`v_t_m`, main class `com.binance.chuyennd.trading.BinanceOrderTradingManager`,
Description tương ứng, và thêm `h242-ingest.service` vào cuối dòng `After=` (thứ tự, không Requires — ingest lỗi không chặn trading).
```bash
systemctl daemon-reload
systemd-analyze verify /etc/systemd/system/h242-ingest.service /etc/systemd/system/h242-trading.service   # PASS: không lỗi của 2 unit này
systemctl show h242-trading -p Type -p RemainAfterExit -p KillMode -p After -p WorkingDirectory -p Environment | tr '\n' ' '
systemctl enable h242-ingest h242-trading      # KHÔNG start (app đang chạy ngoài unit; start sẽ bị prestart chặn rc=1 — vô hại)
systemctl is-enabled h242-ingest h242-trading   # enabled enabled
```

### R3.4 Đưa app đang chạy vào unit (TUỲ CHỌN, gộp vào lần dừng có kế hoạch kế tiếp)
Hiện JVM nằm trong `session-*.scope`; unit `inactive` ⇒ khi tắt máy ExecStop không chạy (JVM vẫn nhận SIGTERM từ scope — như hôm nay).
Muốn unit quản ngay: `cd /home/chuyennd/java/v_t_m && bin/daemon.sh stop && systemctl start h242-trading` (dừng ~1–2 phút: stop ≤ 60 s + init ~10 s),
kiểm `systemctl status h242-trading` = active (exited) + CGroup chứa java, `[LEGACY] managed 47` trở lại. Ingest tương tự (không ảnh hưởng vị thế).
Không bắt buộc cho mục tiêu "tự lên sau reboot".

### R3 rủi ro / rollback
- Rủi ro: (1) prestart hết 10 phút mà deps chưa ok ⇒ unit failed, app không lên ⇒ R4 báo; (2) `LANG=en_US.UTF-8` khác `C.UTF-8` của phiên hiện tại
  (C.UTF-8 không tồn tại trên CentOS 7 ⇒ thực chất đang là ASCII ở JVM con) — đổi theo hướng đúng hơn; (3) boot thật chưa thử (điểm owner).
- Rollback: `systemctl disable h242-ingest h242-trading; mv /etc/systemd/system/h242-{ingest,trading}.service $B/; systemctl daemon-reload`.

---
## R4 Healthcheck trên ORACLE (`research/ops/health_242.sh`, cron */5) — chỉ cảnh báo
- Một phiên ssh/lần, chỉ đọc trên 242: `pgrep -fc` trading/ingest (mẫu `-cp target/binance-java-sdk-1.2.4.jar <Main>`), tuổi dòng cuối
  `[LEGACY] managed`, `Update all position` (`v_t_m/logs/full.log`), `Chốt nến phút` (`collectData/logs/full.log`) từ `tail -c 3MB`
  (định dạng `dd/MM/yyyy HH:mm:ss`, giờ +07 của 242), `redis-cli CLUSTER INFO` (node đầu tiên trả lời), `systemctl is-active aerospike` +
  TCP `103.157.218.242:3222`, `df /`, `free`. Ngưỡng: tuổi log ≤ 180 s, disk < 92 %.
- Báo khi cùng tập lỗi lặp ≥ 2 lần liên tiếp (10 phút; tránh nhiễu cửa sổ auto-restart ~10–20 s), nhắc lại mỗi 30 phút, gửi `RECOVERED` khi hết.
  State `~/claude_master/health242/{state,health.log,last_status}`; flock chống chạy chồng.
- Kênh: Telegram nếu có `~/.config/health242/tg.env` (`TG_TOKEN=…`, `TG_CHAT=…`, chmod 600; token truyền qua `curl -K -` nên không lộ trên `ps`).
  Không có ⇒ ghi `~/claude_master/health242/ALERT_PENDING_NEED_OWNER_CHANNEL.txt` + `NO_CHANNEL` trong log (**cần owner cấp kênh**).
- Không tự restart ở bản đầu, vì: (1) 10-07 app start lại khi Redis rỗng ⇒ tạo lại 48 order `priceSL null` — restart tự động sẽ lặp lại đúng lỗi đó
  nếu nguyên nhân là Redis/Aerospike; (2) nguy cơ 2 JVM cùng quản vị thế thật nếu `pgrep` nhỡ đúng lúc `Utils.reset`; (3) restart từ Oracle cần
  quyền ghi lên 242 qua cron — mở rộng bề mặt rủi ro; (4) cần vài tuần dữ liệu cảnh báo để biết tỉ lệ báo nhầm trước khi cho hành động.
- Đã kiểm (2026-10-09 07:13–07:15, Oracle, chỉ đọc 242): `--dry-run` → `OK | trading_n=1 legacy_n=47 legacy_age=58 updpos_age=58 ingest_n=1
  kline_age=3 redis=ok aero=active/up disk=87% mem_avail=2788MB`; giả lập ssh hỏng (`HEALTH242_SSH=false`) 2 lần → lần 2 `NO_CHANNEL … FAIL:
  UNREACHABLE` ghi file pending; lần thật kế tiếp → `RECOVERED`; `HEALTH242_MAX_AGE=1` → `LEGACY_STALE UPDPOS_STALE KLINE_STALE`.

### R4 cài (Oracle)
```bash
mkdir -p /home/ubuntu/ops /home/ubuntu/.config/health242 && chmod 700 /home/ubuntu/.config/health242
cp -p /home/ubuntu/src/BinanceFuturesJava/research/ops/health_242.sh /home/ubuntu/ops/health_242.sh   # bản ghim, git pull không đổi ngầm
/home/ubuntu/ops/health_242.sh --dry-run                       # PASS: dòng "OK | …", problems='none'
# khi owner cấp kênh: tạo tg.env (KHÔNG in, KHÔNG commit), chmod 600; thử gửi:
HEALTH242_DIR=/home/ubuntu/claude_master/health242_test HEALTH242_MAX_AGE=1 HEALTH242_CONSEC=1 /home/ubuntu/ops/health_242.sh
cat /home/ubuntu/claude_master/health242_test/health.log      # PASS: "SENT http=200 … FAIL: LEGACY_STALE …" và owner nhận tin
( crontab -l; echo '*/5 * * * * /home/ubuntu/ops/health_242.sh >> /home/ubuntu/claude_master/health242/cron.out 2>&1' ) | crontab -
crontab -l | grep health_242                                    # 1 dòng
```
Rollback: xoá dòng cron (`crontab -l | grep -v health_242 | crontab -`). Rủi ro: thấp (1 ssh/5 phút; báo nhầm khi 242 chậm — CONSEC=2).

---
## R5 Cổng 8002 + 53 (0 phút dừng)
```bash
firewall-cmd --get-default-zone                                  # public
diff <(firewall-cmd --zone=public --list-all | sed 1d) <(firewall-cmd --permanent --zone=public --list-all | sed 1d)   # chỉ khác "interfaces: ens192"
ss -tulpn | grep -E ':(53|8002)\s' || echo NO_LISTENER           # PASS: NO_LISTENER (đóng không làm hỏng dịch vụ nào)
cp -p /etc/firewalld/zones/public.xml /etc/firewalld/zones/public.xml.bak_harden_$TS
firewall-cmd --permanent --zone=public --remove-port=8002/tcp
firewall-cmd --permanent --zone=public --remove-port=53/tcp
firewall-cmd --permanent --zone=public --remove-port=53/udp
firewall-cmd --reload
firewall-cmd --zone=public --list-ports                         # PASS: 1194/udp 80/tcp 443/tcp 2222/tcp
firewall-cmd --zone=public --list-rich-rules | grep -c 30001-30006   # PASS: 2 (rule redis Oracle + 242 còn nguyên)
```
Từ Oracle: `timeout 5 bash -c '</dev/tcp/103.157.218.242/8002'; echo rc=$?` → rc≠0 (*No route to host*/timeout); `…/30001` → rc=0;
ssh 2222 vẫn vào; `health_242.sh --dry-run` OK. 53: không rich rule cho 10.8.0.0/24 vì VPN push DNS 8.8.8.8/8.8.4.4 và không có DNS server.
- Rủi ro: `--reload` xoá chain iptables của docker (không container nào chạy ⇒ không ảnh hưởng; đã reload 10-07). Kết nối đang mở giữ nguyên.
- Rollback: `cp -p /etc/firewalld/zones/public.xml.bak_harden_$TS /etc/firewalld/zones/public.xml && firewall-cmd --reload`.
- Ngoài phạm vi được duyệt (chỉ ghi nhận): 80/443 mở mà không có listener; mongod enabled nghe `*:27017` (rich rule 192.168.10.0/24) — owner quyết.

---
## R6 Thứ tự tổng + kiểm cuối (KHÔNG reboot thật)

| # | Việc | Dừng app | Thời gian | Rủi ro | Điều kiện đi tiếp |
|---|------|----------|-----------|--------|-------------------|
| 1 | R4 dry-run baseline (Oracle) | 0 | 1' | không | `OK` |
| 2 | R5 đóng 8002/53 | 0 | 3' | thấp | list-ports đúng, redis từ Oracle ok |
| 3 | R1 enable aerospike + drop-in | 0 | 2' | thấp | enabled/active |
| 4 | R2.0–R2.1 snapshot, backup, config, unit redis | 0 | 10' | không | file đủ, unit inactive |
| 5 | R2.2–R2.4 rolling 6 node + enable | 0 (ghi chặn < 2 s ×3) | ~20' | trung bình (failover) | R2.4 PASS, app 47/47 |
| 6 | R2.5 mô phỏng restart/SIGKILL 1 replica | 0 | 3' | thấp | tự lên |
| 7 | R2.7 khoá script cũ | 0 | 1' | không | rc=1 |
| 8 | R3.1 thí nghiệm KillMode → R3.2–R3.3 enable unit app | 0 | 15' | thấp | PASS A, enabled |
| 9 | R4 cài cron (+ kênh nếu owner đã cấp) | 0 | 5' | thấp | `OK`, tin thử tới owner |

Không làm 4–8 trong cửa sổ cấm. Mỗi bước xong chạy `health_242.sh --dry-run` (Oracle).

### Checklist mô phỏng reboot (sau bước 9; mọi dòng phải PASS)
```bash
systemctl is-enabled aerospike redis-cluster@30001 redis-cluster@30002 redis-cluster@30003 redis-cluster@30004 redis-cluster@30005 redis-cluster@30006 h242-ingest h242-trading | sort | uniq -c   # 9 enabled
systemctl list-dependencies multi-user.target --no-pager | grep -E 'aerospike|redis-cluster@|h242-' | wc -l                  # 9
systemctl is-enabled NetworkManager-wait-online; systemctl show h242-trading -p After | grep -c redis-cluster@30006            # enabled / 1
for p in 30001 30002 30003 30004 30005 30006; do readlink /proc/$(pgrep -f "redis-server $H:$p")/cwd; done | sort -u     # chỉ /  (systemd) — KHÔNG còn $OLD
for p in 30001 30002 30003 30004 30005 30006; do $R -h $H -p $p CONFIG GET dir | sed -n 2p; done                           # /var/lib/redis-cluster/<p>
grep -h -c '127.0.0.1' $NEWR/*/nodes-*.conf | paste -sd' '                                                                 # 0 ×6
ls $NEWR/*/appendonlydir/*.manifest | wc -l                                                                                 # 6
/usr/local/sbin/h242-prestart.sh /home/chuyennd/java/v_t_m com.binance.chuyennd.trading.BinanceOrderTradingManager; echo rc=$?   # "dang chay", rc=1
ls /home/chuyennd/java/v_t_m/run/*.pid /home/chuyennd/java/collectData/run/*.pid                                            # còn nguyên pidfile
firewall-cmd --permanent --zone=public --list-ports                                                                         # 1194/udp 80/tcp 443/tcp 2222/tcp
bash /opt/redis_cluster_config.sh start; echo rc=$?                                                                         # DEPRECATED rc=1
```
Oracle: `crontab -l | grep health_242` (1 dòng), `tail -3 ~/claude_master/health242/health.log` (OK liên tục).
Kịch bản boot kỳ vọng: network-online → aerospike (~27 s cold start) ∥ 6 redis (nodes.conf + AOF từ dir tuyệt đối, cluster ok vài giây) →
prestart ingest/trading chờ 3222/3000 + `cluster_state:ok` → `daemon.sh start` → healthcheck thấy `[LEGACY] managed` trong ≤ 10 phút.
Boot thật để xác nhận: cần owner chọn cửa sổ (47 vị thế không quản lý ~2–4 phút trong lúc reboot).

### Rollback tổng (ngược thứ tự): R4 cron → R3 disable/mv unit → R2.7 khôi phục script → R2 (giữ nguyên systemd là trạng thái tốt; chỉ rollback
từng node theo R2.6 nếu node lỗi) → R1 disable → R5 khôi phục public.xml. Không xoá `$B`, `/opt/appendonlydir`, `$OLD/*` (lưu trữ).

## Điểm cần owner
1. Kênh cảnh báo: dùng lại bot/chat Telegram của `Utils.sendSms2Telegram` hay bot mới ⇒ cung cấp `TG_TOKEN`/`TG_CHAT` vào `~/.config/health242/tg.env` trên Oracle.
2. Token Telegram đang hardcode trong source repo (`Utils`, `P2PTelegramNotifier`) — nên xoay và chuyển ra config.
3. Cửa sổ reboot thật để nghiệm thu (sau R6).
4. Ngoài phạm vi: 80/443 mở không listener; mongod `*:27017` enabled; container docker cũ (tvcs) — giữ/xoá.
