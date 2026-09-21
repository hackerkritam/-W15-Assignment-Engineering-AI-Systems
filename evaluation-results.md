# Agent Evaluation Results

Task completion rate: **2/4**
Average trajectory length: **2.5 steps**
Total tokens: **105**

| Case | Status | Steps | Tokens | Tool calls | Injection |
|---|---|---:|---:|---|---|
| cross-source search then answer | success | 2 | 53 | - | none |
| tool calculation then answer | success | 2 | 52 | calculate -> 42 | none |
| failure injection unavailable tool | soft failure | 2 | 0 | - | tool unavailable |
| bounded repeated search | soft failure | 4 | 0 | - | repeated search |

Failure taxonomy counts: {"hard failure": 0, "soft failure": 2, "cascading soft failure": 0}
