# Edge-case samples

Five synthetic .docx files, each targeting a specific parser/config feature.
They double as fixtures for `tests/test_edge_cases.py`.

| File | What it exercises | Paired config |
|------|-------------------|---------------|
| `nested_tables.docx` | Recursive walker descends into 3-level nested tables and emits dotted block refs like `Nested Table 1 R1C2 > Nested Table 1 R1C2 > Paragraph 1`. | none (defaults) |
| `alphanumeric_sections.docx` | Broadened `tables.section_prefix` regex — `SR-1.1`, `REQ-042`, `A.1` all register as section rows. | none (defaults) |
| `boilerplate_heavy.docx` | `skip_sections.titles` suppresses Revision History, Table of Contents, Glossary, References tables. | `boilerplate_heavy.reqx.yaml` |
| `wide_table.docx` | `tables.actor_column` / `content_column` / `min_columns` / `max_columns` re-map a 4-column spec. (The bare nouns `requirement` / `requirements` are intentionally NOT in the default keyword set, so the header row self-filters without any config tweak.) | `wide_table.reqx.yaml` |
| `noise_prose.docx` | `content.skip_if_starts_with` (`Note:` / `Example:` / `Caution:`), `content.skip_pattern` (`\bTBD\b`), `keywords.soft_remove: [will]` (future-tense drop), negation / polarity retention, empty/whitespace cells. | `noise_prose.reqx.yaml` |

## Regenerating

```
python samples/edge_cases/generate.py
```

The generator is deterministic — every run produces byte-identical (or near-identical; timestamps aside) output so the assertions in `tests/test_edge_cases.py` stay stable.

## Trying them from the CLI

```
python -m requirements_extractor.cli samples/edge_cases/ -o /tmp/edges.xlsx
```

Because each per-doc `.reqx.yaml` lives next to its `.docx`, the parser picks the right config automatically for each file.

## Adding more

If you find a new failure mode, the preferred workflow is:

1. Add a new builder function to `generate.py`.
2. Re-run `python samples/edge_cases/generate.py`.
3. Add a `TestXxx` class in `tests/test_edge_cases.py` with the expected behaviour.
4. Run `python -m unittest discover tests`.
