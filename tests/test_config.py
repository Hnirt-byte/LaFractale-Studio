from pathlib import Path
from shutil import copy2
import pytest
import yaml
from lafractale.config.schema import ConfigError,load_book,validate_plan_vocabulary,within_root
from lafractale.__main__ import main
from lafractale.story.plan import demo_specs,full_build_blockers
from lafractale.assets.registry import registry

ROOT=Path(__file__).resolve().parents[1]


def test_halloween_plan_exact_56(halloween):
    assert halloween.pages==56
    assert len(halloween.plan)==56
    assert validate_plan_vocabulary(halloween)==[]
    assert set(s.type for s in demo_specs(halloween))=={"maze","connect_dots","match"}
    assert full_build_blockers(halloween)


def test_christmas_80_without_fake_pages():
    book=load_book(ROOT/"books/christmas_2026/book.yaml")
    assert book.pages==80
    assert len(book.plan)==0
    assert set(s.type for s in demo_specs(book))=={"maze","connect_dots","match"}
    assert full_build_blockers(book)


def test_malformed_demo_vocabulary_is_a_controlled_config_error():
    book = load_book(ROOT / "books/christmas_2026/book.yaml")
    book.data["demo_activities"][0]["vocabulary"] = 123
    with pytest.raises(ConfigError, match="vocabulary"):
        demo_specs(book)


def test_malformed_demo_type_is_a_controlled_config_error():
    book = load_book(ROOT / "books/christmas_2026/book.yaml")
    book.data["demo_activities"][0]["type"] = []
    with pytest.raises(ConfigError, match="type/page/scene/vocabulary"):
        demo_specs(book)


def test_non_string_vocabulary_value_is_a_controlled_config_error(tmp_path):
    source = ROOT / "books/christmas_2026/book.yaml"
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    data["vocabulary"]["étoile"] = 123
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    asset = tmp_path / "assets/characters/pip"
    asset.mkdir(parents=True)
    copy2(ROOT / "assets/characters/pip/pip_officiel_couleur.png", asset / "pip_officiel_couleur.png")
    config = tmp_path / "book.yaml"
    config.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ConfigError, match="vocabulary"):
        load_book(config)
    assert main(["validate", str(config)]) == 2


def test_null_mascot_and_non_string_title_are_controlled_cli_errors(tmp_path):
    source = ROOT / "books/christmas_2026/book.yaml"
    base = yaml.safe_load(source.read_text(encoding="utf-8"))
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    asset = tmp_path / "assets/characters/pip"
    asset.mkdir(parents=True)
    copy2(ROOT / "assets/characters/pip/pip_officiel_couleur.png", asset / "pip_officiel_couleur.png")
    for name, field, value in (("null-mascot", "mascot", None), ("bad-title", "title", [])):
        data = dict(base)
        data[field] = value
        config = tmp_path / f"{name}.yaml"
        config.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        with pytest.raises(ConfigError):
            load_book(config)
        assert main(["validate", str(config)]) == 2


def test_missing_asset_is_blocking(tmp_path):
    project=tmp_path/"project"; project.mkdir()
    (project/"pyproject.toml").write_text("[project]\n",encoding="utf-8")
    src=(ROOT/"books/halloween_2026/book.yaml").read_text(encoding="utf-8")
    cfg=project/"book.yaml";cfg.write_text(src,encoding="utf-8")
    with pytest.raises(ConfigError,match="Asset officiel absent"):
        load_book(cfg)


def test_outside_asset_path_rejected(tmp_path):
    with pytest.raises(ConfigError,match="hors du projet"):
        within_root(tmp_path,"../other/secret.png")


def test_approved_reference_registered(halloween):
    records=registry(halloween)
    assert len(records)==1
    assert records[0]["approval"]=="APPROVED_REFERENCE"
    assert records[0]["bw_variant"]=="PENDING_HUMAN_APPROVAL"
    assert len(records[0]["sha256"])==64


def test_missing_book_file():
    with pytest.raises(ConfigError,match="Configuration absente"):
        load_book(ROOT/"books/does-not-exist/book.yaml")


def test_missing_required_key_is_a_controlled_config_error(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    config = tmp_path / "book.yaml"
    config.write_text("book_id: missing-fields\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="Champ obligatoire absent"):
        load_book(config)


def test_full_book_refuses_unimplemented_mechanics(halloween):
    blockers=full_build_blockers(halloween)
    assert "coloring" in " ".join(blockers)
