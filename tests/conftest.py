from pathlib import Path

import pytest

POEMAS = Path(__file__).parent / "poemas"


@pytest.fixture
def poema():
    def cargar(nombre: str) -> str:
        return (POEMAS / f"{nombre}.txt").read_text(encoding="utf-8")

    return cargar
