# Local RAG Retrieval Evaluation

The evaluation runner sends repository-specific queries to a running Local RAG API and compares returned paths with the expected paths in `cases.json`.

Run it from the repository root:

```sh
docker compose -f compose/ai/local-rag.yml run --rm api \
  python evaluation/run.py \
  --api-url http://api:8080 \
  --top-k 5
```

The report includes:

- top-1 accuracy
- top-k recall
- mean reciprocal rank
- returned paths for every case

Optional thresholds make the command fail when retrieval quality regresses:

```sh
docker compose -f compose/ai/local-rag.yml run --rm api \
  python evaluation/run.py \
  --api-url http://api:8080 \
  --top-k 5 \
  --min-top-1 0.80 \
  --min-recall 1.00 \
  --min-mrr 0.90
```

Keep cases deterministic and grounded in files committed to this repository. Add a case when a retrieval bug is fixed so the benchmark protects that behavior.
