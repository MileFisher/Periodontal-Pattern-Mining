"""Phase 1: download NHANES 2009-2014, merge per participant, select the cohort.

Run from the repo root:  python -m src.load
"""
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"

CYCLES = {"F": 2009, "G": 2011, "H": 2013}
TABLES = ["DEMO", "OHXPER", "OHXDEN", "GHB", "DIQ", "SMQ", "BMX"]
URL = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{yr}/DataFiles/{t}_{s}.xpt"

# The 28 teeth NHANES probes (third molars 01, 16, 17, 32 are excluded).
TEETH = [f"{n:02d}" for n in [*range(2, 16), *range(18, 32)]]


def download(force: bool = False) -> None:
    """Fetch any of the 21 raw files missing from data/raw/."""
    RAW.mkdir(parents=True, exist_ok=True)
    for s, yr in CYCLES.items():
        for t in TABLES:
            path = RAW / f"{t}_{s}.xpt"
            if path.exists() and not force:
                continue
            r = requests.get(URL.format(yr=yr, t=t, s=s), timeout=120)
            r.raise_for_status()
            if not r.content.startswith(b"HEADER RECORD"):
                raise ValueError(f"{path.name}: response is not a SAS transport file")
            path.write_bytes(r.content)
            print(f"downloaded {path.name}")


def read_table(t: str, s: str) -> pd.DataFrame:
    df = pd.read_sas(RAW / f"{t}_{s}.xpt", format="xport", encoding="infer")
    # read_sas returns stored zeros as ~5.4e-79; snap them back to 0.
    num = df.select_dtypes("number").columns
    df[num] = df[num].mask(df[num].abs() < 1e-10, 0.0)
    return df.set_index("SEQN")


def load_cycle(s: str) -> pd.DataFrame:
    """One cycle, one row per participant, DEMO as the spine (left joins)."""
    demo = read_table("DEMO", s)
    parts, seen = [demo], set(demo.columns)
    for t in TABLES[1:]:
        part = read_table(t, s)
        # OHDEXSTS is in both OHXPER and OHXDEN; keep the first copy.
        part = part.drop(columns=[c for c in part.columns if c in seen])
        seen.update(part.columns)
        parts.append(part.reindex(demo.index))
    parts.append(pd.DataFrame({"cycle": CYCLES[s]}, index=demo.index))
    return pd.concat(parts, axis=1)


def merge() -> pd.DataFrame:
    raw = pd.concat([load_cycle(s) for s in CYCLES])
    raw.index = raw.index.astype("int64")
    weight = (raw["WTMEC2YR"] / 3).rename("WT6YR")  # NHANES rule for pooling 3 cycles
    return pd.concat([raw, weight], axis=1)


def n_natural_teeth(raw: pd.DataFrame) -> pd.Series:
    """Natural teeth among the 28 probed teeth: OHXDEN code 2 (permanent) or 5 (root fragment)."""
    tc = raw[[f"OHX{t}TC" for t in TEETH]].round()
    return tc.isin([2, 5]).sum(axis=1)


def n_assessed_sites(raw: pd.DataFrame) -> pd.Series:
    """Sites with an attachment-loss reading; 99 means "cannot assess"."""
    la = raw[[f"OHX{t}LA{s}" for t in TEETH for s in "DMSPLA"]]
    return la.lt(99).sum(axis=1)


def select_cohort(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply the cohort filters in order; return the cohort and the flow counts."""
    steps = [
        ("NHANES 2009-2014 participants", pd.Series(True, index=raw.index)),
        ("aged 30-79", raw["RIDAGEYR"].between(30, 79)),
        ("complete periodontal exam (OHDPDSTS == 1)", raw["OHDPDSTS"].round() == 1),
        # Edentulous people still get OHDPDSTS == 1 (nothing to probe).
        ("dentate (>= 1 natural tooth or root)", n_natural_teeth(raw) >= 1),
        (">= 1 assessable periodontal site", n_assessed_sites(raw) >= 1),
    ]
    keep = pd.Series(True, index=raw.index)
    rows = []
    for name, mask in steps:
        before = int(keep.sum())
        keep &= mask.fillna(False)
        rows.append({"step": name, "remaining": int(keep.sum()), "excluded": before - int(keep.sum())})
        for s, yr in CYCLES.items():
            rows[-1][f"remaining_{yr}"] = int((keep & (raw["cycle"] == yr)).sum())
    return raw[keep].copy(), pd.DataFrame(rows)


def main() -> None:
    download()
    raw = merge()
    INTERIM.mkdir(parents=True, exist_ok=True)
    raw.to_parquet(INTERIM / "nhanes_0914.parquet")
    cohort, flow = select_cohort(raw)
    cohort.to_parquet(INTERIM / "cohort.parquet")
    flow.to_csv(INTERIM / "cohort_flow.csv", index=False)
    print(f"merged: {raw.shape}, cohort: {cohort.shape}")
    print(flow.to_string(index=False))


if __name__ == "__main__":
    main()
