"""B3-B.3b — mechanics v2: parameterised, verified, SYNTHETIC puzzle generators.

Strictly separate from the editorial data: nothing here reads a CSV, a ``PageRecord`` or a
validation status, and nothing here renders, writes or authorises production. The historical
generators (``lafractale.activities``), the synthetic B3-B.1 contract and the C4 profile are
untouched; no historical module imports this package.
"""
from __future__ import annotations

V2_KIND = "SYNTHETIC_NON_PRODUCTION"
V2_SCHEMA = "lafractale-mechanics-v2-activity-v1"
#: Constant of the code, never read from anywhere: v2 outputs authorise nothing.
PRODUCTION_AUTHORIZED = False
HUMAN_PEDAGOGICAL_VALIDATION = "NONE"
