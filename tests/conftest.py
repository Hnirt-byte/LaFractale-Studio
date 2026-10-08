from pathlib import Path
import pytest
from lafractale.config.schema import load_book
from lafractale.story.plan import demo_specs
from lafractale.activities.engine import generate,stable_seed

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def halloween():
    return load_book(ROOT/"books/halloween_2026/book.yaml")

@pytest.fixture
def activities(halloween):
    return [generate(spec,stable_seed(halloween.book_id,spec.id,2026)) for spec in demo_specs(halloween)]
