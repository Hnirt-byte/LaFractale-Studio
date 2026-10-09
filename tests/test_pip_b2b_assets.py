"""Three B2-B regression tests for the approved Halloween-only Pip art.

No changes to the B2-A engine, PNG images or protected registry are required.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json

import pytest

from lafractale.config.schema import load_book
from lafractale.export.builder import audit_output, build_demo
from lafractale.illustrations.registry import IllustrationError, load_approved_artwork, _strict_png

ROOT = Path(__file__).resolve().parents[1]
PIN = "93c58e86a74e903af1be5cd4257d489c39bece8f5cd41d985586cbf775d45e61"
ASSETS = {
    "pip-reference-nb-v1": "8bf579336b405e2a9de0dc1fdbd7bbc281fd80dfa8d236d4108f8b1a6d9719b1",
    "pip-accueil-v1": "72716b4193b6f15e5ffb55340f6d3ddfa428282e804b44ff410f01354bf52a09",
    "pip-encouragement-v1": "1bd15c92f77825160258e962f08b1bfcc593e9de99f229e73469d1c295051597",
    "pip-indication-v1": "a3bec36fdec734d0791e5c76da99f1273eda43586310fdba795f6fc1a8089a81",
    "pip-reflexion-v2": "37107eb5c2a7331232303a0c0ae0347e3766faacc00e0abc779c78409c47ba48",
    "pip-felicitations-v2": "74030cb477e121addd94bcb1d5d4dcb8193b7cb123695e7a546ef9a733dba098",
}


def _trusted_registry():
    path = ROOT / "assets/illustrations/approvals.json"
    raw = path.read_bytes()
    assert sha256(raw).hexdigest() == PIN
    return json.loads(raw)


def test_b2b_six_approved_pngs_match_registry_and_pins():
    data = _trusted_registry()
    assert data["schema_version"] == 1
    assert len(data["illustrations"]) == 6
    assert {entry["id"] for entry in data["illustrations"]} == set(ASSETS)
    for entry in data["illustrations"]:
        asset_id = entry["id"]
        rel = f"assets/illustrations/halloween_2026/pip/{asset_id}.png"
        assert entry["path"] == rel
        assert entry["book_id"] == "halloween_2026"
        assert entry["companion_id"] == "pip"
        assert entry["human_approved"] is True
        assert entry["sha256"] == ASSETS[asset_id]
        image = (ROOT / rel).read_bytes()
        assert sha256(image).hexdigest() == ASSETS[asset_id]
        assert _strict_png(image) == (1254, 1254)
    assert sha256((ROOT / "assets/characters/pip/pip_officiel_couleur.png").read_bytes()).hexdigest() == (
        "b54194f0cf3be821d38d08e2c7b9b177292b90175faa2180ccb34cdccd8e295c"
    )
    # Documented approval must describe the same immutable, external-pinned registry.
    inventory = json.loads((ROOT / "docs/illustrations/pip/INVENTAIRE_SHA256.json").read_text(encoding="utf-8"))
    assert inventory["production_registry_sha256"] == PIN
    assert inventory["production_registry_path"] == "assets/illustrations/approvals.json"
    assert inventory["integration_scope"] == "technical_B2B_only"
    assert len(inventory["variants"]) == 6
    indexed = {variant["id"]: variant for variant in inventory["variants"]}
    assert set(indexed) == set(ASSETS)
    for asset_id, digest in ASSETS.items():
        assert indexed[asset_id]["candidate_sha256"] == digest
        assert indexed[asset_id]["converted_file_approval"] == "approved_for_B2B_technical_integration"
        assert indexed[asset_id]["integration_approved"] is True


def test_b2b_all_six_opt_in_halloween_with_trusted_audit(tmp_path, monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1780000000")
    book = load_book(ROOT / "books/halloween_2026/book.yaml")
    for asset_id in ASSETS:
        artwork = load_approved_artwork(book, asset_id, trusted_approvals_sha256=PIN)
        assert artwork.sha256 == ASSETS[asset_id]
    # Smoke one real illustrated PDF build; the six registry identities are checked above.
    asset_id = "pip-reflexion-v2"
    out = tmp_path / asset_id
    build_demo(book, out, illustration_id=asset_id, trusted_approvals_sha256=PIN)
    assert audit_output(out, book=book, illustration_id=asset_id, trusted_approvals_sha256=PIN) == []
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["publication_approved"] is False
    assert manifest["illustration"]["id"] == asset_id


def test_b2b_noel_rejects_every_pip_variant():
    book = load_book(ROOT / "books/christmas_2026/book.yaml")
    for asset_id in ASSETS:
        with pytest.raises(IllustrationError):
            load_approved_artwork(book, asset_id, trusted_approvals_sha256=PIN)
