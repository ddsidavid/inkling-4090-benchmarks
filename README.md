# Inkling 2 Mini Unbound v2 on one RTX 4090

I wanted to know how fast one 24 GB card could finish a new file, and how much time I could save when most of an edited file already existed. The engine uses the publisher’s full Unbound v2 checkpoint and its seven-proposal DSpark drafter. The target verifies each proposal. A client supplies source spans for eligible edits and falls back to DSpark on fresh code, broad rewrites and ambiguous selections. [Model revision](https://huggingface.co/nokeepai/Inkling-2-Mini-Unbound/tree/6b7f194d5f020d0508e9dccb4ade56f71dd94a1d) · [Upstream vLLM revision](https://github.com/vllm-project/vllm/commit/ab18334a4f60da74db7de89fe95594e5ed0cda36)

## Eight-block qualification

| Automatic route | Requests | Decode tok/s | Median seconds through file readback |
|---|---:|---:|---:|
| Fresh files | 48 | 402.84 | 0.601 |
| Full-file copy edits | 48 | 3,314.26 | 0.705 |
| Selected repository edits | 16 | 1,627.17 | 1.030 |
| Broad rewrites and a two-file patch | 24 | 453.82 | 2.074 |
| Short rewrite | 8 | 427.16 | 0.356 |

Across ordinary and routed generation all 288 core requests passed. The optimized worker matched 244,688 output token IDs and all core file trees against its earlier control. The previous worker finished the 16 selected edits 0.056 seconds sooner in total. Public Python benchmark rates on this configuration were 350.64 tok/s on HumanEval+ (147/164 passed first try) and 316.67 tok/s on MBPP+ (275/378).

## Five changes and what each bought

| Change | Matched workload | Decode tok/s, before → after | Median time through file readback |
|---|---|---:|---:|
| Use verified source spans on eligible edits | 48 full-file copy edits, ordinary DSpark vs automatic routing on the same optimized worker | 474.19 → 3,314.26 | 3.412 → 0.705 s |
| Replay a CUDA graph for one anchor plus 191 source proposals | 12 copy-heavy edits, graph off vs on | 2,888.46 → 3,320.71 | 0.775 → 0.711 s |
| Score the source vocabulary, apply the softcap and pick the token in one operation | Same 12 edits, graph alone vs graph plus fusion | 3,320.71 → 3,382.53 | 0.711 → 0.703 s |
| Limit compact DSpark scoring to 8,704 candidate rows while the target keeps the full vocabulary | 24 fresh-file requests | 379.23 → 403.34 | 0.634 → 0.604 s |
| Retile the expert projections and pack the 64 routed assignments for eight verified positions | 9 repository creations | 359.17 → 363.38 | 0.596 → 0.588 s |

The first comparison measures the whole source path, including the graph and fusion described in the next two rows. Each other row uses the matching blocks from its own experiment. Adding the gains would count some work twice. A direct literal substitution can bypass generation altogether. This benchmark counts only model-backed requests.

## How I measured it

One active sequence, 4,096-token context, up to 512 tokens per prompt chunk, greedy drafting, cross-request prefix reuse disabled, profiling off. The model stayed loaded. The timed sample excludes warmup and model startup. The engine is a custom Ada build based on vLLM 0.34.0rc1.dev1125. The eight-block test repeats 15 distinct prompts. Each block runs six creations, six copy edits (three prompts twice), two selected edits, one short rewrite and three other rewrites/patches per arm. The ordinary and routed arms see the same frozen inputs. The frozen SQL check uses three queries twice. A separate evaluation on all 500 BIRD Mini-Dev SQLite questions previously achieved 15.8% execution accuracy on the first attempt.

Decode tok/s is the sum of output tokens after the first token in each response divided by the sum of their decode seconds. File time includes the request, writing the result and reading it back. Independent grading checks the resulting files. The core file timings exclude independent grading time. Single-request medians, pooled token rates and total time answer different questions.

Run `python3 score.py` to recompute rates from [per-request measurements](requests.csv). The script pairs rows by block, task and repetition and checks the recorded token and file digests. The [SQL outcomes](sqlite.csv) include retries. The data package supports independent rescoring of the measurements. The [six frozen fresh prompts](fresh-prompts.json) include the rendered text, input token IDs and output caps. They cover five Python files and one SQLite file. The standalone programs also request Python even though their internal IDs start with `swift_`. Running the full routed suite requires the custom worker and its edit fixtures.
