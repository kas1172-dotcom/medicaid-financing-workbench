"""
Source adapters — three-tier ingestion system.

Tier 1 (api):           auto-fetched, no user action required.
Tier 2 (manual_upload): user drops file in data/inbox/.
Tier 3 (pdf):           user drops PDF in data/inbox/; extracted by pdfplumber.

Each adapter implements SourceAdapter from .base.
"""
