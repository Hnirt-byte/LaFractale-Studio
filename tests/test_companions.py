"""Guard character ownership, integrity, neutral previews and future extensibility."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from shutil import copy2

import fitz
import pytest
import yaml

from lafractale.config.schema import ConfigError, load_book
from lafractale.config.companions import CompanionError
from lafractale.export.builder import build_demo, audit_output
from lafractale.story.plan import demo_specs, full_build_blockers

ROOT = Path(__file__).resolve().parents[1]


def _project(tmp_path, source="halloween_2026"):
    root = tmp_path / "project"
    root.mkdir()
    (root / "pyproject.toml").write_text("[project]\n", encoding="utf8")
    config = root / "books" / source / "book.yaml"
    config.parent.mkdir(parents=True)
    data = yaml.safe_load((ROOT / "books" / source / "book.yaml").read_text(encoding="utf8"))
    return root, config, data


def test_halloween_uses_only_approved_pip(halloween):
    assert halloween.companion.id == "pip"
    assert halloween.companion.name == "Pip"
    assert halloween.companion.reference == "assets/characters/pip/pip_officiel_couleur.png"
    assert sha256((ROOT / halloween.companion.reference).read_bytes()).hexdigest() == halloween.companion.sha256


def test_christmas_has_no_pip_anywhere_in_generated_files(tmp_path):
    book = load_book(ROOT / "books/christmas_2026/book.yaml")
    assert book.companion.status == "pending_selection"
    assert book.companion.name is None
    assert any("Compagnon non choisi" in blocker for blocker in full_build_blockers(book))
    out = tmp_path / "christmas"
    build_demo(book, out)
    assert audit_output(out, book=book) == []
    for path in (out / "activities.json", out / "manifest.json", out / "quality_report.json"):
        assert "pip" not in path.read_text(encoding="utf8").casefold()
    for name in ("interior.pdf", "answer_key.pdf"):
        with fitz.open(out / name) as doc:
            assert all("Pip" not in page.get_text() for page in doc)
    assert json.loads((out / "manifest.json").read_text(encoding="utf8"))["companion"]["status"] == "pending_selection"


def test_pip_cannot_be_assigned_to_christmas(tmp_path):
    root, path, data = _project(tmp_path, "christmas_2026")
    data["companion"] = {"status": "approved_reference", "id": "pip"}
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf8")
    # Access control is evaluated before attempting to read the asset.
    (root / "assets/companions").mkdir(parents=True)
    copy2(ROOT / "assets/companions/catalog.yaml", root / "assets/companions/catalog.yaml")
    with pytest.raises(ConfigError, match="interdit pour le livre"):
        load_book(path)


def test_pending_selection_cannot_smuggle_unapproved_identity(tmp_path):
    root, path, data = _project(tmp_path, "christmas_2026")
    data["companion"] = {"status": "pending_selection", "id": "pip"}
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf8")
    with pytest.raises(ConfigError, match="en attente"):
        load_book(path)


def test_legacy_mascot_is_rejected(tmp_path):
    root, path, data = _project(tmp_path, "christmas_2026")
    data["mascot"] = {"name": "Pip"}
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf8")
    with pytest.raises(ConfigError, match="mascot V0.1 obsolète"):
        load_book(path)


def test_asset_checksum_tamper_rejected(tmp_path):
    root, path, data = _project(tmp_path)
    (root / "assets/companions").mkdir(parents=True)
    copy2(ROOT / "assets/companions/catalog.yaml", root / "assets/companions/catalog.yaml")
    asset = root / "assets/characters/pip/pip_officiel_couleur.png"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"tampered-image")
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf8")
    with pytest.raises(ConfigError, match="SHA-256"):
        load_book(path)


def test_unknown_character_is_rejected(tmp_path):
    root, path, data = _project(tmp_path, "christmas_2026")
    (root / "assets/companions").mkdir(parents=True)
    copy2(ROOT / "assets/companions/catalog.yaml", root / "assets/companions/catalog.yaml")
    data["companion"] = {"status": "approved_reference", "id": "unknown"}
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf8")
    with pytest.raises(ConfigError, match="non approuvé"):
        load_book(path)


def test_new_catalog_character_needs_no_engine_changes(tmp_path):
    root, path, data = _project(tmp_path, "christmas_2026")
    catalog_path = root / "assets/companions/catalog.yaml"
    catalog_path.parent.mkdir(parents=True)
    asset = root / "assets/characters/example/reference.png"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"TEST-FIXTURE-NOT-AN-APPROVED-ILLUSTRATION")
    catalog = {"characters": {"example": {"name": "Exemple",
                          "allowed_book_ids": ["christmas_2026"],
                          "approved_reference": "assets/characters/example/reference.png",
                          "sha256": sha256(asset.read_bytes()).hexdigest(),
                          "visual_constraints": ["fixture for test only"],
                          "reference_only": True}}}
    catalog_path.write_text(yaml.safe_dump(catalog), encoding="utf8")
    data["companion"] = {"status": "approved_reference", "id": "example"}
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf8")
    loaded = load_book(path)
    assert loaded.companion.name == "Exemple"
    specs = demo_specs(loaded)
    assert all(spec.companion_name == "Exemple" for spec in specs)


def test_companion_in_halloween_activity_prompts(halloween):
    maze = next(x for x in demo_specs(halloween) if x.type == "maze")
    from lafractale.activities.engine import generate
    activity = generate(maze, 42)
    assert activity.companion_name == "Pip"
    assert "Pip" in activity.prompt_fr


def test_full_christmas_build_reports_pending_companion(tmp_path, capsys):
    from lafractale.__main__ import main
    assert main(["build", str(ROOT / "books/christmas_2026/book.yaml"),
                 "--out", str(tmp_path / "no-book")]) == 2
    stderr = capsys.readouterr().err
    assert "Compagnon non choisi" in stderr
    assert "page_plan.csv absent" in stderr
    assert not (tmp_path / "no-book" / "interior.pdf").exists()

# Hermes security review regression suite (four initially reported bypasses).

def _install_catalog(root):
    catalog = root / "assets/companions/catalog.yaml"
    catalog.parent.mkdir(parents=True, exist_ok=True)
    copy2(ROOT / "assets/companions/catalog.yaml", catalog)
    return catalog


def _install_pip(root):
    source = ROOT / "assets/characters/pip/pip_officiel_couleur.png"
    target = root / "assets/characters/pip/pip_officiel_couleur.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    copy2(source, target)
    return target


def test_security_rejects_namespace_traversal_even_inside_repository(tmp_path):
    root, path, data = _project(tmp_path)
    catalog_file = _install_catalog(root)
    _install_pip(root)
    catalog = yaml.safe_load(catalog_file.read_text(encoding="utf-8"))
    # A path can resolve INSIDE the repo while escaping assets/characters/pip.
    catalog["characters"]["pip"]["approved_reference"] = "assets/characters/pip/../../../pyproject.toml"
    catalog_file.write_text(yaml.safe_dump(catalog, allow_unicode=True), encoding="utf-8")
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ConfigError, match="Traversée|namespace|segment"):
        load_book(path)


@pytest.mark.parametrize("location", ["assets", "assets/companions"])
def test_security_rejects_symlinked_catalog_parent(tmp_path, location):
    root, path, data = _project(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "catalog.yaml").write_text(
        (ROOT / "assets/companions/catalog.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    if location == "assets":
        # assets -> external directory with a companions/catalog.yaml.
        (outside / "companions").mkdir()
        copy2(outside / "catalog.yaml", outside / "companions/catalog.yaml")
        (root / "assets").symlink_to(outside, target_is_directory=True)
    else:
        (root / "assets").mkdir()
        (root / "assets/companions").symlink_to(outside, target_is_directory=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ConfigError, match="symlink|interdit|compagnon"):
        load_book(path)


def test_security_rejects_asset_symlinked_parent(tmp_path):
    root, path, data = _project(tmp_path)
    _install_catalog(root)
    external = tmp_path / "outside"
    external.mkdir()
    copy2(ROOT / "assets/characters/pip/pip_officiel_couleur.png", external / "pip_officiel_couleur.png")
    (root / "assets/characters").mkdir(parents=True)
    (root / "assets/characters/pip").symlink_to(external, target_is_directory=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ConfigError, match="symlink|interdit"):
        load_book(path)


def test_security_revalidates_asset_after_load_before_registry_and_manifest(tmp_path):
    from lafractale.assets.registry import registry
    root, path, data = _project(tmp_path)
    _install_catalog(root)
    asset = _install_pip(root)
    copy2(ROOT / "books/halloween_2026/page_plan.csv", path.with_name("page_plan.csv"))
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    book = load_book(path)
    assert registry(book)[0]["sha256"] == book.companion.sha256
    # Same Book object, changed bytes after initial load.
    asset.write_bytes(b"POST_LOAD_ASSET_MUTATION")
    with pytest.raises(CompanionError, match="SHA-256"):
        registry(book)
    out = tmp_path / "reject"
    with pytest.raises(CompanionError, match="SHA-256"):
        build_demo(book, out)
    assert not (out / "manifest.json").exists()


def test_security_rejects_catalog_changes_after_load(tmp_path):
    from lafractale.assets.registry import registry
    root, path, data = _project(tmp_path)
    catalog_file = _install_catalog(root)
    _install_pip(root)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    book = load_book(path)
    cat = yaml.safe_load(catalog_file.read_text(encoding="utf-8"))
    cat["characters"]["pip"]["name"] = "Fake Pip"
    catalog_file.write_text(yaml.safe_dump(cat, allow_unicode=True), encoding="utf-8")
    with pytest.raises(CompanionError, match="modifié"):
        registry(book)


@pytest.mark.parametrize("injection", [
    ("story", "premise", "Pip arrive dans la neige"),
    ("demo_activities", 0, "Regarde Pip dans la forêt"),
    ("title", None, "Mon Noël avec PIP"),
])
def test_security_rejects_pending_companion_prose_leak_in_yaml(tmp_path, injection):
    root, path, data = _project(tmp_path, "christmas_2026")
    _install_catalog(root)
    kind, key, text = injection
    if kind == "demo_activities":
        data[kind][key]["scene"] = text
    elif kind == "title":
        data[kind] = text
    else:
        data[kind][key] = text
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ConfigError, match="Compagnon non autorisé.*Pip"):
        load_book(path)


def test_security_rechecks_pending_scene_modified_after_load(tmp_path):
    root, path, data = _project(tmp_path, "christmas_2026")
    _install_catalog(root)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    book = load_book(path)
    book.data["demo_activities"][0]["scene"] = "Pip entre en scène"
    with pytest.raises(CompanionError, match="Compagnon non autorisé"):
        build_demo(book, tmp_path / "reject")
    assert not (tmp_path / "reject" / "manifest.json").exists()


def test_security_rejects_pending_companion_in_page_plan(tmp_path):
    from dataclasses import replace
    root, path, data = _project(tmp_path, "christmas_2026")
    _install_catalog(root)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    book = load_book(path)
    altered_book = replace(book, plan=({"story_beat": "Pip se cache dans la cheminée"},))
    with pytest.raises(CompanionError, match="Compagnon non autorisé"):
        build_demo(altered_book, tmp_path / "reject")


# Independent Hermes second-review bypass: catalog changed after load in pending mode.

def test_security_pending_catalog_deletion_cannot_hide_pip_from_postload_scene(tmp_path):
    root, path, data = _project(tmp_path, "christmas_2026")
    catalog_file = _install_catalog(root)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    book = load_book(path)
    assert "Pip" in book.companion.reserved_names
    catalog = yaml.safe_load(catalog_file.read_text(encoding="utf-8"))
    catalog["characters"].pop("pip")
    catalog_file.write_text(yaml.safe_dump(catalog, allow_unicode=True), encoding="utf-8")
    book.data["demo_activities"][0]["scene"] = "Pip apparaît dans la neige"
    out = tmp_path / "must-not-build"
    with pytest.raises(CompanionError, match="catalogue.*modifié"):
        build_demo(book, out)
    assert not (out / "manifest.json").exists()
    assert not (out / "interior.pdf").exists()


def test_security_pending_catalog_changed_without_scene_rejected_by_registry_and_build(tmp_path):
    from lafractale.assets.registry import registry
    root, path, data = _project(tmp_path, "christmas_2026")
    catalog_file = _install_catalog(root)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    book = load_book(path)
    # A semantically equivalent but differently hashed catalogue still fails closed.
    catalog_file.write_bytes(catalog_file.read_bytes() + b"\n# post-load changed\n")
    with pytest.raises(CompanionError, match="catalogue.*modifié"):
        registry(book)
    out = tmp_path / "must-not-build"
    with pytest.raises(CompanionError, match="catalogue.*modifié"):
        build_demo(book, out)
    assert not (out / "manifest.json").exists()


def test_security_selected_catalog_change_elsewhere_rejected(tmp_path):
    from lafractale.assets.registry import registry
    root, path, data = _project(tmp_path, "halloween_2026")
    catalog_file = _install_catalog(root)
    _install_pip(root)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    book = load_book(path)
    catalog_file.write_bytes(catalog_file.read_bytes() + b"\n# unrelated catalogue edit\n")
    with pytest.raises(CompanionError, match="catalogue.*modifié"):
        registry(book)


def test_security_pending_catalog_mutated_midbuild_cannot_emit_manifest(tmp_path, monkeypatch):
    import lafractale.export.builder as builder
    root, path, data = _project(tmp_path, "christmas_2026")
    catalog_file = _install_catalog(root)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    book = load_book(path)
    original_write = builder.write_pdf

    def sabotage_after_first_pdf(*args, **kwargs):
        original_write(*args, **kwargs)
        if not kwargs["answer_key"]:
            cat = yaml.safe_load(catalog_file.read_text(encoding="utf-8"))
            cat["characters"].pop("pip")
            catalog_file.write_text(yaml.safe_dump(cat, allow_unicode=True), encoding="utf-8")

    monkeypatch.setattr(builder, "write_pdf", sabotage_after_first_pdf)
    out = tmp_path / "must-not-build"
    with pytest.raises(CompanionError, match="catalogue.*modifié"):
        builder.build_demo(book, out)
    assert not (out / "manifest.json").exists()


def test_security_pending_catalog_symlink_swap_after_load_rejected(tmp_path):
    from lafractale.assets.registry import registry
    root, path, data = _project(tmp_path, "christmas_2026")
    catalog_file = _install_catalog(root)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    book = load_book(path)
    external = tmp_path / "untrusted_catalog.yaml"
    external.write_bytes(catalog_file.read_bytes())
    catalog_file.unlink()
    catalog_file.symlink_to(external)
    with pytest.raises(CompanionError, match="symlink|interdit"):
        registry(book)


def test_security_pending_prose_mutated_during_render_prevents_manifest(tmp_path, monkeypatch):
    import lafractale.export.builder as builder
    root, path, data = _project(tmp_path, "christmas_2026")
    _install_catalog(root)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    book = load_book(path)
    original_write = builder.write_pdf

    def sabotage_scene_after_pdf(*args, **kwargs):
        original_write(*args, **kwargs)
        if not kwargs["answer_key"]:
            book.data["demo_activities"][0]["scene"] = "Pip est dans la neige"

    monkeypatch.setattr(builder, "write_pdf", sabotage_scene_after_pdf)
    out = tmp_path / "must-not-build"
    with pytest.raises(CompanionError, match="Compagnon non autorisé"):
        builder.build_demo(book, out)
    assert not (out / "manifest.json").exists()

# Independent Hermes third-review bypass: frozen dataclass with forged name
# must never become an authority for rendering or for exempting catalogue names.
@pytest.mark.parametrize("overrides", [
    {"name": "Pip"},
    {"id": "pip"},
    {"reference": "assets/characters/pip/pip_officiel_couleur.png"},
    {"sha256": "0" * 64},
    {"visual_constraints": ("Noël peut utiliser Pip",)},
    {"status": "approved_reference", "id": "pip", "name": "Pip"},
    {"reserved_names": ()},
    {"book_id": "halloween_2026"},
    {"catalog_sha256": "0" * 64},
])
def test_security_rejects_forged_pending_profile_all_fields(tmp_path, overrides):
    from dataclasses import replace
    from lafractale.config.companions import CompanionError, verify_companion_text
    from lafractale.export.builder import build_demo
    from lafractale.config.schema import load_book
    root, path, data = _project(tmp_path, "christmas_2026")
    _install_catalog(root)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    book = load_book(path)
    forged = replace(book, companion=replace(book.companion, **overrides))
    with pytest.raises(CompanionError):
        verify_companion_text(forged.root, forged.companion, forged.data, forged.plan)
    out = tmp_path / "reject-forgery"
    with pytest.raises(CompanionError):
        build_demo(forged, out)
    assert not (out / "interior.pdf").exists()
    assert not (out / "manifest.json").exists()


def test_security_exact_hermes_forged_name_bypass(tmp_path):
    from dataclasses import replace
    from lafractale.config.companions import CompanionError, verify_companion_text
    from lafractale.export.builder import build_demo
    import fitz
    root, path, data = _project(tmp_path, "christmas_2026")
    _install_catalog(root)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    book = load_book(path)
    forged_profile = replace(book.companion, name="Pip")
    forged_book = replace(book, companion=forged_profile)
    with pytest.raises(CompanionError):
        verify_companion_text(forged_book.root, forged_profile, forged_book.data, forged_book.plan)
    out = tmp_path / "forged-hermes"
    with pytest.raises(CompanionError):
        build_demo(forged_book, out)
    assert not (out / "interior.pdf").exists()
    assert not (out / "manifest.json").exists()


def test_security_pending_configuration_mutation_is_not_authoritative(tmp_path):
    from lafractale.config.companions import CompanionError
    root, path, data = _project(tmp_path, "christmas_2026")
    _install_catalog(root)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    book = load_book(path)
    book.data["companion"] = {"status": "pending_selection", "id": "new_hero"}
    out = tmp_path / "bad-memory-config"
    with pytest.raises(CompanionError):
        build_demo(book, out)
    assert not (out / "manifest.json").exists()


def test_security_selected_name_forgery_is_rejected(tmp_path):
    from dataclasses import replace
    from lafractale.config.companions import CompanionError
    root, path, data = _project(tmp_path, "halloween_2026")
    _install_catalog(root)
    _install_pip(root)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    book = load_book(path)
    forged = replace(book, companion=replace(book.companion, name="Autre"))
    out = tmp_path / "bad-selected"
    with pytest.raises(CompanionError):
        build_demo(forged, out)
    assert not (out / "manifest.json").exists()


def test_security_rejects_cross_book_identity_replay(tmp_path):
    """A valid Halloween Pip profile must not authorize a Christmas YAML."""
    from dataclasses import replace
    from lafractale.config.companions import CompanionError
    halloween = load_book(ROOT / "books/halloween_2026/book.yaml")
    christmas = load_book(ROOT / "books/christmas_2026/book.yaml")
    christmas.data["book_id"] = "halloween_2026"
    christmas.data["companion"] = {"status": "approved_reference", "id": "pip"}
    forged = replace(christmas, companion=halloween.companion)
    out = tmp_path / "cross-book"
    with pytest.raises(CompanionError, match="Configuration du livre modifiée"):
        build_demo(forged, out)
    assert not (out / "interior.pdf").exists()
    assert not (out / "manifest.json").exists()


def test_security_rejects_source_yaml_mutation_after_load(tmp_path):
    root, path, data = _project(tmp_path, "christmas_2026")
    _install_catalog(root)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    book = load_book(path)
    path.write_bytes(path.read_bytes() + b"\n# modified source\n")
    out = tmp_path / "changed-source"
    with pytest.raises(CompanionError, match="Configuration du livre modifiée"):
        build_demo(book, out)
    assert not (out / "manifest.json").exists()


def test_security_rejects_selected_companion_profile_field_mutations(tmp_path):
    from dataclasses import replace
    halloween = load_book(ROOT / "books/halloween_2026/book.yaml")
    for field, value in (
        ("id", "another"), ("name", "Other"), ("reference", None),
        ("sha256", None), ("visual_constraints", ("forged",)),
        ("status", "pending_selection"), ("reserved_names", ()),
    ):
        forged = replace(halloween, companion=replace(halloween.companion, **{field: value}))
        with pytest.raises(CompanionError):
            build_demo(forged, tmp_path / ("selected-" + field))


def test_security_rejects_forged_book_data_hash(tmp_path):
    from dataclasses import replace
    from lafractale.config.schema import _hash_data
    halloween = load_book(ROOT / "books/halloween_2026/book.yaml")
    christmas = load_book(ROOT / "books/christmas_2026/book.yaml")
    altered = dict(christmas.data)
    altered["book_id"] = halloween.book_id
    altered["companion"] = {"status": "approved_reference", "id": "pip"}
    forged = replace(christmas, companion=halloween.companion, data=altered,
                     data_sha256=_hash_data(altered))
    out = tmp_path / "cross-book-plus-hash"
    with pytest.raises(CompanionError, match="Configuration du livre modifiée"):
        build_demo(forged, out)
    assert not (out / "manifest.json").exists()


def test_security_rejects_unauthorized_name_in_yaml_mapping_key(tmp_path):
    root, path, data = _project(tmp_path, "christmas_2026")
    _install_catalog(root)
    data["story"]["Pip"] = "une surprise"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ConfigError, match="Compagnon non autorisé"):
        load_book(path)


def test_security_midbuild_mutation_cannot_publish_partially_rendered_pdf(tmp_path, monkeypatch):
    import lafractale.export.builder as builder
    root, path, data = _project(tmp_path, "christmas_2026")
    _install_catalog(root)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    book = load_book(path)
    real_writer = builder.write_pdf

    def inject_unapproved_name_after_first_pdf(*args, **kwargs):
        real_writer(*args, **kwargs)
        if kwargs.get("answer_key") is False:
            book.data["demo_activities"][0]["scene"] = "Pip dans la neige"

    monkeypatch.setattr(builder, "write_pdf", inject_unapproved_name_after_first_pdf)
    out = tmp_path / "must-stay-empty"
    with pytest.raises(CompanionError, match="Compagnon non autorisé"):
        builder.build_demo(book, out)
    assert not out.exists(), "Aucun PDF intermédiaire ne doit fuiter vers dist/"


def test_security_failed_rebuild_preserves_last_valid_output(tmp_path):
    root, path, data = _project(tmp_path, "christmas_2026")
    _install_catalog(root)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    book = load_book(path)
    out = tmp_path / "existing-demo"
    build_demo(book, out)
    before = {x.name: x.read_bytes() for x in out.glob("*.json")}
    book.data["demo_activities"][0]["scene"] = "Pip dans la neige"
    with pytest.raises(CompanionError):
        build_demo(book, out)
    after = {x.name: x.read_bytes() for x in out.glob("*.json")}
    assert after == before
    assert audit_output(out, book=load_book(path)) == []


def test_security_rejects_symlinked_plan_at_load(tmp_path):
    root, path, data = _project(tmp_path, "christmas_2026")
    _install_catalog(root)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    outside = tmp_path / "external-plan.csv"
    outside.write_text("page,chapter,story_beat,activity_type,vocabulary,status\n",
                       encoding="utf-8")
    path.with_name("page_plan.csv").symlink_to(outside)
    with pytest.raises(CompanionError, match="symlink|interdit"):
        load_book(path)
