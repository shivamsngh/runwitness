# Local document extraction evidence: RunWitness v0.2

On 6 September 2026, RunWitness executed two local Ollama document-extraction
pipelines against the named eight-document starter profile drawn from DocuBench's
unchanged 72-document corpus. Both evidence bundles passed their declared smoke
policy and later passed artifact-integrity verification.

This is an integration case study, not a model leaderboard. The vision and text
tracks contain different documents and use different input pipelines, so their
aggregate scores are not directly comparable.

## Results

| Track | Documents | DocuBench aggregate | Wall time | Ollama-reported allocation | Adapter peak RSS |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ministral-3 vision | 5 | 60.15% | 399.48 s | 5.63 GB | 81.14 MB |
| Phi 3.5 native text | 3 | 63.90% | 90.77 s | 3.84 GB | 18.64 MB |

The allocation column is the model allocation reported by Ollama after requests;
it is not whole-machine peak memory. Adapter peak RSS covers the RunWitness child
process, not the separately running Ollama service.

### Ministral-3 vision track

Model: `ministral-3:latest`, 8.9B parameters, Q4_K_M. Model digest:
`1922accd5827ebe6829e536369195db25eaf664528dc66206d646ea3bb386b71`.

| Document | Coverage | Score | Time |
| --- | --- | ---: | ---: |
| `vBIz5dut` | Photographed receipt and line-item array | 78.72% | 58.54 s |
| `ZXlksSpk` | PDF summary table and reconciled total | 92.21% | 86.47 s |
| `NNaGgwE5` | Two-page handwritten form | 54.09% | 119.65 s |
| `nESapyAA` | Hebrew right-to-left invoice | 13.64% | 25.88 s |
| `B0nA2c30` | Rotated receipt PNG | 62.12% | 108.51 s |

### Phi 3.5 text track

Model: `phi3.5:latest`, 3.8B parameters, Q4_0. Model digest:
`61819fb370a3c1a9be6694869331e5f85f867a079e9271d66cb223acb81d04ba`.

| Document | Coverage | Score | Time |
| --- | --- | ---: | ---: |
| `PYhFptk3` | Native-text EDI purchase order | 68.52% | 32.05 s |
| `C7fe2lau` | XML invoice | 23.19% | 29.59 s |
| `eKzY7gEA` | HTML clinical lists | 100.00% | 28.87 s |

## What the evidence establishes

- The exact Ollama model tags, immutable digests, quantization and capabilities
  used by each track were recorded.
- DocuBench's scorer produced the per-document and aggregate quality values.
- RunWitness preserved and hashed every declared native result and summary.
- `runwitness verify` recalculated those hashes successfully for both bundles.
- Both adapters exited successfully and produced the declared document counts.

The run did not enforce network isolation because it intentionally communicated
with the local Ollama service. It does not establish a physical air gap, observe
whole-machine memory, or generalize quality beyond the named starter documents.

## Reproduce

The case-study manifests are
[`case-study-ministral3.json`](../examples/docubench/case-study-ministral3.json)
and [`case-study-phi35.json`](../examples/docubench/case-study-phi35.json).
They were run with Ollama 0.33.3, RunWitness commit
`7f82cb2cf74efc2e0f504ea51fd981d8ac815159`, and DocuBench commit
`43a3f3bc00e591e711075678ca6d154acfedcf42`.

```bash
export RUNWITNESS_HOME=/path/to/RunWitness
export DOCUBENCH_HOME=/path/to/DocuBench

runwitness run examples/docubench/case-study-ministral3.json \
  --output runs/ministral3-v020
runwitness run examples/docubench/case-study-phi35.json \
  --output runs/phi35-v020

runwitness verify runs/ministral3-v020
runwitness verify runs/phi35-v020
runwitness compare runs/ministral3-v020 runs/phi35-v020
```

Use new output directories for every run. The source documents, schemas, labels
and scorer remain in the external DocuBench checkout and are not vendored by
RunWitness.
