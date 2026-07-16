# Phase 1 parser-v2 public development report

## Scope and status

- Track: B, Phase 1.2B-development
- Dataset: `evaluator_sets/parser_v2_v1/development_cases.jsonl`
- Rows: 60 public labeled development fixtures (5 per stratum)
- Dataset SHA-256:
  `bfaeca837ecfe8673df834c5b8a4fc1626f0835c6ae35c0821acf59bd6e4ac27`
- Model, Azure, and network access: no
- Locked labels accessed: no
- Locked evaluation: no
- **Development metrics only; not locked PASS.**

The parser received only `schema_version`, `answer_type`, and `output_text`.
Reference answers were supplied only to the separate post-extraction correctness
comparison.

## Public development metrics

| Metric | Result |
|---|---:|
| Exact typed-decision agreement | 60/60 (100%) |
| Answer-presence macro-F1 (`present`, `ambiguous`, `no_answer`) | 1.000 |
| Ambiguity precision / recall | 1.000 / 1.000 (support 5) |
| No-answer precision / recall | 1.000 / 1.000 (support 15) |
| Boxed/final misses (S01 + S02) | 0/10 |
| Last-number trap errors (S06) | 0/5 |
| Wrong-span errors (expected-present rows) | 0/40 |
| Material correctness errors (correctness XOR) | 0/60 |

| Stratum | Parser v2 | Legacy |
|---|---:|---:|
| S01 | 5/5 | 3/5 |
| S02 | 5/5 | 2/5 |
| S03 | 5/5 | 1/5 |
| S04 | 5/5 | 1/5 |
| S05 | 5/5 | 2/5 |
| S06 | 5/5 | 2/5 |
| S07 | 5/5 | 1/5 |
| S08 | 5/5 | 3/5 |
| S09 | 5/5 | 2/5 |
| S10 | 5/5 | 0/5 |
| S11 | 5/5 | 0/5 |
| S12 | 5/5 | 4/5 |

The frozen reference-blind legacy adapter achieved 21/60 exact typed decisions
(35.0%) and answer-presence macro-F1 0.4012. Parser v2 achieved 60/60 and
1.000, respectively. The clean-strata comparison was 20/20 for v2 versus
10/20 for legacy. This comparison does not alter legacy code or historical
records.

## Parser provenance

- Source:
  `src/jspace_observation/eval_parsing_v2.py`
- Source SHA-256:
  `f538add0bdd6e5a3281d0298b374a99fecea962a91a4cbaa5b4a20795d9a6918`
- `parser_version`:
  `6cfaec62db37562930a4cb7d3a252bcbf80e1eaf748de98213863ff2566a7f86`

The source digest recipe is:

1. Decode the source as UTF-8 and canonicalize CRLF/CR to LF.
2. Replace only the values on the `PARSER_SOURCE_SHA256` and
   `PARSER_VERSION` assignment lines with 64 zeroes.
3. Hash domain `jspace-parser-v2/source/v1\0` followed by those canonical
   bytes.
4. Build a canonical JSON manifest (sorted keys, ASCII, separators `,` and
   `:`) containing the source digest, algorithm ID, public normalizer ID,
   frozen protocol version and bundle digest, and request/result schema
   versions.
5. Hash domain `jspace-parser-v2/version/v1\0` followed by the manifest bytes.

This binds implementation and frozen public contracts without hashing either
embedded digest value into itself. Extraction uses embedded constants and
does not read source files, environment state, or network resources.

## Caveat

These quota-balanced public fixtures were used iteratively and therefore
measure development-set conformance only. No inference about locked-set
performance, natural-output prevalence, or scientific PASS is authorized.
