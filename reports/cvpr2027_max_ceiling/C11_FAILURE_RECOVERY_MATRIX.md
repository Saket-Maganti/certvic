# C11 failure and recovery matrix

| Failure | Safe retry? | New permission? | Rerun? | Preserve | Human action | Scientific consequence |
| --- | --- | --- | --- | --- | --- | --- |
| download interrupted | True | False | True | completed remote output and hashes | redownload | none if hash-valid |
| Kaggle session reset | True | depends | True | downloaded checkpoints and immutable inputs | restart only under same valid permission | rerun disclosure |
| disk full | True | False | True | journals, immutable inputs, completed shards | free space without deleting evidence | none if validated resume |
| CUDA OOM | True | depends | True | failure report and unchanged contract | apply only predeclared fallback or mint new permission | precision/quantization change is separate evidence identity |
| snapshot missing | True | False | True | inputs | attach authenticated snapshot | no evidence produced |
| snapshot hash mismatch | False | True | True | mismatch record and bytes | obtain exact snapshot and new binding | reject entire return |
| wrong provider snapshot | False | True | True | failure report | attach correct provider snapshot | reject entire return |
| wrong permission | False | True | True | permission and audit log | mint correctly bound permission | reject entire return |
| expired permission | False | True | True | expired permission | mint new permission | no launch allowed |
| consumed nonce | False | True | True | ledger | mint a new nonce | replay rejected |
| duplicate return | True | False | False | first committed return | idempotent import/compare hashes | conflict blocks import |
| corrupt ZIP | True | False | True | remote output if present | redownload then rerun if still corrupt | not evidence |
| missing row | False | True | True | raw shards and manifest | rerun missing task under fresh permission | incomplete evidence |
| duplicate row | False | True | True | raw rows | resolve run-contract violation then rerun | reject return |
| parser crash | conditional | depends | depends | raw model text | repair parser only under declared versioning policy | new parser identity or fail-closed missing |
| partial generation | True | False | True | generation journal and completed images | resume deterministic uncompleted items | validate final census |
| review sheet incomplete | True | False | False | original sheet | same human finishes blank rows | review gate stays blocked |
| review packet mutated | False | False | True | original packet and sheets | rebuild/refreeze and restart review | invalidate labels tied to old hash |
| selection imbalance | False | False | False | census and solver trace | declare infeasible or abandon before outcomes | cannot tune after model outcomes |
| detectability failure | False | False | False | all images/audits | do not promote; predeclare new future study | prospective gate fails |
| transaction journal interrupted | True | False | False | journal, staging bytes, destination | resume/recover transaction | no partial promotion |
| analysis crash | True | False | False | immutable inputs | repair deterministic CPU analysis | no evidence change if outputs match |
| figure/table regeneration mismatch | False | False | False | both outputs and upstream manifest | investigate environment/code/input drift | release blocked |
