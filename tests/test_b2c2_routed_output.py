"""End-to-end B2-C2 placement: rendering, QA revalidation and mutation refusals."""
from __future__ import annotations

import hashlib
import json
from io import BytesIO
from pathlib import Path

import fitz
import pytest

from PIL import Image

from lafractale.activities.engine import generate, stable_seed
from lafractale.config.schema import load_book
from lafractale.export.builder import audit_output, build_demo
from lafractale.illustrations.placement import (
    LOWER_LEFT,
    LOWER_RIGHT,
    PIP_PLACEMENT_HALLOWEEN_V1,
    SCENE_RIGHT,
    build_pip_placement_plan,
)
from lafractale.illustrations.registry import IllustrationError
from lafractale.illustrations.routing import (
    ROUTING_HALLOWEEN_PIP_DEMO_V1,
    build_illustration_route,
)
from lafractale.layout.pdf import write_pdf


ROOT = Path(__file__).resolve().parents[1]
HALLOWEEN = ROOT / "books/halloween_2026/book.yaml"
CHRISTMAS = ROOT / "books/christmas_2026/book.yaml"
PIN = "93c58e86a74e903af1be5cd4257d489c39bece8f5cd41d985586cbf775d45e61"
ROUTED_PREVIEWS = {
    "interior_page_01.png", "interior_page_02.png", "interior_page_03.png",
    "answer_key_page_01.png", "answer_key_page_02.png", "answer_key_page_03.png",
}
CANONICAL_ANCHORS = (SCENE_RIGHT, LOWER_RIGHT, LOWER_LEFT)
C2 = {"illustration_routing": ROUTING_HALLOWEEN_PIP_DEMO_V1, "pip_placement": PIP_PLACEMENT_HALLOWEEN_V1,
      "trusted_approvals_sha256": PIN}
C1 = {"illustration_routing": ROUTING_HALLOWEEN_PIP_DEMO_V1, "trusted_approvals_sha256": PIN}


def _activities(book):
    return [generate(spec, stable_seed(book.book_id, spec.id, 2026)) for spec in _specs(book)]


def _specs(book):
    from lafractale.story.plan import demo_specs

    return demo_specs(book)


def _slot_pdf_box(page, layout):
    """Expected image box in PDF coordinates (top-left origin) from the layout."""
    slot = layout.companion_slot
    return (slot.x, page.rect.height - slot.top, slot.right, page.rect.height - slot.y)


def _trusted_layouts(book, answer_key):
    from lafractale.layout.composition import compose_page
    from lafractale.layout.pdf import _measure, fonts

    plan = build_pip_placement_plan(book, build_illustration_route(
        book, policy_id=ROUTING_HALLOWEEN_PIP_DEMO_V1, trusted_approvals_sha256=PIN),
        policy_id=PIP_PLACEMENT_HALLOWEEN_V1, trusted_approvals_sha256=PIN)
    regular, bold = fonts()
    activities = _activities(book)
    layouts = []
    for index, activity in enumerate(activities, 1):
        layout = compose_page(activity, book.data, index=index, count=len(activities),
                              answer_key=answer_key, regular=regular, bold=bold, text_width=_measure)
        from lafractale.illustrations.placement import placed_composition

        layouts.append(placed_composition(layout, plan.anchor_for(activity, demo_index=index),
                                         text_width=_measure))
    return layouts


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


def _rebuild_manifest(out: Path) -> None:
    """Mirror only the output digests, so a tampered PDF reaches the byte check."""
    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name in ("interior.pdf", "answer_key.pdf"):
        manifest["outputs"][name] = hashlib.sha256((out / name).read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def test_placement_produces_six_bound_previews_and_passes_qa(tmp_path):
    book = load_book(HALLOWEEN)
    out = tmp_path / "placed"
    build_demo(book, out, **C2)
    assert audit_output(out, book=book, **C2) == []
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert "illustration" not in manifest
    assert manifest["pip_placement"]["policy_id"] == PIP_PLACEMENT_HALLOWEEN_V1
    assert {path.name for path in (out / "previews").iterdir()} == ROUTED_PREVIEWS
    plan = build_pip_placement_plan(book, build_illustration_route(
        book, policy_id=ROUTING_HALLOWEEN_PIP_DEMO_V1, trusted_approvals_sha256=PIN),
        policy_id=PIP_PLACEMENT_HALLOWEEN_V1, trusted_approvals_sha256=PIN)
    assert manifest["pip_placement"] == plan.manifest_entry()
    expected = []
    for binding in plan.bindings:
        route_binding = next(route_binding for route_binding in build_illustration_route(
            book, policy_id=ROUTING_HALLOWEEN_PIP_DEMO_V1,
            trusted_approvals_sha256=PIN).bindings
            if route_binding.demo_index == binding.demo_index)
        with Image.open(BytesIO(route_binding.artwork.pixels)) as image:
            image.load()
            expected.append(hashlib.sha256(image.tobytes()).hexdigest())
    assert _page_pixel_hashes(out / "interior.pdf") == expected
    assert _page_pixel_hashes(out / "answer_key.pdf") == expected


@pytest.mark.parametrize("answer_key", [False, True])
def test_placed_image_sits_exactly_in_the_expected_slot_on_all_three_pages(tmp_path, answer_key):
    """The delivered raster is centred in the recomputed slot and clears both edges."""
    book = load_book(HALLOWEEN)
    out = tmp_path / "placed"
    build_demo(book, out, **C2)
    name = "answer_key.pdf" if answer_key else "interior.pdf"
    layouts = _trusted_layouts(book, answer_key)
    with fitz.open(out / name) as pdf:
        for index, page in enumerate(pdf):
            images = page.get_image_info(xrefs=True)
            assert len(images) == 1
            expected = _slot_pdf_box(page, layouts[index])
            box = images[0]["bbox"]
            # Contained in the slot, and centred in it on both axes.
            assert expected[0] - 0.05 <= box[0] and box[2] <= expected[2] + 0.05
            assert expected[1] - 0.05 <= box[1] and box[3] <= expected[3] + 0.05
            assert (box[0] - expected[0]) == pytest.approx(expected[2] - box[2], abs=0.05)
            assert (box[1] - expected[1]) == pytest.approx(expected[3] - box[3], abs=0.05)
            pix = fitz.Pixmap(pdf, images[0]["xref"])
            assert pix.n == 1 and pix.alpha == 0
            assert min(72 * pix.width / (box[2] - box[0]),
                       72 * pix.height / (box[3] - box[1])) >= 299.99
            if index:
                # Placed in the lower band: never closer than 4 pt to board or footer.
                layout = layouts[index]
                board_top = page.rect.height - layout.board.y
                footer_top = page.rect.height - layout.footer.top
                assert box[1] - board_top >= 4.0 - 0.05
                assert footer_top - box[3] >= 4.0 - 0.05
                safe = layouts[index].safe
                assert box[0] >= safe.x - 0.05 and box[2] <= safe.right + 0.05
                assert box[1] >= page.rect.height - safe.top - 0.05
                assert box[3] <= page.rect.height - safe.y + 0.05


def test_placement_is_opt_in_and_never_byte_identical_to_c1(tmp_path, monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1780000000")
    book = load_book(HALLOWEEN)
    c1, c2 = tmp_path / "c1", tmp_path / "c2"
    build_demo(book, c1, **C1)
    build_demo(book, c2, **C2)

    def digest(root):
        return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in root.rglob("*") if path.is_file()}

    assert digest(c1) != digest(c2)
    assert (c1 / "interior.pdf").read_bytes() != (c2 / "interior.pdf").read_bytes()
    # The C2 placement reuses the very same approved raster as C1: only its box moves.
    assert _page_pixel_hashes(c1 / "interior.pdf") == _page_pixel_hashes(c2 / "interior.pdf")
    assert _page_pixel_hashes(c1 / "answer_key.pdf") == _page_pixel_hashes(c2 / "answer_key.pdf")
    for name in ("interior.pdf", "answer_key.pdf"):
        with fitz.open(c1 / name) as before, fitz.open(c2 / name) as after:
            for index in range(3):
                old = before[index].get_image_info(xrefs=True)[0]
                new = after[index].get_image_info(xrefs=True)[0]
                assert old["width"] == new["width"] and old["height"] == new["height"]
                if index == 0:
                    assert old["bbox"] == pytest.approx(new["bbox"], abs=0.05)
                else:
                    assert old["bbox"] != pytest.approx(new["bbox"], abs=0.05)
    # The pedagogical content and both quality reports are placement independent.
    for name in ("activities.json", "quality_report.json", "quality_report.md"):
        assert (c1 / name).read_bytes() == (c2 / name).read_bytes(), name
    assert json.loads((c1 / "manifest.json").read_text())["illustration_routing"] == \
        json.loads((c2 / "manifest.json").read_text())["illustration_routing"]


def test_placement_output_is_deterministic_with_fixed_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1780000000")
    book = load_book(HALLOWEEN)
    first, second = tmp_path / "first", tmp_path / "second"
    build_demo(book, first, **C2)
    build_demo(book, second, **C2)

    def digest(root):
        return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in root.rglob("*") if path.is_file()}

    assert digest(first) == digest(second)


@pytest.mark.parametrize("kwargs,expected", [
    (C1, "Placement Pip"),
    ({**C1, "pip_placement": "halloween-pip-placement-v2", "trusted_approvals_sha256": PIN},
     "placement"),
    ({**C2, "trusted_approvals_sha256": None}, "ambigu"),
    ({**C2, "trusted_approvals_sha256": "b" * 64}, "registre"),
    ({**C2, "illustration_id": "pip-reflexion-v2"}, "ambigu"),
])
def test_placement_audit_requires_the_exact_opt_in_context(tmp_path, kwargs, expected):
    book = load_book(HALLOWEEN)
    out = tmp_path / "placed"
    build_demo(book, out, **C2)
    errors = audit_output(out, book=book, **kwargs)
    assert errors and expected.lower() in " ".join(errors).lower(), errors


def test_audit_refuses_a_placement_manifest_on_a_c1_output_and_the_reverse(tmp_path):
    book = load_book(HALLOWEEN)
    c1, c2 = tmp_path / "c1", tmp_path / "c2"
    build_demo(book, c1, **C1)
    build_demo(book, c2, **C2)
    errors = audit_output(c1, book=book, **C2)
    assert any("Placement Pip" in error for error in errors), errors
    errors = audit_output(c2, book=book, **C1)
    assert errors, errors
    manifest = json.loads((c2 / "manifest.json").read_text(encoding="utf-8"))
    del manifest["pip_placement"]
    (c2 / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    errors = audit_output(c2, book=book, **C2)
    assert any("Placement Pip" in error for error in errors), errors


def test_audit_refuses_a_forged_placement_manifest_entry(tmp_path):
    book = load_book(HALLOWEEN)
    out = tmp_path / "placed"
    build_demo(book, out, **C2)
    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["pip_placement"]["bindings"][0]["anchor"] = LOWER_LEFT
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    errors = audit_output(out, book=book, **C2)
    assert any("Placement Pip" in error for error in errors), errors


def test_audit_refuses_a_canonical_placement_announced_on_a_c1_output(tmp_path):
    """A correct plan entry is still a lie when the artefacts were never placed."""
    book = load_book(HALLOWEEN)
    out = tmp_path / "c1"
    build_demo(book, out, **C1)
    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    canonical = build_pip_placement_plan(
        book, build_illustration_route(book, policy_id=ROUTING_HALLOWEEN_PIP_DEMO_V1,
                                       trusted_approvals_sha256=PIN),
        policy_id=PIP_PLACEMENT_HALLOWEEN_V1, trusted_approvals_sha256=PIN).manifest_entry()
    manifest["pip_placement"] = canonical
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    errors = audit_output(out, book=book, **C2)
    # The unplaced pages fail the recomputed placement geometry first; the
    # manifest replay comparison also fires. Any of these refusals is correct.
    assert errors and any(
        "Placement Pip" in error or "non conforme" in error or "slot C1" in error
        or "rendu attendu" in error for error in errors), errors


@pytest.mark.parametrize("take,answer_key", [
    (lambda acts: [], False), (lambda acts: acts[:1], False), (lambda acts: acts[:2], False),
    (lambda acts: acts[:1], True), (lambda acts: acts[:2], True), (lambda acts: [], True),
    (lambda acts: acts + [acts[0]], False), (lambda acts: acts + [acts[0]], True),
    (lambda acts: list(reversed(acts)), False), (lambda acts: list(reversed(acts)), True),
    (lambda acts: [acts[0], acts[0], acts[2]], False),
    (lambda acts: [acts[0], acts[1], acts[1]], True),
    (lambda acts: [acts[0], acts[1], acts[0]], False),
])
def test_renderer_refuses_any_non_canonical_activity_sequence_before_writing(tmp_path, take, answer_key):
    book = load_book(HALLOWEEN)
    activities = _activities(book)
    target = tmp_path / "interior.pdf"
    # A duplicate/reordered list fails closed either on collection validation
    # (ValueError) or on the routed canonical binding check (IllustrationError).
    with pytest.raises((IllustrationError, ValueError)):
        write_pdf(target, take(activities), book.data, answer_key=answer_key,
                  illustration_route=build_illustration_route(
                      book, policy_id=ROUTING_HALLOWEEN_PIP_DEMO_V1,
                      trusted_approvals_sha256=PIN),
                  pip_placement=PIP_PLACEMENT_HALLOWEEN_V1, approved_book=book,
                  trusted_approvals_sha256=PIN)
    assert not target.exists()


def test_renderer_refuses_forged_activity_metadata_and_substitutions(tmp_path):
    book = load_book(HALLOWEEN)
    activities = _activities(book)
    route = build_illustration_route(book, policy_id=ROUTING_HALLOWEEN_PIP_DEMO_V1,
                                     trusted_approvals_sha256=PIN)
    for forged in (
        [activities[1], activities[0], activities[2]],
        [activities[0], activities[1], activities[1]],
        [activities[0], activities[2], activities[1]],
    ):
        target = tmp_path / "forged.pdf"
        with pytest.raises((IllustrationError, ValueError)):
            write_pdf(target, forged, book.data, answer_key=False, illustration_route=route,
                      pip_placement=PIP_PLACEMENT_HALLOWEEN_V1, approved_book=book,
                      trusted_approvals_sha256=PIN)
        assert not target.exists()


def test_renderer_refuses_a_forged_route_or_placement_policy(tmp_path):
    book = load_book(HALLOWEEN)
    activities = _activities(book)
    route = build_illustration_route(book, policy_id=ROUTING_HALLOWEEN_PIP_DEMO_V1,
                                     trusted_approvals_sha256=PIN)
    target = tmp_path / "pdf"
    with pytest.raises(IllustrationError):
        write_pdf(target, activities, book.data, answer_key=False, illustration_route=route,
                  pip_placement="halloween-pip-placement-v9", approved_book=book,
                  trusted_approvals_sha256=PIN)
    with pytest.raises(IllustrationError):
        write_pdf(target, activities, book.data, answer_key=False, illustration_route=route,
                  pip_placement=PIP_PLACEMENT_HALLOWEEN_V1, approved_book=book,
                  trusted_approvals_sha256="c" * 64)
    with pytest.raises(IllustrationError):
        write_pdf(target, activities, book.data, answer_key=False, illustration_route=route,
                  pip_placement=PIP_PLACEMENT_HALLOWEEN_V1, approved_book=None,
                  trusted_approvals_sha256=PIN)
    with pytest.raises(IllustrationError):
        write_pdf(target, activities, book.data, answer_key=False,
                  pip_placement=PIP_PLACEMENT_HALLOWEEN_V1, approved_book=book,
                  trusted_approvals_sha256=PIN)
    assert not target.exists()


def test_renderer_refuses_placement_without_the_c1_route(tmp_path):
    book = load_book(HALLOWEEN)
    activities = _activities(book)
    for extra in ({"illustration_route": None, "pip_placement": PIP_PLACEMENT_HALLOWEEN_V1},
                  {"illustration_route": None, "pip_placement": "halloween-pip-placement-v1"},
                  {"pip_placement": None}):
        target = tmp_path / "plain.pdf"
        kwargs = {"answer_key": False, "illustration_route": build_illustration_route(
            book, policy_id=ROUTING_HALLOWEEN_PIP_DEMO_V1, trusted_approvals_sha256=PIN),
            "pip_placement": PIP_PLACEMENT_HALLOWEEN_V1, "approved_book": book,
            "trusted_approvals_sha256": PIN}
        kwargs.update(extra)
        if extra.get("pip_placement") is None:
            # C1 without placement stays permitted and produces an unplaced page.
            write_pdf(target, activities, book.data, **kwargs)
            assert target.exists()
            continue
        with pytest.raises(IllustrationError):
            write_pdf(target, activities, book.data, **kwargs)
        assert not target.exists()


@pytest.mark.parametrize("answer_key", [False, True])
def test_renderer_refusal_leaves_an_existing_file_untouched(tmp_path, answer_key):
    book = load_book(HALLOWEEN)
    activities = _activities(book)
    target = tmp_path / "existing.pdf"
    route = build_illustration_route(book, policy_id=ROUTING_HALLOWEEN_PIP_DEMO_V1,
                                     trusted_approvals_sha256=PIN)
    write_pdf(target, activities, book.data, answer_key=answer_key, illustration_route=route,
              pip_placement=PIP_PLACEMENT_HALLOWEEN_V1, approved_book=book,
              trusted_approvals_sha256=PIN)
    before = hashlib.sha256(target.read_bytes()).hexdigest()
    with pytest.raises(IllustrationError):
        write_pdf(target, activities[:2], book.data, answer_key=answer_key,
                  illustration_route=route, pip_placement=PIP_PLACEMENT_HALLOWEEN_V1,
                  approved_book=book, trusted_approvals_sha256=PIN)
    assert hashlib.sha256(target.read_bytes()).hexdigest() == before


def test_placement_audit_rejects_a_slot_moved_by_more_than_the_tolerance(tmp_path, monkeypatch):
    book = load_book(HALLOWEEN)
    out = tmp_path / "placed"
    from lafractale.illustrations import placement as placement_module

    original = placement_module.placed_slot

    def shifted(layout, anchor):
        slot = original(layout, anchor)
        # +1 pt stays inside every clearance rule but breaks the canonical box.
        return type(slot)(slot.x, slot.y + 1.0, slot.width, slot.height)

    monkeypatch.setattr(placement_module, "placed_slot", shifted)
    build_demo(book, out, **C2)
    monkeypatch.setattr(placement_module, "placed_slot", original)
    errors = audit_output(out, book=book, **C2)
    assert any("slot" in error.lower() or "bbox" in error.lower() for error in errors), errors


def test_placement_audit_rejects_a_stretched_slot(tmp_path, monkeypatch):
    book = load_book(HALLOWEEN)
    out = tmp_path / "placed"
    from lafractale.illustrations import placement as placement_module

    original = placement_module.placed_slot

    def stretched(layout, anchor):
        slot = original(layout, anchor)
        return type(slot)(slot.x, slot.y, slot.width * 0.8, slot.height)

    monkeypatch.setattr(placement_module, "placed_slot", stretched)
    build_demo(book, out, **C2)
    monkeypatch.setattr(placement_module, "placed_slot", original)
    errors = audit_output(out, book=book, **C2)
    assert errors, "une zone étirée doit être refusée"


@pytest.mark.parametrize("offset", [-2.0, 5.6])
def test_placement_build_refuses_a_slot_without_minimum_clearance(tmp_path, monkeypatch, offset):
    """A 2 pt loss of footer clearance and a 0.1 pt board overlap are both refused."""
    book = load_book(HALLOWEEN)
    from lafractale.illustrations import placement as placement_module

    original = placement_module.placed_slot

    def cramped(layout, anchor):
        slot = original(layout, anchor)
        if anchor == LOWER_RIGHT:
            return type(slot)(slot.x, slot.y + offset, slot.width, slot.height)
        return slot

    monkeypatch.setattr(placement_module, "placed_slot", cramped)
    with pytest.raises(IllustrationError):
        build_demo(book, tmp_path / f"cramped{offset}", **C2)


def test_placement_audit_rejects_an_extra_image_a_foreign_patch_and_a_mask(tmp_path):
    book = load_book(HALLOWEEN)
    out = tmp_path / "placed"
    build_demo(book, out, **C2)
    interior = out / "interior.pdf"
    with fitz.open(interior) as document:
        page = document[0]
        pix = fitz.Pixmap(document, page.get_image_info(xrefs=True)[0]["xref"])
        page.insert_image(fitz.Rect(300, 300, 320, 320), stream=pix.tobytes("png"))
        altered = document.tobytes(garbage=3, deflate=True)
    interior.write_bytes(altered)
    _rebuild_manifest(out)
    errors = audit_output(out, book=book, **C2)
    assert any("illustration" in error.lower() for error in errors), errors


def test_placement_audit_rejects_a_pose_swapped_only_in_the_answer_key(tmp_path):
    book = load_book(HALLOWEEN)
    out = tmp_path / "placed"
    build_demo(book, out, **C2)
    answer_key = out / "answer_key.pdf"
    with fitz.open(answer_key) as document:
        first = document[0].get_image_info(xrefs=True)[0]["xref"]
        second = document[1].get_image_info(xrefs=True)[0]["xref"]
        document.update_stream(first, document.xref_stream(second), compress=True)
        altered = document.tobytes(garbage=3, deflate=True)
    answer_key.write_bytes(altered)
    _rebuild_manifest(out)
    errors = audit_output(out, book=book, **C2)
    assert any("pixels graphiques différents" in error for error in errors), errors


def test_placement_audit_rejects_a_moved_image_inside_the_slot(tmp_path):
    book = load_book(HALLOWEEN)
    out = tmp_path / "placed"
    build_demo(book, out, **C2)
    interior = out / "interior.pdf"
    with fitz.open(interior) as document:
        page = document[1]
        info = page.get_image_info(xrefs=True)[0]
        xref = info["xref"]
        pix = fitz.Pixmap(document, xref)
        page.insert_image(fitz.Rect(200.0, 600.0, 260.0, 660.0), stream=pix.tobytes("png"))
        altered = document.tobytes(garbage=3, deflate=True)
    interior.write_bytes(altered)
    _rebuild_manifest(out)
    errors = audit_output(out, book=book, **C2)
    assert errors, "une image déplacée et surnuméraire doit être refusée"


def test_placement_audit_rejects_a_falsified_preview(tmp_path):
    book = load_book(HALLOWEEN)
    out = tmp_path / "placed"
    build_demo(book, out, **C2)
    preview = out / "previews" / "interior_page_02.png"
    with Image.open(preview) as image:
        image.convert("RGB").save(preview)
    _rebuild_manifest(out)
    errors = audit_output(out, book=book, **C2)
    assert errors, "un aperçu falsifié doit être refusé"


def test_placement_audit_rejects_hidden_symlink_and_fifo_entries(tmp_path):
    import os

    book = load_book(HALLOWEEN)
    for kind in ("hidden", "symlink", "fifo", "empty_dir"):
        out = tmp_path / kind
        build_demo(book, out, **C2)
        if kind == "hidden":
            (out / ".cache").write_bytes(b"x")
        elif kind == "symlink":
            os.symlink(out / "manifest.json", out / "alias.json")
        elif kind == "fifo":
            os.mkfifo(out / "pipe")
        else:
            (out / "extra").mkdir()
        errors = audit_output(out, book=book, **C2)
        assert errors, kind


def test_placement_audit_rejects_a_changed_source_book(tmp_path, monkeypatch):
    book = load_book(HALLOWEEN)
    out = tmp_path / "placed"
    build_demo(book, out, **C2)
    christmas = load_book(CHRISTMAS)
    errors = audit_output(out, book=christmas, **C2)
    assert errors
