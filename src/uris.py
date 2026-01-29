"""
Canonical IRI / namespace helpers for MagicTagger.

Single source of truth:
- Ontology terms (TBox):  RFT_NS = .../rdf/ontology#
- Data/resources (ABox):  BASE_DATA = .../rdf/

Rules:
- Custom classes/properties always use RFT_NS (hash namespace).
- Instances/artifacts always use BASE_DATA + <path>/<id> (slash IRIs).
- raw.githubusercontent.com URLs are *distribution* URLs, never namespaces.
"""

from __future__ import annotations
from rdflib import Namespace, URIRef

# ---------------------------------------------------------------------
# Canonical roots 
# ---------------------------------------------------------------------

ROOT: str = "https://eugeniavd.github.io/magic_tagger/rdf/"
ONT_IRI: str = ROOT.rstrip("/") + "/ontology"  
RFT_IRI: str = ONT_IRI + "#"                    
BASE_DATA: str = ROOT     

# rdflib namespaces
RFT = Namespace(RFT_IRI)
DATA = Namespace(BASE_DATA)

def iri_person(person_id_or_slug: str) -> URIRef:
    return URIRef(f"{BASE_DATA.rstrip('/')}/person/{person_id_or_slug}")