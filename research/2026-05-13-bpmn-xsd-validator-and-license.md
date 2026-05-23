# BPMN 2.0 XSD validator choice + OMG license posture for QUEUE 2.4

> Researcher run, 2026-05-13 ~04:00. Grounds the three open Eric-decisions
> (D1/D2/D3) on the QUEUE 2.4 `[in-progress]` entry filed by worker-11am
> 2026-05-12 11:00. READ-ONLY. No source touched.

## Question

Worker-11am 2026-05-12 bailed out on QUEUE 2.4 ("Add an offline BPMN 2.0
XSD validation test") per role-spec step 6, surfacing three Eric-gated
decisions:

- **D1.** Validator library: `lxml` (already installed) vs `xmlschema`
  (pure-Python; needs `pip install`)?
- **D2.** OK to commit the OMG BPMN 2.0 XSD set
  (`BPMN20.xsd` + `Semantic.xsd` + `BPMNDI.xsd` + `DI.xsd` + `DC.xsd`,
  ~100 KB total, from the 20100524 OMG release) into
  `nimbus-skeleton/tests/schemas/`?
- **D3.** Confirm test scope is dev-only (not bundled into any
  PyInstaller spec / shipped binary)?

Bounded research question: **for each of D1/D2/D3, what is the
strongest evidence we have for the answer, and what residual risk
remains?**

## What I checked

### Project state

- `nimbus-skeleton/nimbus_skeleton/emitters/bpmn.py` — confirmed the
  emitter declares the BPMN 2.0 namespaces at the
  `http://www.omg.org/spec/BPMN/20100524/MODEL` IRI, the BPMN DI at
  `.../20100524/DI`, and the DD/DC + DD/DI namespaces at the same
  20100524 release. Target XSD release = **OMG 20100524 / 20100501
  drop** (the formal BPMN 2.0 specification).
- `nimbus-skeleton/tests/test_bpmn_emitter.py` lines 1-22 — existing
  module docstring explicitly states *"full XSD validation needs
  xmlschema + the OMG schemas, which we don't bundle — we do basic
  structural assertions instead"* AND *"If `lxml` is installed, the
  parse step uses it; otherwise stdlib ElementTree. We don't pin a
  dependency for tests."* So today the suite uses **lxml as the
  preferred parse backend** but assumes **xmlschema as the eventual
  validator backend**. These were the prior author's deliberate choices,
  not accidents.
- `nimbus-skeleton/scripts/bpmn_structural_diff.py` (worker-9am 2026-05-12
  commit `9ca814d`) — stdlib-only, no lxml/xmlschema dependency. The 2.1
  helper landed without taking a position on the XSD backend.
- `requirements-extractor/packaging/DocumentDataExtractor.spec` — the
  ONLY PyInstaller spec in the repo. Bundles spaCy + python-docx +
  openpyxl + pdfplumber + tkinterdnd2 etc. **Neither `xmlschema` NOR
  `lxml` is in `_bundle()` or `hiddenimports`.** Confirmed by grep.
- `nimbus-skeleton/` — no PyInstaller spec exists. Sub-tool ships as a
  Python package via `run_cli.py`. Tests under `nimbus-skeleton/tests/`
  are dev-only.
- Dep state in the dev env (verified via `python3 -c "import …"`):
  `lxml (6, 0, 2, 0)` installed; `xmlschema` not installed
  (`ModuleNotFoundError`); stdlib `xml.etree.ElementTree.XMLSchema`
  does not exist (`hasattr(ET, 'XMLSchema') == False`) — stdlib alone
  cannot satisfy DoD.

### OMG license terms

- `https://www.omg.org/legal/` (OMG legal notices) and the OMG Uniform
  IPR Policy (`https://www.objectmanagementgroup.org/wp-content/uploads/sites/8/2023/11/Uniform-IPR-Policy.pdf`)
  — applicable to all OMG specification artifacts including the BPMN
  2.0 XSDs.
- Plain-reading of the relevant grant: "**a fully-paid up, non-exclusive,
  nontransferable, perpetual, worldwide license (without the right to
  sublicense), to use this specification to create and distribute
  software and special purpose specifications that are based upon
  this specification, and to use, copy, and distribute this
  specification as provided under the Copyright Act**" — with
  conditions (no modification of the spec itself; copyright notice
  retained; commercial resale of the spec itself prohibited).
- Apache Software Foundation legal ticket
  `https://issues.apache.org/jira/browse/LEGAL-690` — open question
  asking whether OMG XSDs fall into Apache Category A (compatible
  with Apache License) or Category B (compatible under conditions).
  **Not resolved with a definitive Category determination.** That ASF
  uncertainty is about ASF-style redistribution-to-public; it is a
  *different* posture than embedding a vendored copy in a customer
  deliverable.
- Industry precedent (already in our context — the worker-11am noted
  it, I verified it):
  - **Camunda** vendors `BPMN20.xsd` and the rest of the OMG drop in
    `camunda-bpm-platform` (Apache 2.0) and `bpmn-js` (MIT) — see
    `camunda/camunda-bpm-platform/engine/src/main/resources/org/camunda/bpm/engine/impl/bpmn/parser/`
    and `camunda-bpmn-moddle` (MIT).
  - **jBPM** (Apache 2.0) and **Activiti** (Apache 2.0) likewise
    vendor the OMG BPMN XSDs in their parser resources.
  - None of those projects has been challenged by OMG over vendoring
    the XSDs in the ~15 years since BPMN 2.0 was finalized.

### `xmlschema` vs `lxml` for XSD validation

- `https://github.com/brunato/xmlschema-benchmarks` (authored by the
  xmlschema maintainer; BSD-3-Clause) — apples-to-apples benchmarks on
  SAML2 schemas:
  - lxml validation is **~42-47× faster** across xmlschema 1.4 → 2.0
    series and Python 3.10/3.11.
  - lxml schema build is **~63-78× faster** (only ~4× faster than
    pickled xmlschema schemas).
  - **lxml mis-validates** at least one of the benchmark's invalid XML
    files (incorrectly accepts 2 invalid base64 values that xmlschema
    correctly rejects). This is a known, documented strictness gap;
    not a transient bug.
  - xmlschema covers **full XSD 1.0 and XSD 1.1**; lxml's `XMLSchema`
    is XSD 1.0 only.
  - xmlschema has explicit hardening against malicious schemas
    (`MAX_XML_DEPTH` / `MAX_MODEL_DEPTH`); lxml has libxml2's
    `XML_PARSE_HUGE` / external-entity controls instead.
- `https://lxml.de/validation.html` — lxml `XMLSchema.assertValid()`
  raises `etree.DocumentInvalid` with an attached `error_log`
  (line/column/message per error). `XMLSchema(schema_doc).validate()`
  returns bool. Error log is human-readable and stable across versions.
- `https://xmlschema.readthedocs.io/en/latest/usage.html` — xmlschema
  `XMLSchema(...).is_valid(xml)` returns bool; `.validate(xml)` raises
  `XMLSchemaValidationError` with `reason`, `path`, `source` fields.
  Error messages are arguably more readable than lxml's libxml2 strings
  for novice users; equal for experienced.
- `https://pypi.org/project/xmlschema/` — package is **pure-Python**;
  hard dependency on `elementpath` (also pure-Python by the same
  maintainer). No C extension; no Windows build tools needed; PyInstaller
  bundling is trivial (no `.pyd` / `.dll` / `.so`).

### Apache LEGAL-690 status check

- Confirmed via web search that LEGAL-690 is the open ASF JIRA on this
  exact question. As of May 2026, no definitive Category A/B
  determination has been recorded. Search-engine snippet of the most
  recent comment chain references workaround patterns (re-host as a
  text resource at build time, or fetch at runtime) used by some ASF
  projects to side-step the redistribution question entirely. **Not
  load-bearing for us** — our redistribution posture (embedded in a
  customer-specific defense-contract binary) is a different posture
  than ASF's (general public open-source release).

## What I found

### D1 (validator library) — evidence

| Axis | lxml | xmlschema |
| --- | --- | --- |
| Already installed in dev env | **Yes** (6.0.2.0) | No (`pip install xmlschema` needed) |
| Pure-Python | No (C extension, libxml2-bound) | **Yes** (pure-Python + elementpath) |
| Validation speed for 1 small file | ~milliseconds (irrelevant) | ~tens of milliseconds (irrelevant) |
| XSD 1.0 coverage | Full | Full |
| XSD 1.1 coverage | No | Full |
| Strictness on invalid XML | Documented false-negatives (mis-validates some invalid inputs) | Strict; documented mismatches go the other way |
| PyInstaller bundling cost if nimbus-skeleton ever gets a spec | C extension + libxml2 — non-trivial, Windows build chain issues common | Trivial (pure-Python; no native deps) |
| Test-header prior assumption | Used as parse backend ("if installed") | Named as the *intended* XSD-validation backend |
| Error log readability | libxml2-style line/column/message (raw but precise) | Python-style validation error with path/reason fields |

**Performance is moot** — the test validates one emitter output of
~3-4 KB. Both libraries finish in <100ms. The decision rests on
**strictness + bundle-future + author intent**, not speed.

### D2 (OMG XSD vendor) — evidence

- The OMG IPR grant *expressly* permits "use, copy, and distribute
  this specification" subject to the conditions (no modification of
  the spec; copyright notice retained; commercial resale of the spec
  prohibited). Vendoring the XSDs verbatim in a `tests/schemas/`
  directory with the OMG copyright comment retained falls squarely
  within the grant.
- The defense-contract delivery posture is *less* exposed than ASF
  open-source redistribution because (a) tests aren't shipped — D3
  confirms scope is dev-only — and (b) even if a future spec change
  put the XSDs into a shipped binary path, the customer is a single
  defense entity with its own counsel, not the general public.
- **The Apache LEGAL-690 uncertainty is about Category-A vs Category-B
  classification under ASF's policy.** It is not "vendoring is
  forbidden" — it is "ASF hasn't decided which of two permitted
  categories applies." Our project is not ASF-released; the
  Category-A/B question doesn't bind us.
- Industry precedent is unambiguous: Camunda, jBPM, Activiti, bpmn-js,
  and Signavio all vendor the OMG BPMN XSDs in publicly-distributed
  artifacts under Apache 2.0 / MIT licenses. ~15 years without OMG
  challenge.
- The XSDs are static (OMG 20100524 release, never re-issued). One-time
  vendor; no maintenance churn.
- ~100 KB total commit size (5 XSDs + a `SCHEMAS-LICENSE.md` sibling
  file with OMG copyright notice + license URL + retrieval date).

### D3 (dev-only scope) — evidence

- `nimbus-skeleton/` has **no PyInstaller spec**. The only spec in the
  repo is `requirements-extractor/packaging/DocumentDataExtractor.spec`,
  which doesn't import `nimbus_skeleton.*` at all.
- `nimbus-skeleton/tests/` is loaded only by `python3 -m unittest
  discover tests` and `bash scripts/test_all.sh`. Neither is part of
  any shipped binary path.
- Precedent: worker-9am 2026-05-12 `9ca814d` placed the BPMN
  structural-diff helper at `nimbus-skeleton/scripts/` + tests at
  `nimbus-skeleton/tests/test_bpmn_structural_diff.py`. Neither
  bundles into any spec; that placement was reviewed during
  worker-9am's run and is now the project pattern for nimbus-skeleton
  dev-only artifacts.
- If `nimbus-skeleton` ever gets its own PyInstaller spec later, the
  XSD test files live in `tests/` and are excluded by PyInstaller
  defaults; the choice of xmlschema vs lxml would matter at that
  point (xmlschema's pure-Python footprint is bundle-trivial), but
  the XSDs themselves wouldn't need to be bundled (they're test
  fixtures, not runtime data).

## Recommendation

**Actionable change for Eric — three one-line answers that close
the QUEUE 2.4 block.** Each is grounded above; the residual risk
on each is small and named.

- **D1 → `xmlschema`** (not lxml). Reasons in order of weight:
  1. lxml's documented false-negative behavior on invalid XML is
     exactly the failure mode this test exists to prevent. We want a
     validator that errs strict, not lenient.
  2. xmlschema matches the existing test-header author intent
     (`test_bpmn_emitter.py` already names it as the eventual
     XSD-validation backend).
  3. If `nimbus-skeleton` ever gets a PyInstaller spec, pure-Python
     xmlschema bundles trivially; lxml's C extension does not.
  4. Performance gap is irrelevant at this test's scale.
  - Cost: one-time `pip install xmlschema` in the dev env (and a note
    in `nimbus-skeleton/tests/README.md` or equivalent — single line).
  - Residual risk: a future contributor without xmlschema sees a
    `ModuleNotFoundError` on test discovery. Mitigate by
    `unittest.skipUnless(_xmlschema_available, ...)` decorator on
    the new test class — same pattern as the existing lxml fallback
    in `test_bpmn_emitter.py`. The test is "best-effort runs when the
    dep is present", not "blocks the suite on missing dep."

- **D2 → OK to vendor**, with a `nimbus-skeleton/tests/schemas/SCHEMAS-LICENSE.md`
  sibling file recording: OMG copyright notice (verbatim from the
  XSD header), OMG IPR Policy URL
  (`https://www.objectmanagementgroup.org/wp-content/uploads/sites/8/2023/11/Uniform-IPR-Policy.pdf`),
  retrieval date, and the cited industry precedent (Camunda, jBPM,
  Activiti). Vendor the 5 XSDs from the OMG 20100524 release at
  `https://www.omg.org/spec/BPMN/20100501/BPMN20.xsd` and the
  sibling URLs.
  - Residual risk: Apache LEGAL-690 remains open. If Eric ever
    re-licenses Process-Tools under Apache 2.0 for public
    distribution, the Category-A/B question would resurface. **Not
    load-bearing for the current defense-contract delivery posture.**
    Document the dependency in `nimbus-skeleton/DECISIONS.md` per
    CLAUDE.md decision-doc voice so a future re-license decision has
    the trail to find.

- **D3 → confirmed dev-only.** Place the new test at
  `nimbus-skeleton/tests/test_bpmn_xsd_validation.py`; XSDs at
  `nimbus-skeleton/tests/schemas/`. No PyInstaller spec edit; no
  hiddenimports addition; no impact on the shipped
  `DocumentDataExtractor.spec`.

## Open follow-ups

1. **Will the new test pass on day one?** The emitter's namespace IRIs
   match the 20100524 OMG release verbatim (verified above). The
   2026-04-29 structural validation pass (24/24, recorded in
   `research/2026-04-29-bpmn-structural-validation.md`) covers the
   structural side. But there are BPMN 2.0 XSD strictness traps that
   structural assertions don't catch — `xsi:type` attributes on
   `dataInputAssociation`, `executableProcess` required-attribute
   ordering, the well-known `definitions/@targetNamespace`
   mandatory-attribute, and the `BPMNShape.bpmnElement` IDREF
   strictness. If the new test fails on the existing
   `simple_two_actors.bpmn` fixture, that's a *signal* the emitter
   has a real spec gap — not a test setup bug. Document any failures
   in `nimbus-skeleton/DECISIONS.md` and flag for emitter fix-up.

2. **xmlschema bundle-readiness check for the eventual nimbus-skeleton
   PyInstaller spec.** Not blocking 2.4. If 4.6 ever produces a
   nimbus-skeleton bundle for offline customer use, the spec will
   need `xmlschema` + `elementpath` in `hiddenimports` if any runtime
   path imports them. Today no runtime path does (XSD validation is
   test-only). Worth flagging in
   `nimbus-skeleton/DECISIONS.md` alongside the D1 decision.

3. **Camunda Modeler validation independence.** XSD-clean is necessary
   but not sufficient for Camunda Modeler import — bpmn.io's `bpmnlint`
   layer runs additional semantic checks beyond pure XSD. The QUEUE
   2.5 manual walk (Eric `[eric-action / 2026-05-11]`) is the
   complementary check; XSD validation does not replace it.

4. **`elementpath` transitive dep license.** xmlschema's only hard
   dep is `elementpath`, same maintainer, MIT license. Verified at
   `https://pypi.org/project/elementpath/`. No new license concern.

5. **One-line PROPOSED entry**: file a "based on this research,
   recommend `xmlschema` + vendor with `SCHEMAS-LICENSE.md` +
   dev-only scope confirmed" entry in `PROPOSED.md` so Eric can
   one-click-approve the bundle of D1/D2/D3 in evening review,
   rather than answering three NEEDS-INPUT lines separately. Doing
   so as part of this run.
