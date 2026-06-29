"""
State provider-tax scraper runner.

Usage:
    python -m mfw.sources.state_scrapers.run [--states AL,OH,...] [--dry-run]

Iterates all registered state adapters, collects RateRows, writes:
  data/current/state_provider_taxes.csv  : one row per (state, provider_class)
  data/raw/scrape_log_<timestamp>.json   : per-state run log

One state failing NEVER crashes the run. Failed states are emitted with
confidence=failed and null rates so gaps are always visible.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

import pandas as pd

from ._base import RateRow, CONFIDENCE_FAILED, STRUCTURE_NONE, RATE_BASIS_NOT_COMPARABLE

# ── Adapter registry ──────────────────────────────────────────────────────────
# Only adapters for Phase 1 "verified" sources, plus compliance-risk stubs.
# Order does not matter; sorted alphabetically.

from ._al import AlabamaScraper
from ._az import ArizonaScraper
from ._ca import CaliforniaScraper
from ._ct import ConnecticutScraper
from ._dc import DCScraperScraper
from ._ga import GeorgiaScraper
from ._id import IdahoScraper
from ._il import IllinoisScraper
from ._in import IndianaScraper
from ._ks import KansasScraper
from ._ky import KentuckyScraper
from ._la import LouisianaScraper
from ._ma import MassachusettsScraper
from ._md import MarylandScraper
from ._me import MaineScraper
from ._mi import MichiganScraper
from ._mn import MinnesotaScraper
from ._mo import MissouriScraper
from ._mt import MontanaScraper
from ._nc import NorthCarolinaScraper
from ._nh import NewHampshireScraper
from ._nj import NewJerseyScraper
from ._nm import NewMexicoScraper
from ._nv import NevadaScraper
from ._ny import NewYorkScraper
from ._oh import OhioScraper
from ._ok import OklahomaScraper
from ._or import OregonScraper
from ._pa import PennsylvaniaScraper
from ._ri import RhodeIslandScraper
from ._va import VirginiaScraper
from ._vt import VermontScraper
from ._wa import WashingtonScraper
from ._wi import WisconsinScraper
from ._wv import WestVirginiaScraper

ALL_SCRAPERS = [
    AlabamaScraper,
    ArizonaScraper,
    CaliforniaScraper,
    ConnecticutScraper,
    DCScraperScraper,
    GeorgiaScraper,
    IdahoScraper,
    IllinoisScraper,
    IndianaScraper,
    KansasScraper,
    KentuckyScraper,
    LouisianaScraper,
    MassachusettsScraper,
    MarylandScraper,
    MaineScraper,
    MichiganScraper,
    MinnesotaScraper,
    MissouriScraper,
    MontanaScraper,
    NorthCarolinaScraper,
    NewHampshireScraper,
    NewJerseyScraper,
    NewMexicoScraper,
    NevadaScraper,
    NewYorkScraper,
    OhioScraper,
    OklahomaScraper,
    OregonScraper,
    PennsylvaniaScraper,
    RhodeIslandScraper,
    VirginiaScraper,
    VermontScraper,
    WashingtonScraper,
    WisconsinScraper,
    WestVirginiaScraper,
]

CURRENT_DIR = Path("data/current")
RAW_DIR = Path("data/raw")
OUTPUT_CSV = CURRENT_DIR / "state_provider_taxes.csv"
OUTPUT_COLUMNS = [
    "state", "abbr", "expansion", "provider_class", "structure",
    "effective_rate_pct", "native_rate", "rate_basis",
    "revenue_base_used", "source_url", "retrieved_date",
    "confidence", "waiver_flag", "notes",
]


def run_scrapers(
    scraper_classes: list = None,
    verbose: bool = True,
) -> tuple[pd.DataFrame, dict]:
    """
    Run all (or selected) scrapers. Returns (DataFrame, log_dict).

    Never raises: all failures are captured in the log and emitted as
    confidence=failed rows.
    """
    if scraper_classes is None:
        scraper_classes = ALL_SCRAPERS

    all_rows: list[dict] = []
    log: dict[str, dict] = {}
    stamp = time.strftime("%Y%m%dT%H%M%S")

    for cls in scraper_classes:
        scraper = cls()
        abbr = scraper.abbr
        state = scraper.state
        start = time.time()

        if verbose:
            print(f"  [{abbr}] {state}...", end=" ", flush=True)

        entry: dict = {
            "abbr": abbr,
            "state": state,
            "expansion": scraper.expansion,
            "start": stamp,
            "rows_extracted": 0,
            "method": "http_get+parse",
            "structures_found": [],
            "derivation_inputs": {},
            "error": None,
            "success": False,
        }

        try:
            rows: list[RateRow] = scraper.scrape()
            dicts = [r.to_dict() for r in rows]
            all_rows.extend(dicts)

            entry["rows_extracted"] = len(dicts)
            entry["structures_found"] = list({r["structure"] for r in dicts})
            entry["confidences"] = list({r["confidence"] for r in dicts})
            entry["has_waiver_flag"] = any(r.get("waiver_flag") for r in dicts)
            entry["success"] = True
            elapsed = round(time.time() - start, 2)
            entry["elapsed_s"] = elapsed

            if verbose:
                rates = [
                    f"{r['provider_class']}={r['effective_rate_pct'] or r['native_rate']}"
                    for r in dicts
                ]
                print(f"ok ({len(dicts)} rows, {elapsed}s): {'; '.join(rates[:3])}")

        except Exception as exc:
            elapsed = round(time.time() - start, 2)
            entry["error"] = traceback.format_exc()
            entry["elapsed_s"] = elapsed

            # Emit a failed sentinel row so the state never silently disappears
            failed = RateRow(
                state=state, abbr=abbr, expansion=scraper.expansion,
                provider_class="hospital",
                structure=STRUCTURE_NONE,
                effective_rate_pct=None,
                native_rate="unknown",
                rate_basis=RATE_BASIS_NOT_COMPARABLE,
                revenue_base_used=None,
                source_url=None,
                retrieved_date=time.strftime("%Y-%m-%d"),
                confidence=CONFIDENCE_FAILED,
                notes=f"Scrape failed: {exc}",
            )
            all_rows.append(failed.to_dict())

            if verbose:
                print(f"FAILED ({elapsed}s): {exc}")

        log[abbr] = entry

    # Build DataFrame
    if all_rows:
        df = pd.DataFrame(all_rows, columns=OUTPUT_COLUMNS)
    else:
        df = pd.DataFrame(columns=OUTPUT_COLUMNS)

    return df, log


def write_outputs(df: pd.DataFrame, log: dict, verbose: bool = True) -> None:
    CURRENT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    df.to_csv(OUTPUT_CSV, index=False)

    stamp = time.strftime("%Y%m%dT%H%M%S")
    log_path = RAW_DIR / f"scrape_log_{stamp}.json"
    log_path.write_text(json.dumps(log, indent=2, default=str))

    if verbose:
        n_ok = sum(1 for v in log.values() if v["success"])
        n_fail = len(log) - n_ok
        n_verified = (df["confidence"] == "verified").sum()
        n_likely = (df["confidence"] == "likely").sum()
        n_failed = (df["confidence"] == "failed").sum()
        n_not_comp = (df["rate_basis"] == "not_comparable").sum()
        n_waiver = df["waiver_flag"].notna().sum()
        print(f"\n── Scrape complete ─────────────────────────────────")
        print(f"  States attempted:    {len(log)}")
        print(f"  States succeeded:    {n_ok}")
        print(f"  States failed:       {n_fail}")
        print(f"  Rows written:        {len(df)}")
        print(f"  confidence=verified: {n_verified}")
        print(f"  confidence=likely:   {n_likely}")
        print(f"  confidence=failed:   {n_failed}")
        print(f"  not_comparable rows: {n_not_comp}")
        print(f"  waiver_flag rows:    {n_waiver}")
        print(f"  Output: {OUTPUT_CSV}")
        print(f"  Log:    {log_path}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run state provider-tax scrapers and write state_provider_taxes.csv"
    )
    parser.add_argument(
        "--states", default=None,
        help="Comma-separated list of state abbrs to run (default: all)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run scrapers but do not write output files"
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress per-state progress output"
    )
    args = parser.parse_args(argv)

    # Filter scrapers if --states provided
    selected = ALL_SCRAPERS
    if args.states:
        abbrs = {s.strip().upper() for s in args.states.split(",")}
        selected = [cls for cls in ALL_SCRAPERS if cls.abbr in abbrs]
        if not selected:
            print(f"No scrapers found for: {args.states}", file=sys.stderr)
            sys.exit(1)

    verbose = not args.quiet
    if verbose:
        print(f"Running {len(selected)} state scraper(s)…\n")

    df, log = run_scrapers(selected, verbose=verbose)

    if not args.dry_run:
        write_outputs(df, log, verbose=verbose)
    elif verbose:
        print(f"\n[dry-run] Would write {len(df)} rows to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
