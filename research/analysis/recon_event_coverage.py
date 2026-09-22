#!/usr/bin/env python3
import csv, datetime

BD_PATH = "/home/ubuntu/claudedata/universe_birth_death.csv"
T170_PATH = "/home/ubuntu/java/devrun/X1_GS_T170_2021/storage/printDone.csv"

DEV_START = "2021-07"
DEV_END = "2025-12"

def ym(s):
    return s  # already YYYY-MM

rows = []
with open(BD_PATH) as f:
    r = csv.DictReader(f)
    for row in r:
        rows.append(row)

print(f"Total symbols in universe_birth_death.csv: {len(rows)}")

# global last_month seen (to detect "still alive" vs "true delisted")
all_last = [row['last_month'] for row in rows]
max_last_month = max(all_last)
print(f"Max last_month observed across all symbols (dataset horizon): {max_last_month}")

# births within DEV window
births_dev = [row for row in rows if DEV_START <= row['first_month'] <= DEV_END]
print(f"\nSymbols with first_month (birth) inside DEV window [{DEV_START},{DEV_END}]: {len(births_dev)} / {len(rows)} ({100*len(births_dev)/len(rows):.1f}%)")

# births by year
from collections import Counter
birth_year = Counter(row['first_month'][:4] for row in rows)
for y in sorted(birth_year):
    print(f"  birth year {y}: {birth_year[y]}")

# deaths that look "real" (last_month meaningfully before dataset horizon, i.e. not still-alive)
# heuristic: last_month < max_last_month by at least 2 months AND last_month within DEV window
def month_diff(a, b):
    ya, ma = map(int, a.split('-'))
    yb, mb = map(int, b.split('-'))
    return (yb - ya) * 12 + (mb - ma)

true_deaths = [row for row in rows if month_diff(row['last_month'], max_last_month) >= 2]
print(f"\nSymbols with 'true delisting' signal (last_month >=2 months before dataset horizon {max_last_month}): {len(true_deaths)} / {len(rows)} ({100*len(true_deaths)/len(rows):.1f}%)")
deaths_dev = [row for row in true_deaths if DEV_START <= row['last_month'] <= DEV_END]
print(f"  of which last_month inside DEV window: {len(deaths_dev)}")
death_year = Counter(row['last_month'][:4] for row in true_deaths)
for y in sorted(death_year):
    print(f"  death year {y}: {death_year[y]}")

# Coverage density: total distinct (symbol, month) pairs of "birth event" and "death event" in DEV window
# vs total distinct (symbol, month) pairs of ANY trading activity in DEV window (approx via birth<=month<=last)
total_symbol_months = 0
for row in rows:
    if row['first_month'] > DEV_END or row['last_month'] < DEV_START:
        continue
    fm = max(row['first_month'], DEV_START)
    lm = min(row['last_month'], DEV_END)
    total_symbol_months += month_diff(fm, lm) + 1

n_birth_events = len(births_dev)
n_death_events = len(deaths_dev)
print(f"\nApprox total symbol-months of ANY trading activity in DEV window: {total_symbol_months}")
print(f"Birth events in DEV window: {n_birth_events} ({100*n_birth_events/total_symbol_months:.2f}% of symbol-months)")
print(f"Death events in DEV window: {n_death_events} ({100*n_death_events/total_symbol_months:.2f}% of symbol-months)")

# ---- Overlap with T170 entries ----
t170_entries = []  # (sym, YYYY-MM)
with open(T170_PATH) as f:
    r = csv.DictReader(f)
    for row in r:
        try:
            ts = row['start']  # e.g. 20251201 07:09
            date_part = ts.split(' ')[0]
            y = date_part[0:4]
            m = date_part[4:6]
            sym = row['sym']
            t170_entries.append((sym, f"{y}-{m}"))
        except Exception as e:
            pass

print(f"\nT170 total entries parsed: {len(t170_entries)}")
t170_symbol_months = set(t170_entries)
print(f"T170 distinct (symbol, month) pairs: {len(t170_symbol_months)}")

birth_symbol_months = set((row['symbol'], row['first_month']) for row in births_dev)
death_symbol_months = set((row['symbol'], row['last_month']) for row in deaths_dev)

overlap_birth = t170_symbol_months & birth_symbol_months
overlap_death = t170_symbol_months & death_symbol_months
print(f"\nOverlap T170-entry-month vs birth-month (same symbol, same month): {len(overlap_birth)} pairs")
print(f"Overlap T170-entry-month vs death-month (same symbol, same month): {len(overlap_death)} pairs")
print(f"  as % of T170 distinct (sym,month) pairs: birth {100*len(overlap_birth)/len(t170_symbol_months):.2f}%, death {100*len(overlap_death)/len(t170_symbol_months):.2f}%")
print(f"  as % of birth events: {100*len(overlap_birth)/max(1,len(birth_symbol_months)):.2f}%")
print(f"  as % of death events: {100*len(overlap_death)/max(1,len(death_symbol_months)):.2f}%")

# how many T170 trade DAYS overall (distinct days with >=1 entry) -- for reference to 1644-day denominator used elsewhere
t170_days = set()
with open(T170_PATH) as f:
    r = csv.DictReader(f)
    for row in r:
        ts = row['start']
        date_part = ts.split(' ')[0]
        t170_days.add(date_part)
print(f"\nT170 distinct entry days: {len(t170_days)}")
