# Permissions & Licensing (v1.0 (pseudonymised))

## 0. Scope & Status
- Corpus A (Local Gold): Estonian Folklore Archive subset (mounted locally).
- Corpus B (External, optional): FEB — Afanasyev mirror (context-only retrieval).

## 1. Licenses
- **Software (code):** AGPL-3.0-only.
- **Derived transcriptions & metadata:** We release derived transcriptions and metadata under Creative Commons Attribution 4.0 International (CC BY 4.0). 
- **Scans/images:** governed by Estonian Folklore Archive policies.
- **External Corpus B:** subject to its own terms; used read-only for retrieval; external snippets are labeled “B: External”.

## 2. Privacy & Anonymization Policy (Corpus A)
- Masking rules for collectors/narrators when required; pseudonym schema.
- Versioned policy file included with the app (see §7 Versioning).

Until the archive issues a decision on public disclosure of personal names, narrators and collectors are published in pseudonymised form:

**schema**: Person entries expose stable pseudonymous IDs (e.g., nar002, col056) and non-identifying attributes only. The name mapping table is held by the archive and is not shipped in this repository or exports. This interim policy aims to balance Open Science (CC BY 4.0) with personal data minimisation.

When/if disclosure is approved, we will publish a versioned update (see §7 Versioning) with named persons; prior pseudonymised versions remain available for provenance.

*Community Norms (Ethical Use)*
CC BY 4.0 permits reuse; however, we ask users to refrain from any re-identification attempts and to contact the archive for legitimate scholarly requests concerning identified persons. Users remain responsible for compliance with applicable privacy laws.

## 3. Quotation Policy (External Corpus B)
- Quote-length cap per external source; disable-quotes switch available.

## 4. Source Badges & Ordering
- Everywhere in UI/exports: badge **A** = Archive (Corpus A), **B** = External (Corpus B).
- Lists order: **A first**, then B.

## 5. FAIR / LOD in Exports
- Stable IRIs; per-item **JSON-LD** and batch **Turtle (.ttl)**.
- Required fields:
  - `dc:rights`: **“CC BY 4.0 (derived data); scans per archive policy”**
  - `dcterms:license`: https://creativecommons.org/licenses/by/4.0/
  - `dc:source`: accession/call number (e.g., *ERA, Vene 13, 635/8 (20)*)

## 7. Versioning & Distribution
- This policy file is versioned; exports reference exact policy version (e.g., `policy_version: v1.0`).
- Bundled into Docker image and repository; license labels baked into images.

## 8. Contact
- Rights & permissions: evgeniia.vdovichenko@studio.unibo.it.
