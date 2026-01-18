# rdf/build_kg.py
from __future__ import annotations

import re
from urllib.parse import quote

from rdf.kg_helpers import all

# Single source of truth for all IRIs in the project.

BASE = "https://github.com/eugeniavd/magic_tagger/rdf/"

_ATU_WS = re.compile(r"\s+")
_ATU_OK = re.compile(r"^[A-Z0-9-]+$")
