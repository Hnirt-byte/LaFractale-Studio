"""End-to-end B2-C1 routed rendering, inventory and independent QA."""
from __future__ import annotations

import hashlib
import json
from io import BytesIO
from pathlib import Path

import fitz
import pytest

from PIL import Image

from lafractale.config.schema import load_book
from lafractale.export.builder import audit_output, build_demo
from lafractale.illustrations.registry import IllustrationError
from lafractale.illustrations.routing import (
    ROUTING_HALLOWEEN_PIP_DEMO_V1,
    build_illustration_route,
)


ROOT = Path(__file__).resolve().parents[1]
HALLOWEEN = ROOT / "books/halloween_2026/book.yaml"
CHRISTMAS = ROOT / "books/christmas_2026/book.yaml"
PIN = "93c58e86a74e903af1be5cd4257d489c39bece8f5cd41d985586cbf775d45e61"
ROUTED_PREVIEWS = {
    "interior_page_01.png", "interior_page_02.png", "interior_page_03.png",
    "answer_key_page_01.png", "answer_key_page_02.png", "answer_key_page_03.png",
}


def _page_pixel_hashes(pdf_path: Path) -> list[str]:
    hashes: list[str] = []
    with fitz.open(pdf_path) as pdf:
        assert len(pdf) == 3
        for page in pdf:
            images = page.get_image_info(xrefs=True)
            assert len(images) == 1
            pix = fitz.Pixmap(pdf, images[0]["xref"])
            hashes.append(hashlib.sha256(pix.samples).hexdigest())
    return hashes


def test_routed_halloween_produces_six_bound_previews_and_passes_qa(tmp_path):
    book = load_book(HALLOWEEN)
    route = build_illustration_route(
        book, policy_id=ROUTING_HALLOWEEN_PIP_DEMO_V1, trusted_approvals_sha256=PIN,
    )
    out = tmp_path / "routed"
    build_demo(
        book, out, illustration_routing=ROUTING_HALLOWEEN_PIP_DEMO_V1,
        trusted_approvals_sha256=PIN,
    )
    assert audit_output(
        out, book=book, illustration_routing=ROUTING_HALLOWEEN_PIP_DEMO_V1,
        trusted_approvals_sha256=PIN,
    ) == []
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert "illustration" not in manifest
    assert manifest["illustration_routing"] == route.manifest_entry()
    assert {path.name for path in (out / "previews").iterdir()} == ROUTED_PREVIEWS
    expected = []
    for binding in route.bindings:
        with Image.open(BytesIO(binding.artwork.pixels)) as image:
            image.load()
            expected.append(hashlib.sha256(image.tobytes()).hexdigest())
    assert _page_pixel_hashes(out / "interior.pdf") == expected
    assert _page_pixel_hashes(out / "answer_key.pdf") == expected


def test_routed_audit_rejects_an_approved_pose_swapped_only_in_answer_key(tmp_path):
    book = load_book(HALLOWEEN)
    out = tmp_path / "routed"
    build_demo(
        book, out, illustration_routing=ROUTING_HALLOWEEN_PIP_DEMO_V1,
        trusted_approvals_sha256=PIN,
    )
    answer_key = out / "answer_key.pdf"
    with fitz.open(answer_key) as document:
        first = document[0].get_image_info(xrefs=True)[0]["xref"]
        second = document[1].get_image_info(xrefs=True)[0]["xref"]
        document.update_stream(first, document.xref_stream(second), compress=True)
        altered = document.tobytes(garbage=3, deflate=True)
    answer_key.write_bytes(altered)
    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["outputs"]["answer_key.pdf"] = hashlib.sha256(altered).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    errors = audit_output(
        out, book=book, illustration_routing=ROUTING_HALLOWEEN_PIP_DEMO_V1,
        trusted_approvals_sha256=PIN,
    )
    assert any("pixels graphiques différents" in error for error in errors), errors


def test_routed_mode_is_deterministic_with_fixed_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1780000000")
    book = load_book(HALLOWEEN)
    kwargs = {
        "illustration_routing": ROUTING_HALLOWEEN_PIP_DEMO_V1,
        "trusted_approvals_sha256": PIN,
    }
    first, second = tmp_path / "first", tmp_path / "second"
    build_demo(book, first, **kwargs)
    build_demo(book, second, **kwargs)
    def digest_tree(root):
        return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in root.rglob("*") if path.is_file()}
    assert digest_tree(first) == digest_tree(second)


@pytest.mark.parametrize(
    ("book_path", "illustration_id", "routing", "pin"),
    [
        (HALLOWEEN, "pip-reflexion-v2", ROUTING_HALLOWEEN_PIP_DEMO_V1, PIN),
        (HALLOWEEN, None, ROUTING_HALLOWEEN_PIP_DEMO_V1, None),
        (HALLOWEEN, None, None, PIN),
        (CHRISTMAS, None, ROUTING_HALLOWEEN_PIP_DEMO_V1, PIN),
    ],
)
def test_routed_mode_rejects_ambiguous_partial_or_christmas_requests(
    tmp_path, book_path, illustration_id, routing, pin,
):
    with pytest.raises(IllustrationError):
        build_demo(
            load_book(book_path), tmp_path / "reject", illustration_id=illustration_id,
            illustration_routing=routing, trusted_approvals_sha256=pin,
        )
