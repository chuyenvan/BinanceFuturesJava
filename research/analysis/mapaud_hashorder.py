#!/usr/bin/env python3
"""MAPAUD: thu tu duyet java.util.HashMap<String,..> cho tung cap id trung -> symbol bi GHI DE trong ring
HistoryManager (processKline cung startTime => nen sau ghi de nen truoc). Symbol duyet TRUOC = bi ghi de (nan nhan).
Gia dinh: 2 key khac bucket (cung bucket: thu tu chen -> khong xac dinh tu day)."""
import json, sys
PAIRS = {843: ("MUUUSDT", "XBIUSDT"), 844: ("BNCUSDT", "SOXSUSDT"), 845: ("FWDIUSDT", "TZAUSDT"), 846: ("MINIMAXUSDT", "VRTUSDT"),
         847: ("SNOWUSDT", "ZHIPUUSDT"), 848: ("APPUSDT", "SHAZUSDT"), 849: ("GEVUSDT", "SOFIUSDT"), 850: ("PANWUSDT", "SKHYUSDT")}


def jhash(s):
    h = 0
    for ch in s:
        h = (31 * h + ord(ch)) & 0xFFFFFFFF
    return h


def idx(s, n):
    h = jhash(s)
    return (h ^ (h >> 16)) & (n - 1)


out = {}
for cap in (1024, 2048):
    r = {}
    for i, (a, b) in PAIRS.items():
        ia, ib = idx(a, cap), idx(b, cap)
        if ia == ib:
            r[i] = {"victim": None, "note": "cung bucket"}
        else:
            first, last = (a, b) if ia < ib else (b, a)
            r[i] = {"victim_features_from_twin": first, "kept": last}
    out[cap] = r
print(json.dumps(out, indent=1))
json.dump(out, open(sys.argv[1], "w"), indent=1)
