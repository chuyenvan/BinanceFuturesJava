import zipfile, sys
jar = sys.argv[1] if len(sys.argv) > 1 else "/home/ubuntu/java/simulator/binance-exit003-20260730.jar"
z = zipfile.ZipFile(jar)
b1 = z.read("com/binance/chuyennd/tradecore/Configs.class")
b2 = z.read("com/binance/chuyennd/research/OrderTargetInfoTest.class")
print("jar =", jar)
print("Configs.class chua TS_RATCHET_DECOUPLED:", b"TS_RATCHET_DECOUPLED" in b1)
print("OrderTargetInfoTest.class chua TS_RATCHET_DECOUPLED:", b"TS_RATCHET_DECOUPLED" in b2)
