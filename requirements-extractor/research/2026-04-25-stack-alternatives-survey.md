# Stack alternatives survey — Process-Tools

> Date: 2026-04-25. Autonomous overnight research pass. No code or
> existing-doc changes; this file is reference material to inform
> future architectural decisions.

The Process-Tools stack (DDE + compliance-matrix + nimbus-skeleton)
has settled into a pattern: stdlib-first, python-docx + openpyxl as
the parser/writer floor, spaCy + `en_core_web_sm` as the NLP ceiling,
PyInstaller for sealed-bundle distribution to a restricted Windows
network, and Tkinter for the GUI. Each tool's README captures the
"why" of those choices well. This file looks outward — what else
is on the table in April 2026, what teams in defense-aerospace are
actually shipping, and where switching costs could pay off.

The rest of this document walks the ten domain areas in turn. Each
section has the same shape: current choice, plausible alternatives,
real-world fit in defense / regulated work, and a recommendation
verb (keep / switch / watch / consider with caveat). A summary table
and the load-bearing call on the offline-NLP question land at the
end.

---

## 1. NLP for actor extraction

**Current choice.** spaCy 3.7.x with `en_core_web_sm` (the small
English pipeline). Bundled into the PyInstaller exe with a pinned
model wheel (`en_core_web_sm-3.7.1-py3-none-any.whl`) so the
target machine — restricted Windows defense network, no outbound
package fetch — never has to download anything. The pydantic v1/v2
hazard around spaCy's transitive deps is a known build-side issue
already documented in `packaging/build-requirements.txt`.

The model is 12–13 MB on disk; the bundled exe weighs 300–450 MB
because spaCy carries `thinc`, `pydantic`, `pydantic_core`, and
`murmurhash` along with it.

**Alternatives in April 2026.**

GLiNER ([urchade/GLiNER](https://github.com/urchade/GLiNER)) is the
most interesting new entrant. It's a bidirectional-transformer NER
trained for *zero-shot* generalisation: at inference time you supply
the entity types as plain English ("operator", "ground system",
"payload subsystem") and the model returns spans with no
fine-tuning. The original arXiv release ([Zaratiana et al., 2023](https://arxiv.org/abs/2311.08526))
showed it outperforming ChatGPT and several fine-tuned LLM baselines
on common NER benchmarks, and the [GLiNER2](https://arxiv.org/html/2507.18546v1)
follow-up adds schema-driven extraction. Models are 50–600 MB
depending on size class. Apache 2.0 licensed. The hugely attractive
property here is that defense-spec actor vocabulary (which is
domain-specific and not covered by `en_core_web_sm`'s OntoNotes
training) becomes a config decision rather than a training task —
and there's a [`gliner-spacy`](https://huggingface.co/spaces/tomaarsen/gliner_medium-v2.1)
bridge that lets it slot into a spaCy pipeline directly.

Flair ([flairNLP/flair](https://github.com/flairNLP/flair)) keeps
showing up at the top of NER accuracy tables — multiple
[head-to-head reviews](https://medium.com/@sapphireduffy/is-flair-a-suitable-alternative-to-spacy-6f55192bfb01)
report Flair beating spaCy out-of-the-box by a meaningful margin.
The cost is speed (Flair is comparatively slower per [CodeTrade's
comparison](https://www.codetrade.io/blog/the-battle-of-the-nlp-libraries-flair-vs-spacy/))
and dependency weight: Flair pulls in PyTorch, which roughly doubles
the bundle size compared to spaCy's `thinc`-based default. For a
batch CLI tool that's fine; for a GUI smoke-tested under "double-click
the exe and wait" UX expectations it's friction.

Stanza (Stanford NLP, [stanza](https://stanfordnlp.github.io/stanza/))
is the third long-standing competitor. Per [spaCy's own benchmarks
page](https://spacy.io/usage/facts-figures), spaCy's accuracy is
within a percentage point or two on standard NER corpora; Stanza is
preferred when you need broader language coverage. For an
English-only defense-document workload that's not a differentiator.

Distilled BERT NER models ([dslim/bert-base-NER](https://huggingface.co/dslim/bert-base-NER),
[DistilBERT NER](https://huggingface.co/docs/transformers/model_doc/distilbert))
are the "transformer baseline" in 2026. DistilBERT specifically
gives 97% of BERT's accuracy at 60% of the size, which is exactly
the trade-off the bundled-distribution constraint asks for. TinyBERT
([Jiao et al.](https://arxiv.org/abs/1909.10351)) is even smaller —
4-layer model, 7.5× smaller than BERT-base, 96.8% of GLUE
performance. Both run on CPU, both ship via Hugging Face's
`transformers`. The integration cost is heavier than spaCy: tokenizer
+ model + label-aligner + entity-merging logic, all of which spaCy
already encapsulates.

LLM-based extraction with structured output (Outlines, Instructor)
is the 2026-fashionable answer to extraction problems generally.
[Outlines](https://github.com/dottxt-ai/outlines) does
constrained-grammar generation against any HuggingFace model and
guarantees schema-valid output without retries; [Instructor](https://python.useinstructor.com/)
wraps LLM providers with Pydantic validation. Both look great on a
slide. For an offline defense network, the local-model path is
real but heavy: a usable open-weight model (Llama-3.1-8B or similar)
is ~5–8 GB after quantisation, and inference latency on a CPU-only
target machine is seconds per requirement. This is not a viable
runtime path for the DDE workload (DDE processes thousands of
requirements per spec). It's an interesting *enrichment* layer for
a connected-machine workflow — generate richer actor metadata
upstream, persist into the DDE actors xlsx, ship the xlsx through
to the offline machine.

**Real-world fit in defense.** SpaCy and HF transformers are both
well-established in defense-adjacent NLP work — the
[bio-medical / clinical NER repo](https://github.com/magesh-technovator/bio-medical-clinical-ner)
is a representative pattern: same NER comparison playbook (spaCy,
Stanza, Flair) applied to a regulated domain. GLiNER is the new
entrant; usage in defense is still emerging and primarily appears in
academic papers rather than in named-vendor stacks. Distilled BERT
flavours are common in air-gapped LLM deployments
([Anchore's DoD DevSecOps writeup](https://anchore.com/blog/dod-devsecops-air-gap-environment/),
[DataCouch](https://datacouch.io/zero-trust-ai-infrastructure/)) but
mostly for free-text classification rather than NER specifically.

**Recommendation: keep spaCy, but invest in the rule-based fallback
path as the load-bearing layer.** This is covered in detail in the
load-bearing call-out near the end. GLiNER is worth a watch — the
zero-shot vocabulary configurability is a genuine fit for defense
specs that use domain-specific actor names — but bundling it via
PyInstaller into a 300+ MB exe doesn't yet have the field-tested
recipe spaCy does, and FIELD_NOTES already shows the work-network
team treats NLP availability as the failure-prone link. Rule-based
robustness compounds even when the bundled NLP works.

---

## 2. Document parsing for `.docx` and `.pdf`

**Current choice.** `python-docx >=1.1,<2` (pinned) for `.docx`,
`pdfplumber >=0.10` for `.pdf` (optional dep), and a LibreOffice
`soffice --headless` shell-out for legacy `.doc`. The python-docx
private-API exposure (`_tc`, `_p`) was already centralised behind
`_cell_element` / `_paragraph_element` helpers in `parser.py` per
REVIEW §2.7.

**Alternatives.**

[Mammoth](https://github.com/mwilliamson/python-mammoth) is targeted
at converting `.docx` to clean, semantic HTML. It's actively
maintained, simple, and good at preserving heading-style mappings.
The wrong tool for DDE: DDE wants the underlying tree with table
geometry preserved, and HTML is a lossy intermediate. Useful as a
side-channel emitter (DDE could grow an HTML output via mammoth)
but not as a parser replacement.

[docx2python](https://github.com/ShayHill/docx2python) returns a
`DocxContent` object with body / header / footer / footnote /
endnote sections separated, and surfaces images as a flat list. Its
[Snyk advisor page](https://snyk.io/advisor/python/docx2python)
flags it as "Inactive" — the last release was several years stale.
On feature parity with python-docx for table-heavy specs, it's a
sideways move; for paragraph-heavy memos with footnotes it's a step
up. For the DDE workload (2-column tables with nested content), no
benefit.

Pandoc via [pypandoc](https://pypi.org/project/pypandoc/) is the
industrial-strength path. The 2026 pypandoc release [bundles the
pandoc binary](https://onebadbit.com/posts/2025/10/pypandoc-is-incredible/),
so the install footprint is one pip command. Two well-known
limitations apply: pandoc's [intermediate representation is less
expressive](https://pandoc.org/MANUAL.html) than several of its
input formats — complex tables in particular don't survive — and
[pandoc relies on style names](https://github.com/jgm/pandoc/issues/1843)
to recover document structure, so a `.docx` whose author leaned on
"Normal" everywhere comes out flat. Defense specs typically *do*
follow style discipline (Heading 1 / 2 / 3 used semantically), so
pandoc would work — but the table fidelity loss is fatal for DDE's
two-column-table-driven extraction.

[unstructured.io](https://unstructured.io/) is the
"throw-anything-at-me" parser favoured by RAG pipelines. A
[2025 PDF parser comparison](https://onlyoneaman.medium.com/i-tested-7-python-pdf-extractors-so-you-dont-have-to-2025-edition-c88013922257)
found it produced clean semantic chunks but at 1.29s per document
versus pdfplumber's 0.10s. More concerning for DDE's positioning,
[recent reviews flag accuracy regressions](https://parsli.co/blog/best-pdf-parser-tools)
and complex-layout struggles. It's also a heavy dependency tree —
inappropriate for a stdlib-first PyInstaller bundle.

[PyMuPDF](https://pymupdf.readthedocs.io/en/latest/about.html) is
the speed-and-fidelity champion for PDFs in
[direct comparisons](https://arxiv.org/html/2410.09871v1) — fastest
text extraction, most consistent table recall among rule-based
tools. The catch is licensing: PyMuPDF is AGPL-licensed, which
forces the surrounding tool into AGPL or a commercial PyMuPDF
license. For an internal defense-contractor tool that may flow to
restricted networks, this is a procurement-friction headache that
pdfplumber (MIT) avoids cleanly. Worth knowing about; not worth
adopting until the licensing story is sorted at the user's org.

**Real-world fit.** python-docx + pdfplumber is the well-trodden
path for regulated-document Python work — both are MIT-licensed,
both are zero-CVE in recent history, both bundle through PyInstaller
without ceremony.

**Recommendation: keep python-docx and pdfplumber.** Watch
PyMuPDF's licensing — Artifex periodically reconsiders the dual-
license model, and a permissive flip would make it the obvious
upgrade for the PDF path. Mammoth could be added as a side-channel
emitter (HTML output of DDE results) without disturbing the parser.

---

## 3. Process model formats and Nimbus alternatives

**Current choice.** TIBCO Nimbus, with a five-emitter `nimbus-
skeleton` pipeline (PlantUML / YAML / UML 2.5 XMI / Visio `.vsdx` /
review xlsx) targeting Nimbus's import-from-Visio path documented
in the Nimbus 10.6.1 User Guide.

**Critical finding.** TIBCO announced on July 1, 2024 that TIBCO
Nimbus would no longer be available for renewal or new subscriptions
starting September 2, 2024, and that the on-premise product suite
[officially retired on September 1, 2025](https://www.netcall.com/blog/alternative-to-tibco-nimbus/).
TIBCO Platform — TIBCO's modernisation umbrella — does not include
a Nimbus equivalent. This means that as of the date of this survey,
Nimbus is in vendor-end-of-life mode. Existing installations
continue to function, but the toolchain is no longer receiving
patches and any new project that would have selected Nimbus is now
obligated to choose differently.

**Alternatives.**

ARIS (Software AG, now ARIS GmbH) is the market default for BPM in
regulated industries and has a [direct Nimbus migration story](https://aris.com/nimbus-alternatives/).
Strong process repository, governance workflows, BPMN 2.0 + EPC +
ArchiMate support. Expensive, on-premise still available, defense
deployments common.

Liberty Spark (Netcall, [the explicit Nimbus successor](https://www.netcall.com/tibco-nimbus-alternative-designed-to-revolutionise-process-mapping/))
is built by ex-Nimbus engineers and imports existing Nimbus
process repositories. UPN-based (Universal Process Notation, Nimbus's
core notation), so existing models survive the migration semantically.

[Interfacing](https://interfacing.com/replace-nimbus?nocache=1) makes
a play specifically for the regulated-industry Nimbus exit — their
platform is 21 CFR Part 11 validated and pitched at aerospace,
life sciences, finance, and government.

Open-standards alternatives — BPMN 2.0 ([OMG standard](https://www.signavio.com/wiki/process-design/bpmn/)),
EPC, DMN, ArchiMate, IDEF0 — are notation choices independent of
tool. BPMN 2.0 is the de-facto standard in commercial work; EPC
remains common in ARIS shops; IDEF0 still appears in DoD contract
deliverables but is no longer where new work is being done.

**Real-world fit in defense.** The DoD has been moving to MBSE for
mission-architecture work — [UAF (Unified Architecture Framework)](https://www.omg.org/uaf/)
is the OMG standard layered on top of SysML / UML for DoDAF / NAF /
MODAF conformance, and the [DoD's January 2025 Mission
Architecture Style Guide](https://ac.cto.mil/wp-content/uploads/2025/01/U-Mission-Architecture-Style-Guide-Final_07Jan2025.pdf)
codifies the practice. The new Cameo 2026x release ships with
[UAF 1.3 plugin in production](https://3dswym.3dexperience.3ds.com/en/post/catia-mbse-cyber-systems/the-latest-2026x-release-of-catia-magic-cameo-products_MsRWrimbTrKUN4mQtIr-vQ).
Programs like [Missile Track Custody at the U.S. Space Force](https://dair.nps.edu/bitstream/123456789/5362/1/SYM-AM-25-346.pdf)
are explicitly building on UAF. So the future-state of "model-
driven defense process" is increasingly Cameo / SysML / UAF, not
Nimbus / UPN.

**Recommendation: keep the existing Nimbus emitter for active
projects, but treat the BPMN 2.0 emitter as the highest-priority
phase-3 addition.** A BPMN 2.0 XML emitter from `nimbus-skeleton`'s
in-memory `Skeleton` is genuinely a 200-line task — the YAML
manifest already exposes activities, gateways, flows, and actor
swimlanes. With BPMN 2.0 XML, the same skeleton imports cleanly
into Camunda Modeler, Bizagi, Signavio, ARIS, and Liberty Spark, and
sets up a viable post-Nimbus future without abandoning Nimbus
support today. The `bpmn-to-visio` pure-Python converter
([Mgabr90/bpmn-to-visio](https://github.com/Mgabr90/bpmn-to-visio))
demonstrates a working pure-stdlib implementation pattern that the
existing `vsdx.py` emitter can mirror.

---

## 4. Compliance traceability standards

**Current choice.** Custom in-house compliance-matrix tool with five
matchers (explicit_id regex / manual_mapping / TF-IDF similarity /
fuzzy_id Levenshtein / keyword_overlap Jaccard) producing a 3-sheet
xlsx (Matrix / Detail / Gaps).

**Alternatives.**

IBM DOORS (classic) and DOORS Next Generation (DNG) are the
incumbent in DoD defense work — [DoD programs
historically mandate DOORS / DNG](https://www.jamasoftware.com/solutions/airborne-systems/),
and the toolchain integrations (Cameo Data Hub for SysML sync,
Polarion for ALM, ELM Python Client for scripting) all assume DOORS
is in the picture. DOORS itself is increasingly criticised — Jama's
[market positioning](https://www.jamasoftware.com/solutions/better-than-ibm-doors/)
calls out DOORS' age, scriptability gaps, and integration friction.

Polarion (Siemens, formerly Polarion Software) is the heavyweight
[ALM platform with built-in requirements management](https://polarion.plm.automation.siemens.com/products/polarion-requirements).
SysML / SysML v2 friendly, integrates with Cameo via the same
Polarion-Cameo connector ecosystem.

Jama Connect is the modern challenger and the strongest at "live
traceability" — it's the [DoD-contractor preferred answer in 2024–
2026 reviews](https://www.jamasoftware.com/solutions/airborne-systems/),
particularly for DevSecOps integration with CI/CD pipelines.

CodeBeamer (Intland Software, now PTC) and Visure are the second-
tier specialists. Visure in particular has the [most explicit
multi-standard compliance template support](https://visuresolutions.com/),
covering ISO 26262 / IEC 62304 / IEC 61508 / CENELEC 50128 /
DO-178B/C / FMEA / SPICE / CMMI in a single product surface.

**Real-world standards expectations.** Traceability matrix
expectations vary by standard: DO-178C (commercial avionics
software) requires bidirectional traceability between high-level
requirements, low-level requirements, source code, and test cases;
ISO 26262 (automotive functional safety) requires the same plus
hazard / safety-goal links; CMMI process areas describe traceability
as a generic engineering practice; NIST 800-53 requires mapping
between security controls and implementing artefacts.
[Parasoft's coverage](https://www.parasoft.com/learning-center/iso-26262/requirements-traceability/),
[Modern Requirements'](https://www.modernrequirements.com/standards/managing-iso-26262-compliance-with-modern-requirements/)
and [Stell Engineering's](https://stell-engineering.com/blog/what-is-requirement-traceability)
overviews converge: the tooling is less important than the
discipline, but auditors expect machine-generated coverage
artefacts. The compliance-matrix tool's 3-sheet xlsx (Matrix /
Detail / Gaps) is exactly the artefact shape auditors look for.

**Recommendation: keep compliance-matrix as a lightweight DOORS-
adjacent tool.** The tool isn't competing with DOORS / Polarion /
Jama; it's serving the case where the contract-side requirements
are in a Word spec and the procedure-side requirements are in another
Word spec, and a heavyweight RM platform isn't on the bill of
materials. That use case stays valid even as the heavyweights
dominate the enterprise tier. The matchers in particular are well-
calibrated for this niche — the fuzzy-id matcher addresses exactly
the "DO-178C Section 6.3.1 vs bare 6.3.1" failure mode that bites
RM-lite workflows.

---

## 5. ReqIF tooling

**Current choice.** Custom `reqif_writer.py` emitting ReqIF 1.2 in
`basic` / `cameo` / `doors` dialect variants. Stretch item per
REVIEW: actual Cameo and DOORS import validation against real
installs.

**Alternatives.**

[strictdoc-project/reqif](https://github.com/strictdoc-project/reqif)
is the actively maintained Python ReqIF library in 2026. Released
on a regular cadence, supports parsing and unparsing, used as the
foundation of the [strictdoc](https://github.com/strictdoc-project/strictdoc)
project's import / export plumbing. PyPI: [reqif](https://pypi.org/project/reqif/).
Well worth adopting as the parsing-side companion to DDE's writer
once round-tripping becomes a real workflow.

[pyreqif](https://github.com/ebroecker/pyreqif) is the older
alternative. PyPI release [0.7](https://pypi.org/project/pyreqif/)
dates to 2021; the project has been quiet since. Functional but
stale. The strictdoc-project replacement effectively absorbed the
audience.

[ReqView](https://www.reqview.com/) is the leading commercial
ReqIF-native authoring tool — useful for Eric to know about as a
reviewer-facing endpoint (a defense reviewer with ReqView can
consume ReqIF files directly without DOORS / Polarion / Jama).

[Requisis ReqIF-Manager for DOORS Next](https://requisis.com/en/produkte/dng-reqif-manager.html)
is the third-party gap-fill for DNG's native ReqIF support, which
is famously [imperfect on round-trip](https://www.reqif.academy/forums/topic/reqif-roundtrip-to-doors-ng-problem-with-images/)
— in particular, image preservation breaks when modifying a DNG
export and re-importing.

[Cameo Requirements Modeler Plugin](https://www.3ds.com/products/catia/no-magic/cameo-requirements-modeler-plugin)
imports ReqIF natively and is the consumer DDE's `cameo` dialect
targets.

**State of ReqIF tooling in 2026.** ReqIF 1.2 (the current
specification, OMG-standardised) is widely supported but has
implementation gotchas: image-link preservation, custom-attribute
serialisation, hierarchical-spec round-tripping. The
[ELM-Python-Client REQIF_IO example](https://github.com/IBM/ELM-Python-Client/blob/master/elmclient/examples/REQIF_IO.md)
documents IBM's official import / export script, which is the
reference for what DOORS Next will actually accept. DDE's `doors`
dialect should in principle align with that reference.

**Recommendation: keep the in-house writer; add `reqif` (strictdoc-
project) as a development-time dependency for round-trip testing.**
The development-time test path would be: emit DDE → ReqIF, parse
back via `reqif`, assert no information loss on a fixture set. This
nails down the dialect compliance question without forcing a
runtime dependency. The Cameo / DOORS validation stretch item
remains gated on access to a real install, which `reqif` doesn't
substitute for.

---

## 6. Synthetic test data for controlled environments

**Current choice.** Hand-authored `.docx` fixtures in `samples/
edge_cases/` and `samples/procedures/`, characterising failure
modes from work-network observations without containing controlled
content. Per FIELD_NOTES, four `procedural_*.docx` fixtures landed
in 2026-04-24 to reproduce header-signal / blank-actor / multi-
actor / bulleted failure modes.

**Alternatives.**

LLM-generated synthetic procedures — the 2026 way. Drive a model
with a structural template ("write a 12-page system specification
in MIL-STD-498 style with H1 / H2 / H3 headings, two-column
tables, and 'shall' statements at the actor-cell level"), generate
varied corpora at scale. The advantage is volume; the disadvantage
is realism — LLM-generated specs are often *too* uniform and miss
the quirks (inconsistent capitalisation, weird table merges, residual
formatting from prior templates) that real specs actually break on.

Public-domain government documents — the underused option. The
[FAR / DFARS](https://www.acquisition.gov/), [NIST 800-series](https://csrc.nist.gov/publications/sp800),
[MIL-STD-498](https://en.wikipedia.org/wiki/MIL-STD-498),
[DO-178C](https://my.rtca.org/), and CMMI institute documents are
all publicly available and contain exactly the structural patterns
DDE is built to handle ("shall", "should", "may" language; section
hierarchies; tabular requirement layouts). They make excellent
positive-case fixtures with no controlled-content concerns. A
representative trio — one MIL-STD, one NIST 800-53, one
DO-178C-derived spec — covers most of the structural diversity an
internal defense corpus exhibits.

Structural-template approaches — what the existing `samples/
edge_cases` fixtures embody. Hand-author a `.docx` whose *shape*
matches a real failure mode (nested tables / merged cells / mixed
heading styles) without containing any real content. Per
FIELD_NOTES this is the working approach.

[Synthesized](https://www.synthesized.io/) and
[Tonic.ai](https://www.tonic.ai/) are the commercial synthetic-data
players, but both are tabular / database-oriented. Not directly
applicable to text specs.

**Real-world fit.** The defense / aerospace literature on synthetic
data ([the CPS4EU paper on AI-airborne systems](https://cps4eu.eu/wp-content/uploads/2022/11/From-Operational-Scenarios-to-Synthetic-Data-Simulation-Based-Data-Generation-for-AI-Based-Airborne-Systems.pdf),
[Meegle's defense data overview](https://www.meegle.com/en_us/topics/synthetic-data-generation/synthetic-data-for-defense-applications))
is overwhelmingly about training data for AI / ML models, not about
test corpora for document-parsing tools. The closest match is
[redaction-and-declassification automation](https://blog.dreamfactory.com/government-and-defense-air-gapped-llm-data-access-dreamfactory) —
take a real spec, replace the controlled fragments with synthetic
analogues, keep the structure. That path is technically sound but
operationally heavy: redaction has its own approval cycle.

**Recommendation: keep the current approach (hand-authored
structural fixtures), and add a small public-domain government-doc
positive-case set.** Three fixtures from the FAR / NIST / MIL-STD
universe would materially expand DDE's regression coverage at zero
content-control cost. LLM-generated fixtures are watch-only — the
realism gap is what makes them risky for a tool whose failures are
mostly about handling unusual structure rather than unusual prose.

---

## 7. Smoke tests for offline / air-gapped deployments

**Current approach.** Monkey-patched outbound-network assertions in
the test path (the technique tonight's main task is using). PyInstaller-
built exe with all deps frozen at build time. NLP_BUNDLE_SMOKE_TEST.md
runbook covers the manual verification step.

**Alternatives.**

Docker `--network=none` smoke testing — run the bundle inside a
container with no network interface and assert that everything
needed is local. This is the [defense-unicorns / Anchore pattern](https://anchore.com/blog/dod-devsecops-air-gap-environment/)
and works regardless of language. The catch on Windows: the
PyInstaller artefact is a `.exe`, and exercising it inside a
container means a Windows container (heavier) or a Wine-based
runner (fragile). For Linux portions of the toolchain it's a clean
pattern; for the Windows-targeted DDE bundle, the manual smoke test
on a network-isolated VM is more honest.

`tox` matrix with offline-mode runners — `tox` calls `pip` against
a pre-staged wheelhouse rather than PyPI, asserting that the
dependency tree closes against local artefacts. The
[Coder air-gapped install docs](https://coder.com/docs/install/airgap)
and [InfraGap's writeup](https://infragap.com/air-gapped/) describe
the same pattern. Best paired with a `pip download -d wheelhouse/`
step in CI.

Monkey-patched outbound assertions — the in-test technique. Patch
`socket.create_connection` to raise on any unexpected hostname,
exercise the full happy path, assert no raise. Cheap, fast,
verifiable in normal unit tests. No environmental setup. Eric's
current approach.

`pip-audit` and SBOM generation — adjacent rather than alternative.
Both go in the runbook for restricted-network software-approval
processes ("show us the bill-of-materials for what you're
deploying").

**Recommendation: keep monkey-patched assertions for fast-feedback
unit tests, and keep the manual NLP_BUNDLE_SMOKE_TEST runbook for
release gates.** The two layers complement each other and both are
already documented. Worth adding: a `pip download` recipe to the
release checklist that produces a frozen wheelhouse the build is
reproducible against — that closes the "rebuild on a fresh CI
machine and get a byte-different exe" hazard.

---

## 8. PyInstaller alternatives for sealed-bundle distribution

**Current choice.** PyInstaller pinned to `>=6.0,<7`,
single-file `.exe` (`upx=False` to avoid AV false-positives), build
batch script, optional NLP-stack pin block.

**Alternatives.**

[Nuitka](https://nuitka.net/) is the most credible alternative.
Compiles Python to C and then to a native binary; the result starts
faster (no PyInstaller-style temp-dir extraction), is smaller for
pure-Python workloads, and is much harder for AV / SmartScreen to
flag because it looks like a real native executable. The catch is
binary-extension support: per [PyOxidizer's comparisons doc](https://pyoxidizer.readthedocs.io/en/stable/pyoxidizer_comparisons.html),
PyInstaller still leads on "knows how to find runtime dependencies"
for packages like PyQt and spaCy. For DDE specifically — which
bundles a pile of spaCy-internal hidden imports — a Nuitka switch
would be a multi-week project rather than a 30-minute swap.
Compliance-matrix and nimbus-skeleton, by contrast, have minimal
binary deps (openpyxl + pyyaml) and are ideal Nuitka candidates.

[PyOxidizer](https://pyoxidizer.readthedocs.io/) was the
mid-2020s dark horse. Embeds a Rust-built native loader and an
in-memory Python interpreter. The project has been [effectively
quiet since 2022](https://github.com/indygreg/PyOxidizer); the
last meaningful release is `0.24.0`. Not a candidate.

[Briefcase (BeeWare)](https://briefcase.readthedocs.io/) is alive,
actively releasing, targets installer formats (.msi / .exe / .pkg /
.deb / .rpm) rather than single-file bundles. For Windows defense
networks the .msi installer story is *better* than the
double-clickable .exe — corporate IT can deploy via SCCM /
Intune more cleanly. Worth considering as a secondary distribution
channel for sites that prefer installers; doesn't replace the
PyInstaller portable-exe path that targets the "drop on a network
share, run without admin" scenario.

[shiv](https://shiv.readthedocs.io/) and [PEX](https://pex.readthedocs.io/)
build single-file ZIPapps. They require Python on the target
machine, so they don't solve DDE's "no Python install" constraint.
Useful elsewhere in the toolchain (CI tooling, internal scripts);
not for DDE.

[conda-pack](https://conda.github.io/conda-pack/) packages a
conda environment as a relocatable archive. Heavy. Useful for
data-science distributions; overkill for a small-footprint tool.

[py2exe](https://www.py2exe.org/) is the original Windows-only
freezer. Maintained at low velocity, no advantage over PyInstaller
in 2026.

**Recommendation: keep PyInstaller for DDE; consider Nuitka for
compliance-matrix and nimbus-skeleton.** Those two have small
binary-extension surface (openpyxl is the heaviest), and the AV /
SmartScreen story for Nuitka is materially better — fewer false-
positive quarantines, faster start. Add Briefcase .msi as a
secondary distribution channel watch-item for sites where
installer-based deployment is preferred over portable-exe.

---

## 9. Document classification — actor-vs-action discrimination

**Current approach.** Implicit. Primary actor comes from the 2-column
table's left cell; secondary actors come from the requirement text
via known-actor regex match plus optional spaCy NER pass. The
"is X the subject?" question is answered structurally, not
linguistically.

**Alternatives.**

Dependency-parser-based subject extraction — spaCy's
`token.dep_ == "nsubj"` already tells you which token is the
sentence subject. The DDE design instead leans on table structure
because defense specs use tables to encode actor-responsibility,
which is structurally more reliable than natural-language subject
parsing.

Frame-semantic parsing (FrameNet-derived) — academically
interesting, no production-ready Python toolkit in 2026 with the
ergonomics of spaCy.

LLM-based actor / action splitting with a structured-output schema
(Outlines / Instructor) — works well in connected-machine workflows.
For the DDE in-bundle case, latency is again the issue.

Rule-based with linguistic signals — strengthen the existing path
with more sophisticated patterns. "The system shall …" → system as
actor. "The user shall …" → user as actor. "X shall happen" →
passive voice, actor implicit. Defense specs use these patterns
predictably enough that a 100-line pattern matcher catches the long
tail.

**Recommendation: keep the structural-first approach, and invest in
the rule-based long-tail layer.** Specifically: a passive-voice
detector that flags requirements where the syntactic subject isn't
the table-cell actor, and a "system" / "operator" / "ground
station" canonical-keyword aliasing layer. These compound with the
existing actor list mechanism cleanly.

---

## 10. GUI alternatives for Windows desktop process tools

**Current choice.** Tkinter (stdlib), with optional `tkinterdnd2`
for drag-and-drop. Per memory and FIELD_NOTES, *not* customtkinter.

**Alternatives.**

[customtkinter](https://customtkinter.tomschimansky.com/) is the
"modernise tkinter" play — drop-in replacement widgets with
rounded corners, dark/light themes. Adds ~3 MB to the bundle, no
new GUI architecture. The lowest-friction visual upgrade from the
status quo.

[PySide6](https://www.pythonguis.com/faq/which-python-gui-library/)
is the LGPL-licensed Qt 6 binding from The Qt Company. Qt is the
gold standard for desktop polish on Windows. The LGPL means it's
usable in proprietary defense contractor work; PyQt6 is GPL and
would force GPL on any closed-source tool, so PySide6 is the right
Qt choice for this domain. The cost is bundle size (~50–100 MB
larger than tkinter) and a steeper architectural change.

[Flet](https://flet.dev/) is the Flutter-based Python framework.
Beautiful, modern, web/mobile/desktop unified. Uses an embedded
Flutter engine, which is a heavy dependency for a small tool. Best
for greenfield apps that genuinely need cross-platform polish.

[Toga (BeeWare)](https://toga.readthedocs.io/) targets the same
"native widget on every platform" goal as Flet via different means.
Per [comparison reviews](https://medium.com/@areejkam01/i-compared-pyside6-pyqt-kivy-flet-and-dearpygui-my-honest-2025-review-8c037118a777),
polish on Windows is uneven.

[Tauri + Python backend](https://tauri.app/) and Eel are
HTML/JS-frontend frameworks that drive a Python process behind.
Much heavier than Tkinter. Appropriate for tools that actually need
a web-app UI; overkill for DDE's form-driven workflow.

**Real-world fit.** Defense contractor internal tools tend toward
either WPF / WinForms (the .NET native path) or Qt-based apps. Tk
shows up most often in academic / scientific contexts and as the
"first thing that ships" in Python-internal tooling. None of those
are wrong; they just imply different polish ceilings.

**Recommendation: stay on tkinter; consider customtkinter as a
low-risk visual refresh.** A PySide6 migration is a medium-sized
project and would only pay off if the GUI grew beyond the current
form-shaped UX. The existing Tk implementation is well-tested
(progress callback, cancel, persistent settings, drag-and-drop) and
upgrading the visual shell without disturbing those mechanics is the
better trade. Watch Flet — if Eric ever wants the same UI on a
mobile reviewer's tablet, Flet becomes interesting.

---

## Summary recommendations table

| # | Area                                | Verdict                                       |
|---|-------------------------------------|-----------------------------------------------|
| 1 | NLP for actor extraction            | Keep spaCy; harden rule-based fallback        |
| 2 | Document parsing (.docx / .pdf)     | Keep python-docx + pdfplumber; watch PyMuPDF licensing |
| 3 | Process model formats               | Keep Nimbus emitter; **add BPMN 2.0** (priority) |
| 4 | Compliance traceability             | Keep compliance-matrix; track DOORS / Jama / Polarion as enterprise tier |
| 5 | ReqIF tooling                       | Keep writer; add `strictdoc-project/reqif` for round-trip tests |
| 6 | Synthetic test data                 | Keep hand-authored fixtures; add public-domain gov-doc set |
| 7 | Offline smoke tests                 | Keep monkey-patched + manual runbook; add `pip download` wheelhouse |
| 8 | PyInstaller alternatives            | Keep for DDE; **consider Nuitka** for compliance-matrix and nimbus-skeleton |
| 9 | Actor-vs-action discrimination      | Keep structural-first; invest in passive-voice detector |
| 10| GUI alternatives                    | Keep tkinter; consider customtkinter for visual refresh |

---

## Highest-leverage potential switch

**A BPMN 2.0 XML emitter on `nimbus-skeleton`.** TIBCO Nimbus is in
vendor end-of-life as of September 2025, the BPMN 2.0 ecosystem
(Camunda, Bizagi, Signavio, ARIS, Liberty Spark) all import the
standard losslessly, and the in-memory `Skeleton` already exposes
every primitive BPMN needs (activities, gateways, flows, swimlanes).
This is a single new emitter file, ~200 lines, on the same pivot
the YAML / XMI / Visio emitters already share. The payoff is
strategic continuity: when the user's organisation eventually picks
a Nimbus successor, the skeleton tool keeps working unchanged.

The runner-up is **Nuitka for compliance-matrix and nimbus-skeleton**:
both have small dependency surfaces, both would benefit from
Nuitka's better AV-friendliness on Windows defense networks, and
both are too small to justify the spaCy-style hidden-import dance
that would block Nuitka on DDE. Treat as a follow-on after BPMN
emitter.

---

## What got cheaper / better since the stack was chosen

Three deltas worth noting honestly.

**Zero-shot NER got real.** GLiNER changes the cost equation for
domain-specific actor extraction. In 2023 the only paths were
"fine-tune a model on labelled spec data" (multi-week, requires
labelled data) or "ship spaCy and accept the OntoNotes-trained
generic-entity baseline" (current path). GLiNER's zero-shot
property collapses that to "list your actor types in config and go."
Bundle size remains a real constraint and the field-tested PyInstaller
recipe doesn't yet exist, so the recommendation is still "keep
spaCy" — but the technological floor under that decision shifted
notably.

**Pandoc grew up.** The 2026 `pypandoc` ships the pandoc binary
in the wheel, which removes the historic deployment friction (no
more "install pandoc separately"). Pandoc still doesn't preserve
complex tables losslessly so it's not a python-docx replacement
for DDE — but it's now the right tool for emitting *secondary*
formats (HTML reviews, Markdown PR comments) without bringing in
mammoth as a separate dep.

**Nimbus retired.** The biggest single delta is the one Eric may
already be tracking: TIBCO Nimbus's on-premise EOL was September
2025. Existing installs continue to work, but the toolchain no
longer ships patches. This puts a soft deadline on the BPMN 2.0
emitter recommendation in §3 / above. For active Nimbus users in
the next 12–24 months, the tool keeps working; beyond that horizon,
the Nimbus path is technically functional but strategically dead.

---

## Load-bearing call: NLP stack for offline defense networks

This is the question that decides whether DDE works in its target
environment. FIELD_NOTES already documents that NLP availability is
the failure mode that bit the work-network deployment, and the
current resolution path (Path-A: PyInstaller-bundled spaCy +
en_core_web_sm 3.7.1 wheel, pre-baked) is technically sound but
fragile in three specific places.

**The recommendation: keep spaCy as the bundled NLP, but treat
rule-based actor extraction as the load-bearing layer and the NLP
as enrichment.** Concrete reasoning:

First, the *evidence base for spaCy in this role is the strongest
of any candidate.* PyInstaller + spaCy has [community-tested
recipes](https://github.com/josh-cooper/spacy-pyinstaller),
multi-year deployment history in regulated industries, and a
predictable failure mode (missing hidden imports — caught at smoke
test) rather than an unpredictable one. GLiNER and HuggingFace
transformer NER both have working PyPI packages but the
PyInstaller-bundled story is much less battle-tested, and the bundle
size goes from 300–450 MB (current) to 600 MB+ for a transformer
NER. On a restricted network where the AV / SmartScreen exception
process is already a release gate, doubling the artefact size for
a marginal accuracy gain is an unforced loss.

Second, the *NLP failure mode is recoverable only if the rule-based
fallback is actually load-bearing.* Currently the failure mode is
"NLP missing → actor extraction degrades → output not trustworthy."
The right architecture treats the rule-based path as the floor and
NLP as a confidence-boosting upgrade. This means the actor list +
regex matching — which already exists in `actors.py` — needs to
get *better* on real specs, including: (a) richer canonical-name
normalisation than the current `canonicalise_ner_name` (which is
NER-output-targeted), (b) house-style alias detection (the same
actor appearing as "Auth Service" and "AS"), and (c) passive-voice
detection so requirements like "X shall be logged" can still
attribute the action correctly.

Third, the *connected-machine workflow option (REVIEW Path-C, FIELD_NOTES
option c) deserves more credit than it gets.* Pre-processing on a
connected machine, exporting the actors xlsx, importing on the
restricted network is operationally clean if the operational flow
is acceptable. It would also be the right path to integrate
GLiNER as a sidecar — generate richer actor metadata once on the
connected machine, propagate via the actors xlsx, never need
GLiNER in the bundled exe. The architecture already supports this
(actors xlsx is the canonical interchange); the question is purely
operational.

The single concrete next step: spend a week on the rule-based
actor-extraction path quality on real (or synthetic-realistic) specs
*assuming NLP is unavailable*, and pin the output quality with
fixtures. If rule-based-only output is acceptable for the
work-network's review purposes, the bundling-vs-pre-process question
becomes much less urgent and the bundled-spaCy path becomes a
"nice when it works" rather than "load-bearing."

---

End of survey.
