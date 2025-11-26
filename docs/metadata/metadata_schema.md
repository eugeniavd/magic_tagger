# Metadata Schema — Corpus A Index

This document describes the fields used in the corpus index for Russian folktales from the Estonian Folklore Archive.  
For each field we provide: **name**, **description**, **allowed values / format**, and an **example**.

## General conventions

- **Language of field names and descriptions**
  - Field names (`tale_id`, `collection`, …) are in English and use `lower_snake_case`.
  - Descriptions in this document are in English.
  - Field values may be in Estonian and/or Russian if they reproduce archival wording (e.g., place names, short content notes, narrator information).

- **Scripts and transliteration**
  - Original scripts are preserved: Estonian in Latin, Russian in Cyrillic.
  - No mandatory transliteration layer is stored in this index; any Latin transliteration for Russian names or toponyms can be maintained in a separate derived dataset if needed.
  - Identifiers such as `tale_id` use only ASCII characters.

- **Empty values and missing data**
  - If the archive does not provide a value or a field is not applicable, the cell is left empty.
  - At this research step we do not insert `0`, `NA`, `NULL`, or `unknown` as literal strings.
  - Multiple values (collectors, genres, type codes) are split across numbered fields (`collector_1`–`collector_5`, `genre_1`–`genre_3`, `type_code_1`–`type_code_4`).  
    If there are fewer values than the maximum, remaining fields stay empty.

- **Uncertain and partial dates**
  - When the exact recording date is known, we use the full ISO format: `YYYY-MM-DD`.
  - When only the year is known, we use `YYYY`.
  - When year and month are known, we use `YYYY-MM`.
  - If the date is approximate (e.g. “1920s”, “around 1930”) or unclear, we leave the date fields empty and keep the original wording in project notes or auxiliary documentation.
  - `recorded_date_start` and `recorded_date_end` always refer to the period when the tale was recorded, not when it was digitised or processed.

## Fields

| Field name | Description | Allowed values / format | Example |
|-----------|-------------|-------------------------|---------|
| `tale_id` | Stable, human-readable identifier for the tale within the research corpus. Encodes collection, volume, page and local tale number. | String without spaces; pattern like `era_vene_<volume>_<page>_<tale_no>`. Minted by the project and remains stable across versions. | `era_vene_1_309_38` |
| `collection` | Archival collection / series where the manuscript is stored. | Controlled vocabulary. Currently: `ERA, Vene` (pre-war Russian series), `RKM, Vene` (post-war Russian series), `TRÜ, VKK` (Tartu University Russian folklore collection). | `ERA, Vene` |
| `volume_no` | Volume number within the given collection. | Integer (stored as string). Sequential per collection. | `1` |
| `source_ref` | Full archival shelfmark pointing to the tale in the physical or scanned manuscript: collection, volume, page / entry, local tale number in parentheses. | Free text string following archive conventions, typically: `<collection> <volume>, <page>/<entry> (<tale_no>)`. | `ERA, Vene 1, 309/20 (38)` |
| `digital_carrier` | What kind of digital representation exists for this tale in the project workspace. | Controlled vocabulary. Currently used values: `scan_only` (only scan available), `transcript_only` (only transcription available). Extensible if new carriers appear. | `scan_only` |
| `rights_status` | Reuse and visibility status of the tale in the research corpus. | Controlled vocabulary. Example values: `open` (can be quoted and visualised with proper attribution), `restricted_anon` (content can be used in analysis, but narrators/collectors must be anonymised or hidden in public outputs). | `open` |
| `narrator` | Narrator’s name and, where available, biographical note as recorded in the manuscript (may be multilingual). | Free text. Can include labels like `Nimi:` (name), `Vanus/Sünniaasta:` (age/year of birth), religion, occupation etc. This composite field will later be split into separate attributes (name, age, occupation, etc.) for the knowledge graph. | `Nimi: Авдотья Петровна Бабина, Vanus/Sünniaasta: …` |
| `collector_1` | Primary collector who recorded the tale. | Personal name as free text; use full name where possible. Many manuscripts were recorded by groups of fieldworkers, and a single volume may list up to five collectors; for this reason, we provide up to five separate collector fields. | `Paul Ariste` |
| `collector_2` | Second collector (if applicable), e.g. assistant, student or co-recorder. | Personal name as free text; empty if not applicable. | `А. Малтс` |
| `collector_3` | Third collector (if applicable). | Personal name as free text; empty if not applicable. | `Н. В. Решетилова` |
| `collector_4` | Fourth collector (if applicable). | Personal name as free text; empty if not applicable. | `Т. Р. Сула` |
| `collector_5` | Fifth collector (if applicable). | Personal name as free text; empty if not applicable. | `С. Семененко` |
| `narrator_school` | School or educational institution associated with the narrator (mainly in collections recorded via pupils). | Free text, usually original archive wording; may contain class/grade information. | `Черновское Русское Начальное Училище, 6 кл.` |
| `recording_parish` | Parish (or comparable administrative unit) where the tale was recorded. | The place name is stored here in the original archival language; an English version of the parish/place name will be provided in a separate field for use in the knowledge graph and user interface. | `Torma khk.` |
| `recording_place` | Settlement / village where the tale was recorded. | Free text, often combining Estonian and Russian place names and abbreviations like `v.` (village), `k.` (settlement)., an English version of the parish/place name will be provided in a separate field for use in the knowledge graph and user interface| `Kasepää v., Raja (Раюша) k.` |
| `narrator_origin_parish` | Parish of the narrator’s origin (may differ from recording parish if narrator migrated). | an English version of the parish name will be provided in a separate field for use in the knowledge graph and user interface | `Petserimaa` |
| `narrator_origin_place` | Settlement of the narrator’s origin. | Free text, may be in Estonian or Russian. An English version of the place name will be provided in a separate field for use in the knowledge graph and user interface | `Petseri l.` |
| `recorded_date_start` | Earliest date of recording of this tale; for multi-day recordings, the start date. | Date in ISO format `YYYY-MM-DD`. Partial dates allowed as `YYYY` or `YYYY-MM` when full date is unknown. Unknown dates are left empty. | `1929-07-27` |
| `recorded_date_end` | Latest date of recording of this tale; for multi-day recordings, the end date. For single-day recordings can coincide with `recorded_date_start`. | Date in ISO format `YYYY-MM-DD`. Partial dates allowed as `YYYY` or `YYYY-MM` when full date is unknown. Unknown dates are left empty. | `1938-08-25` |
| `content_description` | Short content note indicating main character or plot; usually in Russian. | The content description is kept in the original archival language; an English translation or summary will be provided in separate fields to support interoperability with other datasets and tools. | `[А]()_
| `genre_1` | Primary genre label assigned in the archive’s system. | Controlled vocabulary of ERA genre terms (Estonian), e.g. `muinasjutt`, `muistend`, `andmed`, etc. Single term. | `andmed` |
| `genre_2` | Secondary genre label (if applicable), capturing mixed or overlapping genres. | Controlled vocabulary; same pool as `genre_1`. Empty if not used. | `muinasjutt` |
| `genre_3` | Tertiary genre label (if applicable). | Controlled vocabulary; same pool as `genre_1`. Empty if not used. | `kõnekäänd` |
| `subgenre` | Subgenre within the main folk-tale genre, following folkloristic categories used in the Archive. | Controlled vocabulary of subgenre terms (Estonian). | `imemuinasjutt` |
| `folklore_category` | More fine-grained folkloristic category for the tale, often combining genre and thematic type. | Controlled vocabulary of Estonian labels (e.g. `legendiline muinasjutt`, `novellmuinasjutt`, `loomamuinasjutt`, etc.). | `legendiline muinasjutt` |
| `type_code_1` | Primary classification code for the tale (usually ATU number; may include other systems). | String; may contain digits, letters and symbols. Can encode ATU types, Estonian national types, or Russian national types. Example patterns: `706`, `300`, `365`, `vrd Ee 424*`. | `706` |
| `type_code_2` | Secondary classification code, often alternative or additional ATU or national-type number. | Same format as `type_code_1`. Empty if the tale has only one code. | `530A` |
| `type_code_3` | Tertiary classification code, e.g. SUS (East-Slavic) numbers or further parallels. | Same format as `type_code_1`. Can include prefixes like `SUS`, suffix `*`. | `SUS 1060*` |
| `type_code_4` | Quaternary classification code, for additional variants, parallels or local catalogue references. | Same format as `type_code_1`. | `556А*` |
