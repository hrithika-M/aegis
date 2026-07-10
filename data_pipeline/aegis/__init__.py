"""Aegis — a general self-healing data engine.

Point it at any data source (file path or database credentials); it learns what
"normal" looks like (median/MAD), detects anomalies (BLACKOUT/SPIKE/LOW/DRIFT),
repairs them scaled to the day's real activity, reconciles doubtful values from
related tables + ground-truth references, and iterates — confidence-gated —
until the data-trust score converges. Honest by design: what it cannot fix
confidently is escalated, never fabricated.

Design lineage (docs/AEGIS_RESEARCH_AND_PLAN.md): HoloClean's signal-unification,
Soda's config/connector pattern, MICE cross-column imputation, and the 2026
self-healing confidence-gate rule — plus our POD-validated detector/repair core.

Standalone: aegis does NOT depend on the POD project or on data_trust.
"""
__version__ = '0.1.0'
