# Repository replacement validation

| Check | Result |
| --- | --- |
| Exact repaired full archive present | FAIL — absent |
| Unambiguous fallback full archive present | FAIL — absent |
| Patch/release/provider archive rejected | PASS |
| Unsafe extraction avoided | PASS |
| Live checkout preserved | PASS |
| Nested repository avoided | PASS |
| Historical raw evidence rewritten | PASS — no |
| Replacement completed | FAIL — not authorized without source bytes |

Final replacement state: `BLOCKED_SOURCE_ARCHIVE_MISSING`. This blocker is not converted into a
software-success claim.

