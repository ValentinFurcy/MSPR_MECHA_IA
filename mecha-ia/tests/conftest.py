"""Assure que la racine du repo est sur sys.path pour `from src.cleaning import ...`,
quel que soit le répertoire depuis lequel pytest est lancé (local ou CI)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
