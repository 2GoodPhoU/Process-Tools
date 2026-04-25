# Integration: requirements-extractor → compliance-matrix

## Data Flow

```
   procedure.docx
        ↓
   [requirements-extractor]
        ↓
   requirements.xlsx
     (DDE schema)
        ↓
   [compliance-matrix]
        ↓
   matrix.xlsx
 (coverage report)
```

## DDE Output Schema

**File:** `requirements.xlsx`

**Sheets:**
- **Requirements** — one row per extracted requirement
  - Columns: ID, Requirement, Type, Primary Actor, Secondary Actors, Polarity, Confidence, Keywords, Context, Source File, Heading Trail, Section / Topic, Block Ref, Row Ref, Notes
  - Row count: number of requirements found in source document
- **Summary** — metadata
  - Total requirements, parsing timestamp

**Column Details:**
- **ID** — unique requirement identifier (e.g., "REQ-001")
- **Requirement** — the requirement text extracted from the source
- **Type** — HARD, SOFT, or POLARITY (negated requirement)
- **Primary Actor** — the main entity responsible for the requirement
- **Secondary Actors** — other entities mentioned in the requirement text
- **Confidence** — keyword match confidence (1.0 = explicit keyword, 0.0 = inferred)
- **Keywords** — which requirement indicators were detected
- **Context** — sentences surrounding the requirement for audit trail
- **Polarity** — True if the requirement is negated (SHALL NOT, MUST NOT, etc.)

## compliance-matrix Input

**File:** requires two xlsx files (contract and procedure/standard, both in DDE schema)

**CLI Usage:**
```bash
compliance-matrix \
  --contract requirements_contract.xlsx \
  --procedure requirements_procedure.xlsx \
  -o coverage_matrix.xlsx
```

**Optional parameters:**
- `--mapping` — YAML or CSV file with manual ID-to-ID mappings
- `--similarity-threshold` — TF-IDF cutoff (default: 0.20)
- `--keyword-threshold` — Token Jaccard cutoff (default: 0.15)

## compliance-matrix Output Schema

**File:** `coverage_matrix.xlsx`

**Sheets:**
- **Matrix** — traceability matrix (contract reqs × procedure clauses)
  - Rows: contract requirements (from first input)
  - Columns: procedure requirements (from second input)
  - Cell values: match score (0.0–1.0, color-coded white→yellow→green)
  - Frozen panes for ID visibility
- **Detail** — evidence for each match
  - Columns: Contract ID, Procedure ID, Explicit ID Match, Manual Mapping, Similarity, Keyword Overlap, Combined Score
  - One row per linked pair
  - Sorted by descending score
- **Gaps** — unmatched requirements
  - Contract gaps: contract reqs with no procedure match (score < 0.5)
  - Procedure gaps: procedure reqs with no contract match

## Integration Testing

See `tests/integration/test_extractor_to_compliance_matrix.py` for three test cases:

1. **test_extractor_output_schema** — DDE produces valid xlsx with expected columns
2. **test_compliance_matrix_intake** — compliance-matrix consumes DDE output and produces matrix
3. **test_integration_data_flow** — end-to-end flow with validation of all output sheets

**Run the tests:**
```bash
cd requirements-extractor
python tests/integration/test_extractor_to_compliance_matrix.py
```

## Real-World Usage

1. Extract contract document:
   ```bash
   cd requirements-extractor
   python -m requirements_extractor.cli --no-summary requirements path/to/contract.docx -o contract.xlsx
   ```

2. Extract procedure/standard:
   ```bash
   python -m requirements_extractor.cli --no-summary requirements path/to/procedure.docx -o procedure.xlsx
   ```

3. Generate coverage matrix:
   ```bash
   cd ../compliance-matrix
   python -m compliance_matrix.cli \
     --contract ../contract.xlsx \
     --procedure ../procedure.xlsx \
     -o coverage_matrix.xlsx
   ```

4. (Optional) Add manual mappings for custom ID references:
   ```bash
   python -m compliance_matrix.cli \
     --contract ../contract.xlsx \
     --procedure ../procedure.xlsx \
     --mapping ../manual_mappings.yaml \
     -o coverage_matrix.xlsx
   ```

## Schema Version

- **DDE output:** v0.3.0 (as of 2026-04-25)
  - Latest columns: added Polarity, Confidence, Context (prior versions had fewer columns)
- **compliance-matrix input:** compatible with v0.3.0+ (requires ID and Requirement columns at minimum)
- **coverage-matrix output:** v0.1.0

For schema evolution, see `process-tools-common/process_tools_common/dde_xlsx.py`.
