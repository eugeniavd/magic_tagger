# Transcription_guidelines.md  

## Guidelines for TEI Transcription of Russian Folktale Manuscripts ("TRÜ, VKK" collection)

These guidelines describe how the TRÜ, VKK folktale manuscripts are transcribed and encoded in TEI-XML for the project “Unlocking Russian Folklore”. They focus on the phonetic layer that preserves the collector’s notation. Orthographic normalization and other NLP-oriented transformations will be implemented in a subsequent project stage and are not part of the present transcription workflow.

All TEI files in this repository have been checked for XML well-formedness using an online XML validator (FreeFormatter XML Validator). 

## 1. Scope and goals

Our transcription aims to:

- Preserve collector’s phonetic notation as faithfully as possible.  
- Make graphic signs and diacritics machine-readable.  
- Distinguish clearly between:  
  - **Collector’s notation** (what is on the manuscript),  
  - **Editorial interventions** (what we add or correct),  
  - **Normalized orthographic layer** (for NLP, generated later).

The guidelines apply to all TEI files in the TRÜ, VKK subset. All files are encoded as **UTF-8** and conform to **TEI P5**.


## 2. Preserved text features 

In the primary transcription layer we preserve the following features :

1. **Punctuation**  
   - All punctuation marks written by the collector: `. , : ; ? !` and dashes `—` (if present).  
   - Performance pauses are encoded separately (see §4.6) and are **not** converted into commas or periods.

2. **Stress**  
   - Stress marks are preserved and encoded as `<hi>` with `@rendition="#accent"`.  
   - In Unicode, stress is represented by `U+0301 COMBINING ACUTE ACCENT`, but in TEI we refer to the custom character via `charDecl` and `rendition`.  
   - Example:  
     ```xml
     Б<hi rendition="#accent">ы</hi>ла
     ```

3. **Length**  
   - Vowel or consonant length marks are preserved and encoded as `<hi>` with `@rendition="#long"`.  
   - Unicode mapping: `U+0304 COMBINING MACRON`.  
   - Example:  
     ```xml
     г<hi rendition="#long">о</hi>дъ
     ```

4. **Palatalization**  
   - Palatalization marks after consonants are encoded as `<hi>` with `@rendition="#pal"`
   - Unicode mapping: `U+02B9`.  
   - Example:  
     ```xml
     а<hi rendition="#pal">т</hi>ец
     ```

5. **Reduced vowels**  
   - Underbar marks (often indicating syllabic consonants or reduced vowels) are encoded as `<hi>` with `@rendition="#underbar"`.  
   - Unicode mapping: `U+0332 COMBINING LOW LINE`.  
   - Example:  
     ```xml
     а<hi rendition="#underbar">н</hi>
     ```

6. **Under-arc between words**  
   - Under-arc joining words is encoded as a graphic sign using `<g>` with `@ref="#underparenChar"` and `@place="below"`.  
   - Unicode mapping: `U+203F UNDERTIE`.  
   - Example:  
     ```xml
     в<g ref="#underparenChar" place="below"/>бат</hi>ки
     ```

7. **Pauses**  
   - Short pauses `|` and long pauses `‖` are retained as `<pause>` elements with `@rendition="#pause1"` or `@rendition="#pause2"`.  
   - Unicode mapping: `U+007C` and `U+2016`. 
   - Example:  
     ```xml
     гаварит<pause rendition="#pause1"/>
     ```

8. **Corrections**  
   - Any editorial expansions are encoded as variants.
   - Example: 
   ```xml
     xml <choice><sic>Скаска пра Хаму Брута</sic><corr>Сказка про Хому Брута</corr></choice>
     ```

9. **Dialect forms and non-standard orthography**  
   - Dialectal spellings, phonetic spellings and non-standard forms (e.g. _гава́рит_, _сыно́к_, _ужа́к_) are not normalized in this layer.  
   - We preserve the collector’s spelling, together with associated diacritics and signs.

10. **Graphic emphasis**  
    - Underlining is encoded as `<hi>` with `@rendition="#underline"`.  
    - Superscript letters are encoded as `<hi>` with `@rendition="#sup"`.


## 3. Encoding and character set

### 3.1. Encoding

All TEI files use UTF-8. The XML declaration explicitly states:
<?xml version="1.0" encoding="UTF-8"?>

### 3.2. TEI namespace

The root element declares the TEI namespace:
<TEI xmlns="http://www.tei-c.org/ns/1.0">

### 3.3. Custom characters and renditions

Custom diacritics and signs are declared in <charDecl> and <tagsDecl> within <encodingDesc>:

- <charDecl> defines what the sign is and its Unicode mapping (e.g. `accentChar`, `longChar`, `palChar`).

- <tagsDecl> / rendition defines how it is referenced in the transcription (e.g. #accent, #long, #pal, #underbar, #underparen, #pause1, #pause2).

In the body of the transcription we never insert raw combining characters by hand; instead we always use:

- <hi> with @rendition="#..." for diacritics and emphasis,
<hi rendition="#accent">ы</hi>

- <g> with @ref="#...Char" for graphic signs.
<g ref="#underparenChar" place="below"/>


## 4. Core transcription conventions

### 4.1. Pages and lines: `<pb>` and `<lb>`

We preserve the original manuscript layout:

- **Page breaks**  
  ```xml
  <pb n="12"/>

"@n" holds the page number as written in the manuscript.

- **Line breaks** 
  ```xml
<lb n="04"/>яво к царю Далмату. Дастали
 
"@n" holds a zero-padded line number ("01", "02", …) per page.

Principle: page and line numbering follow the original manuscript and are never renumbered for layout reasons.

### 4.2. Paragraphs and indentation

Paragraphs are grouped in <p>. Manual indentation (e.g. first line of a new episode) is encoded via:

<p rendition="#indent"> ... </p>

### 4.3. Additions and deletions

We distinguish between several types of changes.

1. Collector’s additions

Material added in the manuscript (margin, interline, top of page, etc.) is encoded as <add>, with optional @place and @hand:

<add place="top-right" hand="#hand-collectors">
  <signed>
    <persName xml:lang="ru" role="narrator">
      <surname>Иванова</surname>
      <forename>Клавдия Кирилловна</forename>
    </persName>
  </signed>
  <lb n="a1"/>80 лет.
</add>

2. Deletions (crossed-out text)

Text that is clearly struck out on the manuscript is encoded as <del>. If the deletion is visibly overstruck, we use a rendition such as #overstrike:

<del rendition="#overstrike">о</del>

3. Overwritten corrections: <subst>

Where a collector overwrites one letter/word with another, we use <subst> grouping <del> and <add>:

<subst>
  <del type="letter" rendition="#overwrite">э</del>
  <add place="inline">ъ</add>
</subst>

*Superscript letters (#sup)*

Superscript letters written above the main baseline (e.g. inserted vowels or consonants) are encoded with <hi> and `@rendition="#sup"`.

Example:
ръзли<hi rendition="#sup">е</hi>телис

Here the collector inserted a superscript е above the line; we encode it as <hi rendition="#sup"> to distinguish this graphic behaviour from normal inline letters.

### 4.4. Variants and normalization

We distinguish three logical layers (see §5):

1. Collector’s form: what is literally written.
2. Editorial correction: obvious slips or orthographic standardization.
3. Normalized form: a later, orthographic representation for NLP.

For variant encoding we use <choice> and/or <sic>/<corr>.

If we correct an obvious slip:

<choice>
  <sic>в<hi rendition="#accent">ы</hi>йшл</sic>
  <corr>в<hi rendition="#accent">ы</hi>шел</corr>
</choice>

If we provide a normalized lemma or orthographic form:

<choice>
  <orig>гава<hi rendition="#pal">р</hi><hi rendition="#accent">и</hi>т</orig>
  <reg>говорит</reg>
</choice>

Current practice:
At the current stage, our TEI transcriptions encode only the phonetic/diplomatic layer of the manuscript text. Editorial corrections and normalized forms will be added in subsequent processing stages.

### 4.5. Graphic highlighting
We use <hi> with @rendition to encode diacritics and graphic emphasis:

- Stress: `hi@rendition="#accent"`
- Length: `hi@rendition="#long"`
- Palatalization: `hi@rendition="#pal"`
- Underbar: `hi@rendition="#underbar"`
- Underlining: `hi@rendition="#underline"`

Example:
м<hi rendition="#accent">а</hi>л<hi rendition="#pal">ь</hi>ч<hi rendition="#pal">и</hi>к

### 4.6. Pauses
Performance pauses are treated as distinct units. 

- Short pause (one vertical line on page):
<pause rendition="#pause1"/>

- Long pause (double vertical line):
<pause rendition="#pause2"/>

These pauses are retained in the phonetic TEI edition, will be dropped in normalized exports for NLP (see editorial policy in editorialDecl).


## 5. Layers: collector’s notation, editorial correction, normalized layer

### 5.1. Collector’s notation (primary layer)

The top-priority principle: this layer reflects the manuscript as written.

**Features:**

- Dialect forms and phonetic spellings are preserved.

- Diacritics, underbars, palatalization marks, underties, pauses, and underlining are encoded as described above.

- No silent normalization (we do not silently replace гава́рит with говорит).

This layer is described in <transcriptionDesc> as a phonetic transcription.

### 5.2. Editorial corrections

Will be provided at the later stages of project, interventions arewill be minimal and always marked:

- Use sic / corr or choice for corrections.

- Use <add type="editorial"> for supplied text.

We do not correct dialectal forms; only obvious slips or technical markup errors (e.g. missing closing tag).

### 5.3. Normalized (orthographic) layer

The normalized layer is not stored as the main TEI text in these files. It may appear as <reg> or <corr> inside choice blocks where needed. Full normalized texts for NLP are generated downstream (e.g. in JSON/CSV exports) and documented in separate NLP/normalization guidelines.

**Separation of concerns:**

1. TEI phonetic layer = archival / philological fidelity.
2. Normalized export = derived, machine-friendly text for search and NLP.


## 6. Numbers

### 6.2. Numerals

Numerals are preserved as written. We do not normalize them to words in this layer.


## 7. TEI document structure 

Every file follows a lightweight TEI structure:

<TEI>
  <teiHeader>
    <fileDesc>…</fileDesc>
    <encodingDesc>…</encodingDesc>
    <profileDesc>…</profileDesc>
  </teiHeader>

  <text>
    <body>
      <div type="magic_tale" xml:id="tru_vkk_25_120" n="23">
        <pb n="120"/>
        <p rendition="#indent">
          <lb n="01"/>Б<hi rendition="#accent">ы</hi>ла …
        </p>
        <!-- ... -->
      </div>
    </body>
  </text>
</TEI>

### 7.1. teiHeader

1. **<fileDesc>**

- <titleStmt>: supplied titles in Russian and English; transcription responsibility (<respStmt>).

- <publicationStmt> rights and usage notes.

- <sourceDesc>: archive, collection identifiers, volume references, hand descriptions, date and place of recording.

2. **<encodingDesc>**

- <transcriptionDesc>: declares that the main layer is phonetic.

- <projectDesc>: brief encoding/project note (e.g. pb / lb usage).

- <tagsDecl> and <charDecl>: define diacritics, pauses, and graphic signs.

- <editorialDecl>: summarizes our policy on stress, length, palatalization, pauses, deletions and normalization.

3. **<profileDesc>** 

- <langUsage>: language ident="ru".

- <textClass>: basic classification according to the archive (e.g. genre: SKAZKA).


### 7.2. text / body / div

Each tale is wrapped in a single div, usually with: `@type="magic_tale"`, `@xml:id` derived from the file name, `@n` holding the running volume of the collection.

Inside div:

- Page layout: `pb` + `p` + `lb`.

- Additions (e.g. narrator’s name and age if it is written in the manuscript) may appear before the main page as add blocks.

### 8. Personal names and anonymization

The folktale texts themselves are made available in this repository, but personal names of narrators and collectors are currently subject to archive and privacy considerations. For this reason, all TEI files in the public repository use pseudonymous identifiers instead of real personal names. Narrators and collectors are encoded as:

- `persName @role="narrator" @type="pseudonym" @key="NAR###"`
- `persName @role="collector" @type="pseudonym" @key="COL###"`

A non-public correspondence table between these pseudonyms and actual persons is stored locally by the researcher. Once the archive confirms the final licensing and privacy policy, the TEI files may be updated to restore full personal names, or remain pseudonymised if required.


## 9. Summary for reuse and reproducibility

**1. Faithful phonetic layer**
We encode the collector’s phonetic notation with explicit TEI markup for stress, length, palatalization, pauses, underbars, and graphic signs, without silent normalization.

**2. Clear markup for change and uncertainty**
Handwritten additions, deletions, overwrites and editorial additions are always marked using <add>, <del>, <subst>.

**3. Separated layers**
Collector’s notation and corrections are kept logically distinct, ensuring that:

- Philological work can rely on a stable “as written” layer.
- NLP pipelines can operate on derived normalized texts, documented elsewhere.

**4. Standard TEI structure**
Shared <teiHeader> patterns and <encodingDesc> settings make the files reproducible and interoperable across the corpus.

These guidelines are designed so that another team could recreate the same transcription practice on comparable Russian folklore manuscripts and understand exactly which signs were preserved, how they were encoded, and how they relate to normalized exports.
