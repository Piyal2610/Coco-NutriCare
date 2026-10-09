import csv
import math
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
MAX_DAY = 1856


@lru_cache(maxsize=None)
def load_table(gender):
    file_name = "wfa_boys.csv" if gender == "male" else "wfa_girls.csv"
    table = {}
    with open(DATA_DIR / file_name, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            table[int(row["Day"])] = (float(row["L"]), float(row["M"]), float(row["S"]))
    return table


def weight_z_score(gender, age_days, weight_kg):
    if age_days < 0 or age_days > MAX_DAY:
        return None
    L, M, S = load_table(gender)[age_days]
    if L == 0:
        return math.log(weight_kg / M) / S
    return ((weight_kg / M) ** L - 1) / (L * S)


def z_to_percentile(z):
    return 50 * (1 + math.erf(z / math.sqrt(2)))


def weight_percentile(gender, age_days, weight_kg):
    z = weight_z_score(gender, age_days, weight_kg)
    if z is None:
        return None
    return round(z_to_percentile(z), 1)


def growth_trend(previous_percentile, current_percentile):
    if previous_percentile is None or current_percentile is None:
        return None
    change = current_percentile - previous_percentile
    if change <= -10:
        return "slow"
    if change >= 10:
        return "fast"
    return "normal"


def update_growth_records(child):
    previous = None
    for record in child.growth_records:
        age_days = (record.date - child.date_of_birth).days
        record.percentile = weight_percentile(child.gender, age_days, record.weight_kg)
        record.trend = growth_trend(previous, record.percentile)
        previous = record.percentile    