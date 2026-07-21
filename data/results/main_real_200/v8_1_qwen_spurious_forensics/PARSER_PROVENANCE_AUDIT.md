# Parser and Provenance Audit

`paper_evidence=false`

| Provider | Rows | Items | Parse ok | Provider ok | Pairing ok | Could affect Qwen result |
| --- | ---: | ---: | ---: | --- | --- | --- |
| `qwen2_5_vl_7b` | 188 | 94 | 188 | True | True | False |
| `internvl_8b` | 188 | 94 | 188 | True | True | False |
| `llava_onevision_7b` | 188 | 94 | 188 | True | True | False |

## Shard Merge

| Provider | Zip exists | Shard rows | Merged member rows | Shards match canonical order | Shard rows match as set | Merged member matches canonical |
| --- | --- | ---: | ---: | --- | --- | --- |
| `qwen2_5_vl_7b` | True | 188 | 188 | False | True | True |
| `internvl_8b` | True | 188 | 188 | False | True | True |
| `llava_onevision_7b` | True | 188 | 188 | False | True | True |

## Qwen Auxiliary Ingestion

Qwen polarity used the zip-member canonical source, not the top-level shard0-only file. Qwen mechanism is complete and provider-consistent.

`__CTRL__` path resolution: 94/94 originals and 94/94 edited images resolved.

Finding: no parser, merge, provider-name, or provenance issue was found that could explain or reduce the Qwen 12/94 result.
