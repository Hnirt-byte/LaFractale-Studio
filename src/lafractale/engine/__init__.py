"""B3-B.1 engine slice: generic, deterministic, synthetic-only vertical slice.

Chain: strict JSON source -> activity -> independently verified solution ->
page composition -> PDF (fiche + corrigé) -> automated QA -> traceable package.

Scope guard: this package refuses every real book. The gates below are constants
of the code, never read from a source file, and nothing here approves anything.
"""
from __future__ import annotations

from types import MappingProxyType

#: Value of ``kind`` in every report and manifest produced by this package.
KIND = "SYNTHETIC_NON_PRODUCTION"
#: The only ``kind`` accepted in a source specification.
SPEC_KIND = "SYNTHETIC_TEST_FIXTURE"
READY_FOR_KDP = False
HUMAN_VALIDATIONS_RECORDED = 0
GATES = MappingProxyType({
    "MAJOR-03": "OPEN",
    "MAJOR-04": "OPEN",
    "EDITORIAL": "PENDING",
    "KDP": "FORBIDDEN",
    "PRODUCTION_GENERATION": "FORBIDDEN",
})


class EngineError(ValueError):
    """Any refusal of the engine slice (contract, generation, QA or output)."""


class ContractError(EngineError):
    """The source specification violates the B3-B.1 contract."""

    def __init__(self, errors: list[str] | str):
        self.errors = [errors] if isinstance(errors, str) else list(errors)
        super().__init__("; ".join(self.errors))
