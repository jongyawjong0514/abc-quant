# Yahoo Concept Snapshots

This directory contains immutable reference exports created by
`scripts/sync_yahoo_concept_membership.py` from Yahoo Taiwan's concept-stock
class page and paginated class-quotes resource.

Each snapshot directory is keyed by Yahoo's source data date plus a content
hash. The manifest records the full SHA-256, fetch timestamp, row counts, and
`IMPORTANT_BASELINE` designation. Historical use before the snapshot date must
remain tagged `static_current_backfill_user_authorized`; it is not historical
point-in-time membership and is not formal promotion evidence.

These files support research reproducibility only. They do not create orders,
positions, portfolio weights, or formal strategy changes.
