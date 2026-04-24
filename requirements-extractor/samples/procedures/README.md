# Procedure fixtures

FIELD_NOTES §4. Hand-authored synthetic procedure documents exercising
the actor-ID failure modes Eric saw on the work network. None of them
contain real controlled content — they're structural analogues built
from generic industry conventions (ops, release-management, backup,
change-management language).

Each document is a standalone `.docx`. The first five are 2-column
actor/content tables in the format the extractor expects by default.
The last four (the `procedural_*` files) are 3-column tables whose
header row is literally:

| &nbsp; | Step | Required Action |
|---|---|---|

— blank column-1 header, `Step` in column 2, `Required Action` in
column 3. That specific header shape is the *type signal*: any table
matching it should treat every non-empty content row as a requirement,
regardless of whether the text contains shall/must/should/may. A
different header like `Actor | Step | Required Action` keeps the
normal keyword-driven detection path. All four `procedural_*`
fixtures share this header — they differ in what they stuff into the
body rows.

The 3-column files ship with paired `.reqx.yaml` configs so the
parser knows which columns are the actor and the content (actor in
col 1, content in col 3, step number in col 2 ignored). Pair any of
them with a `--nlp` or `--actors seed.xlsx` run to see the NLP-
present / NLP-absent accuracy gap the field notes flagged.

| File | What it exercises | Paired config |
|------|-------------------|---------------|
| `simple_two_actors.docx` | Baseline: two named actors (Operator, Supervisor), clean active-voice prose, one requirement per row. Regression pin. | none (defaults) |
| `ambiguous_roles.docx` | Nested procedure; same actor appears as "Ops Engineer" / "Operations Engineer" / "the engineer", and "Platform Lead" vs "Platform-Lead". Tests the resolver's normalisation + alias grouping. | none (defaults) |
| `implicit_system_actor.docx` | Most steps attributed to "the system" or left blank in column 1. Tests whether the tool surfaces a reasonable actor when none is named. | none (defaults) |
| `passive_voice.docx` | Heavy passive-voice prose ("shall be performed by X"). Primary-column holds a coordinator role; the real per-step actor is buried in a trailing `by`-phrase that only NLP / dependency-parse can reach. | none (defaults) |
| `parallel_flows.docx` | Two actors (QA Lead, Release Manager) interleave across eight rows. Tests row-ordering and actor continuity across a longer table. | none (defaults) |
| `procedural_actor_continuation.docx` | `\|  \| Step \| Required Action \|` table with blank-actor continuation rows in the body. Blank column-1 body cells should inherit the actor from the nearest non-blank row above. Eric 2026-04-23. | `procedural_actor_continuation.reqx.yaml` |
| `procedural_multi_actor_cell.docx` | Same header; column 1 body cells list multiple candidates (`Auth Service, Gateway, Logger`). The sentence subject in column 3 picks which of the candidates actually performs the step; rows without an explicit subject keep the full candidate set. Eric 2026-04-23. | `procedural_multi_actor_cell.reqx.yaml` |
| `procedural_bullet_rows.docx` | Same header; body mixes single-sentence rows with rows whose content cell is a bulleted or numbered list. Each bullet must be emitted as its own requirement — flattening the list loses traceability. Eric 2026-04-23. | `procedural_bullet_rows.reqx.yaml` |
| `procedural_no_keywords.docx` | Same header; body sentences use indicative voice (no shall/must/should/may). The header itself is the only signal that every row is a requirement — today's keyword-based detector captures none of them. Regression target for header-aware parsing. The rule **must** be gated on the exact `\|  \| Step \| Required Action \|` header so other 3-column tables keep normal keyword-driven detection. Eric 2026-04-23. | `procedural_no_keywords.reqx.yaml` |
| `mixed_language.docx` | 2-column procedure where English rows alternate with Spanish translations of the same step. Tests the resolver's behaviour when only a subset of the corpus is parseable — English `shall`/`must` rows should be captured, Spanish rows (no cognate modal) should drop out. Useful for any future multilingual-keyword extension. | none (defaults) |
| `long_procedure.docx` | 52-row procedure with four rotating actors (QA Lead / Release Manager / Duty Engineer / Security Officer) and a deterministic verb×subject grid. Used as a throughput fixture and as the corpus for cancel-path stress tests — ask the extractor to parse it with a `cancel_check` that fires on the tenth file_progress callback and verify no partial xlsx lands on disk. | none (defaults) |

## Regenerating

```
python samples/procedures/generate.py
```

Deterministic — every run produces byte-identical output (timestamps
aside) so test assertions stay stable. Same convention as
`samples/edge_cases/`.

## Running the extractor against them

```
# All five, NLP off — shows the baseline without spaCy.
python -m requirements_extractor.cli requirements samples/procedures/ \
    -o /tmp/procedures_no_nlp.xlsx

# Same corpus, NLP on — shows the recall delta if spaCy is available.
python -m requirements_extractor.cli requirements samples/procedures/ \
    --nlp -o /tmp/procedures_nlp.xlsx

# Actors-mode scan — produces a seed list from the corpus.
python -m requirements_extractor.cli actors samples/procedures/ \
    -o /tmp/procedures_actors.xlsx
```

Comparing the two outputs (NLP on/off) against each document is the
fastest way to characterise the gap the work network currently suffers.

## Adding more

Workflow mirrors `samples/edge_cases/`:

1. Add a builder function to `generate.py`.
2. Re-run `python samples/procedures/generate.py`.
3. Once behaviour stabilises, add a test class in `tests/` pinning the
   expected row count / actor list / requirement types.

All eleven fixtures above now live in this folder; the two stretch
suggestions from the earlier README pass (mixed-language, long
procedure) both landed this pass. Next-up ideas for when you find a
new failure mode:

- A **hand-drawn / OCR'd PDF** of a spec, for exercising the
  pdfplumber fallback path in `legacy_formats.py`. Today's PDF
  testing uses programmatic PDFs with perfect text layers — a scan
  would stress the best-effort extraction.
- A **tracked-changes fixture** — two versions of a docx with Word's
  tracked-changes feature unaccepted, so the diff subcommand's
  behaviour on "pre-acceptance" vs "post-acceptance" extractions can
  be pinned.
