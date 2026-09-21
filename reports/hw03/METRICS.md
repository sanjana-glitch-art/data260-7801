# Homework 3 Retrieval Metrics

## Student Configuration

| Setting | Value |
|---|---|
| Student | Sanjana Thummalapalli |
| SID4 | 7801 |
| PORT_BASE | 8601 |
| PREFIX | s7801 |
| SEED | 7801 |
| VERIFY_SEED | 267801 |
| DOMAIN_ID | 1 |
| Assigned domain | Clinical Trial Listings |

## Experiment Configuration

| Setting | Value |
|---|---|
| Retrieval framework | LlamaIndex |
| Embedding model | sentence-transformers/all-MiniLM-L6-v2 |
| Embedding dimension | 384 |
| Vector store | LlamaIndex SimpleVectorStore |
| Index type | In-memory VectorStoreIndex |
| Retrieval mode | Retrieval only |
| Top-k | 5 |
| Preregistered questions | 5 |
| Additional false-positive question | 1 |
| Total questions evaluated | 6 |
| Chunking techniques | Token, Semantic, Sentence-window |

The five graded questions and their expected answers and source files were recorded in `reports/hw03/questions.yaml` and committed before the original retrieval experiment. An additional sixth question was later added and committed before rerunning the experiment because the first five questions did not produce a source mismatch.

## Chunking Configuration

### Token Chunking

The token pipeline used `TokenTextSplitter` with:

- Chunk size: 512 tokens
- Chunk overlap: 64 tokens

This technique creates chunks of approximately fixed token length and preserves some context between neighboring chunks through overlap.

### Semantic Chunking

The semantic pipeline used `SemanticSplitterNodeParser` with:

- Buffer size: 1
- Breakpoint percentile threshold: 95
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`

This technique embeds neighboring sentences and creates a boundary when their semantic difference exceeds the configured percentile threshold.

### Sentence-Window Chunking

The sentence-window pipeline used `SentenceWindowNodeParser` with:

- Window size: 3
- Central sentence used as the indexed node
- Neighboring sentences stored in the `window` metadata field
- Original sentence stored in `original_sentence`

The experiment used the surrounding sentence window as the returned context when calculating explicit document embeddings, cosine similarity, chunk length, and the preview.

## Retrieval Quality Comparison

The metrics below are averages across all six questions.

| Technique | Chunks | Average chunk length | Mean top-1 cosine | Mean@5 cosine | Recall@5 | Mean retrieval latency |
|---|---:|---:|---:|---:|---:|---:|
| Token | 162 | 2,432.29 characters | 0.6765 | 0.6271 | 100.0% | 27.67 ms |
| Semantic | 90 | 3,824.51 characters | 0.6155 | 0.5833 | 100.0% | 22.00 ms |
| Sentence-window | 1,705 | 1,412.98 characters | 0.6842 | 0.6084 | 100.0% | 86.13 ms |

Recall@5 was calculated by checking whether at least one of the five retrieved chunks came from the expected source file for the question.

## Results by Technique

### Token

Token chunking produced 162 chunks, with an average returned length of 2,432.29 characters. Its mean top-1 cosine similarity was 0.6765, and its mean similarity across the five retrieved chunks was 0.6271.

Token chunking had the highest Mean@5 cosine similarity of the three techniques. Its 27.67 ms mean retrieval latency was also substantially lower than sentence-window retrieval. The fixed chunk size allowed each retrieved result to contain enough context without creating an excessive number of index nodes.

### Semantic

Semantic chunking produced the fewest chunks: 90. It also produced the largest average chunks, at 3,824.51 characters. Its mean top-1 cosine was 0.6155, and its Mean@5 cosine was 0.5833.

Semantic retrieval had the lowest latency at 22.00 ms because its index contained the fewest nodes. However, it also had the lowest similarity measurements. The large semantic chunks sometimes included multiple related ideas, which made each chunk less focused on the precise wording of a question.

### Sentence-Window

Sentence-window chunking produced 1,705 nodes, far more than either of the other techniques. Its mean top-1 cosine of 0.6842 was the highest result, while its Mean@5 cosine was 0.6084.

The sentence-window method was effective at locating a highly relevant first result because each indexed node represented a focused sentence. The surrounding sentences supplied useful context after retrieval. However, the large number of nodes increased mean retrieval latency to 86.13 ms, the slowest of the three techniques.

## False-Positive Retrieval

The additional question `q6` asked:

> What should a clinical-trial sponsor do to protect participants and ensure that study results are reliable?

The expected answer described a risk-based monitoring approach focused on critical data and processes. The expected source was `fda_risk_based_monitoring.txt`.

Token retrieval returned the following result at rank 5:

| Field | Result |
|---|---|
| Technique | Token |
| Question | q6 |
| Rank | 5 |
| Cosine similarity | 0.5353 |
| Expected source | `fda_risk_based_monitoring.txt` |
| Retrieved source | `fda_informed_consent.txt` |
| Source match | False |

The returned preview began:

> information is available. For clinical investigations involving the comparison of an investigational product to one or more standards of care, it may be acceptable...

This result did not contain the expected answer about designing and using a risk-based monitoring strategy. It discussed clinical investigations and standards of care instead.

The embedding model probably considered it relevant because the question and chunk share related clinical-research concepts, including clinical trials, sponsors, participant protection, investigations, and standards of care. Embedding similarity measures overall semantic relatedness, not whether a passage contains the specific required answer. Therefore, a passage can receive a moderately confident score while still failing to answer the question.

Other source mismatches for `q6` were also observed:

| Technique | Rank | Cosine | Retrieved source |
|---|---:|---:|---|
| Semantic | 3 | 0.5236 | `fda_informed_consent.txt` |
| Semantic | 4 | 0.5151 | `fda_informed_consent.txt` |
| Semantic | 5 | 0.5121 | `fda_informed_consent.txt` |
| Sentence-window | 4 | 0.4698 | `fda_informed_consent.txt` |

These results demonstrate why a strong similarity score alone should not be treated as proof that a retrieved passage contains the answer.

## Observations

Sentence-window chunking achieved the highest mean top-1 cosine similarity. Its sentence-level indexing allowed the retriever to locate a precise sentence closely related to each query, while the attached window provided neighboring context. However, it generated more than ten times as many nodes as token chunking and had a mean retrieval latency more than three times as high.

Token chunking produced the highest Mean@5 cosine while maintaining moderate latency and a much smaller index. Semantic chunking was the fastest because it produced only 90 nodes, but its large chunks had the lowest top-1 and Mean@5 cosine measurements. All three techniques achieved 100% source-based Recall@5, so the main differences were similarity, granularity, index size, and latency.

## Conclusion

Token chunking provided the best overall balance for this clinical-trial corpus. Sentence-window chunking produced the strongest average first result, but token chunking produced the highest Mean@5 similarity with much lower latency and far fewer nodes. For this corpus, token chunks provided sufficient context without the high indexing and retrieval cost of sentence-window nodes.

## Raw Result Files

The complete machine-readable experiment output is stored in:

- `reports/hw03/raw/retrieval_results.jsonl`
- `reports/hw03/raw/retrieval_results.csv`
- `reports/hw03/raw/retrieval_metrics.json`

Each retrieved result records:

- Question ID
- Technique
- Rank
- Query
- Expected answer
- Expected source file
- Retrieved source file
- Source-match result
- Vector-store score
- Explicit cosine similarity
- Chunk length
- Text preview
- Node ID
- Retrieval latency

The console output containing embedding dimensions, first eight embedding values, vector shapes, retrieval tables, and timestamps is stored in `reports/hw03/RUN_LOG.txt`.