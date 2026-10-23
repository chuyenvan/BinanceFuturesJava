#!/usr/bin/env python3
"""Tao ban OFFLINE cua V11FeatHarness / V11MdHarness tu ban goc (~/claude_master/v11_settle/harness/src) — patch toi thieu,
co kiem moi cho thay the dung 1 lan (khong im lang). argv: src_dir out_dir"""
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("patch")
src, out = sys.argv[1], sys.argv[2]
P = "com/binance/chuyennd/aerospike/"


def sub1(txt, old, new, tag):
    n = txt.count(old)
    if n != 1:
        raise SystemExit("patch %s: tim thay %d lan (can dung 1)" % (tag, n))
    return txt.replace(old, new)


t = open(os.path.join(src, P + "V11FeatHarness.java")).read()
t = sub1(t, " * args: mode restartMs firstMinute lastMinute out.csv.gz\n */",
         " * args: mode restartMs firstMinute lastMinute out.csv.gz\n"
         " * HARNESS_OFFLINE=1 (research/parity_v11, PREREG_PARITY_V11_WINDOW §1): chi doc cache file cuc bo + provider file,\n"
         " * chan cung Aerospike/mang (OfflineGuard + stub AerospikeClient). Thieu cache => dung, KHONG doc Aerospike.\n */", "doc")
t = sub1(t, "            return;\n        }\n        long t = from;",
         "            return;\n        }\n"
         "        if (OfflineGuard.enabled()) throw new IllegalStateException(\"HARNESS_OFFLINE: thieu cache \" + cf.getAbsolutePath());\n"
         "        long t = from;", "load")
t = sub1(t, "        g.set(null, Boolean.FALSE);   // CHI DOC: chan moi ghi 242 (mapper, ai_pred...)\n",
         "        g.set(null, Boolean.FALSE);   // CHI DOC: chan moi ghi 242 (mapper, ai_pred...)\n"
         "        OfflineGuard.install();       // HARNESS_OFFLINE=1: provider file + chan mang (khong bat => nhu cu)\n", "install")
t = sub1(t, "        LOG.info(\"{}\", \"done \" + mode);\n        System.exit(0);",
         "        OfflineGuard.finish();\n        LOG.info(\"{}\", \"done \" + mode);\n        System.exit(0);", "finish")
os.makedirs(os.path.join(out, P), exist_ok=True)
open(os.path.join(out, P + "V11FeatHarness.java"), "w").write(t)

m = open(os.path.join(src, P + "V11MdHarness.java")).read()
m = sub1(m, "        g.set(null, Boolean.FALSE);\n",
         "        g.set(null, Boolean.FALSE);\n"
         "        OfflineGuard.install();\n"
         "        TreeMap<Long, Map<String, KlineObjectSimple>> off = null;\n"
         "        if (OfflineGuard.enabled()) {   // HARNESS_OFFLINE=1: kline tu cache file (HARNESS_CACHE_FILE), khong Aerospike\n"
         "            try (java.io.ObjectInputStream in = new java.io.ObjectInputStream(new java.util.zip.GZIPInputStream(\n"
         "                    new java.io.FileInputStream(System.getenv(\"HARNESS_CACHE_FILE\"))))) {\n"
         "                @SuppressWarnings(\"unchecked\") TreeMap<Long, Map<String, KlineObjectSimple>> x =\n"
         "                        (TreeMap<Long, Map<String, KlineObjectSimple>>) in.readObject();\n"
         "                off = x;\n"
         "            }\n"
         "            LOG.info(\"offline cache minutes={}\", off.size());\n"
         "        }\n", "md-install")
m = sub1(m, "                TreeMap<Long, Map<String, KlineObjectSimple>> r = DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(t, cnt);",
         "                TreeMap<Long, Map<String, KlineObjectSimple>> r = off != null\n"
         "                        ? new TreeMap<>(off.subMap(t, true, t + (cnt - 1) * MIN, true))\n"
         "                        : DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(t, cnt);", "md-read")
m = sub1(m, "        LOG.info(\"MD done minutes={} miss={}\", n, nMiss);\n",
         "        OfflineGuard.finish();\n        LOG.info(\"MD done minutes={} miss={}\", n, nMiss);\n", "md-finish")
open(os.path.join(out, P + "V11MdHarness.java"), "w").write(m)
log.info("patched -> %s", out)
