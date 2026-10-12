"""B3-B.1 source contract: strict JSON, closed keys, synthetic-only (adversarial)."""
import pytest

from b3b1_support import FIXTURE, dumps, mutated, spec_dict
from lafractale.engine import ContractError
from lafractale.engine.contracts import MAX_SOURCE_BYTES, load_spec_set, parse_spec_set


def test_fixture_is_valid_and_synthetic():
    spec = load_spec_set(FIXTURE)
    assert spec.spec_id == "synthetic_slice_v1"
    assert [p.mechanic for p in spec.pages] == ["maze", "connect_dots", "match"] * 2
    assert len(spec.source_sha256) == 64


def test_parse_is_deterministic_and_immutable():
    payload = FIXTURE.read_bytes()
    assert parse_spec_set(payload) == parse_spec_set(payload)
    with pytest.raises(TypeError):
        parse_spec_set(payload).pages[0].params["x"] = "y"


def _set(path, value):
    def apply(data):
        target = data
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
    return apply


def _drop(path):
    def apply(data):
        target = data
        for key in path[:-1]:
            target = target[key]
        del target[path[-1]]
    return apply


def _many_pages(data):
    data["pages"] = [dict(data["pages"][0], page=i + 1, unit_id=f"syn-p{i + 1:03d}") for i in range(13)]


ADVERSARIAL = {
    "unknown top-level key": (_set(["extra"], 1), "clé inconnue"),
    "unknown page key": (_set(["pages", 0, "colour"], "red"), "clé inconnue"),
    "missing page key": (_drop(["pages", 0, "scene"]), "clé obligatoire absente"),
    "companion key": (_set(["companion"], {"id": "x"}), "clé interdite"),
    "production flag": (_set(["production"], True), "clé interdite"),
    "ready_for_kdp key": (_set(["ready_for_kdp"], True), "clé interdite"),
    "asset key on page": (_set(["pages", 0, "assets"], ["a.png"]), "clé interdite"),
    "non synthetic kind": (_set(["kind"], "PRODUCTION"), "kind"),
    "wrong schema": (_set(["schema"], "other-v9"), "schema"),
    "real book id": (_set(["spec_id"], "halloween_2026"), "spec_id"),
    "mascot name in text": (_set(["pages", 0, "prompt_fr"], "Aide Pip à sortir."), "Compagnon non autorisé"),
    "unaccented seasonal name": (_set(["pages", 1, "scene"], "Noel magique"), "Compagnon non autorisé"),
    "seasonal symbol family hats": (_set(["pages", 2, "params"], {"family": "hats"}), "valeur non autorisée"),
    "seasonal symbol family gifts": (_set(["pages", 2, "params"], {"family": "gifts"}), "valeur non autorisée"),
    "real theme in text": (_set(["pages", 1, "scene"], "Nuit d'Halloween"), "Compagnon non autorisé"),
    "unknown mechanic": (_set(["pages", 0, "mechanic"], "sudoku"), "mécanique"),
    "param not allowed": (_set(["pages", 0, "params"], {"size": 9}), "paramètre non autorisé"),
    "param value not allowed": (_set(["pages", 1, "params"], {"shape": "dragon"}), "valeur non autorisée"),
    "required param missing": (_set(["pages", 2, "params"], {}), "obligatoire absent"),
    "page numbering gap": (_set(["pages", 1, "page"], 5), "numérotation"),
    "duplicate unit id": (_set(["pages", 1, "unit_id"], "syn-p001"), "doublon"),
    "too many pages": (_many_pages, "pages"),
    "unsupported trim": (_set(["trim", "width_in"], 6), "8.5 x 11"),
    "invisible character": (_set(["pages", 0, "prompt_en"], "Follow​ the corridor."), "invisible"),
    "newline in prompt": (_set(["pages", 0, "prompt_en"], "Follow\nthe corridor."), "retour à la ligne"),
    "prompt too long": (_set(["pages", 0, "prompt_en"], "x" * 200), "caractères"),
    "bad age band": (_set(["age_band"], [5, 4]), "age_band"),
    "bool seed": (_set(["seed"], True), "seed"),
}


@pytest.mark.parametrize("name", sorted(ADVERSARIAL))
def test_adversarial_source_is_refused(name):
    mutator, expected = ADVERSARIAL[name]
    with pytest.raises(ContractError) as info:
        parse_spec_set(mutated(mutator))
    assert expected in str(info.value), str(info.value)


def test_duplicate_json_key_is_refused():
    text = FIXTURE.read_text(encoding="utf-8").replace('"seed": 2026,', '"seed": 2026, "seed": 7,')
    with pytest.raises(ContractError, match="JSON strict"):
        parse_spec_set(text.encode())


def test_non_finite_number_is_refused():
    text = FIXTURE.read_text(encoding="utf-8").replace('"seed": 2026', '"seed": NaN')
    with pytest.raises(ContractError, match="JSON strict"):
        parse_spec_set(text.encode())


def test_oversized_and_malformed_sources_are_refused():
    with pytest.raises(ContractError):
        parse_spec_set(b" " * (MAX_SOURCE_BYTES + 1))
    with pytest.raises(ContractError):
        parse_spec_set(b"[1, 2]")
    with pytest.raises(ContractError):
        parse_spec_set(b"\xff\xfe not utf-8")


def test_symlinked_source_is_refused(tmp_path):
    link = tmp_path / "link.json"
    link.symlink_to(FIXTURE)
    with pytest.raises(ContractError, match="lien symbolique"):
        load_spec_set(link)


def test_all_errors_are_reported_together():
    payload = dumps({**spec_dict(), "kind": "X", "spec_id": "bad"})
    with pytest.raises(ContractError) as info:
        parse_spec_set(payload)
    assert len(info.value.errors) >= 2
