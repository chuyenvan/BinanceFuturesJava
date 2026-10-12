# LIVEFIX2 deploy — bien chung (source tren Oracle). KHONG chua bi mat.
LF=/home/ubuntu/claude_master/1011/livefix
DEP=$LF/deploy
JAR=$LF/jar/binance-java-sdk-1.2.4.jar
JAR_SHA=db181d41bd6837752638a63de99a2023cee7ad4b897d6e64924ac3d6c8f21577   # commit d44202d6 (fix/live-1011)
OLD_SHA=b0f23b7d                                  # jar dang chay 242 + 2 shadow (prefix)
WT=/home/ubuntu/claude_master/1011/livefix_wt
G=/home/ubuntu/kfix_gate                          # thu muc dung buffer gate (KLINE_FIX muc C)
K242=/home/ubuntu/.ssh/id_rsa_chuyennd
S242="ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i $K242 root@103.157.218.242"
SCP242="scp -P 2222 -o BatchMode=yes -i $K242"
LOGD=$DEP/logs; mkdir -p $LOGD
TOOL="com.binance.chuyennd.aerospike.tools.SymbolMapperRepairTool"
