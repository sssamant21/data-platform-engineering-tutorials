# Chapter 081 — targeted expected-output review (2026-11-25)

Scope: [chapter](../../part-09-functions-views-json/081-string-functions-and-regular-expressions.md), blob `9f1ddc442e91a7dca7fb19ba789858456fd8e2ce`; [lab](../081-string-functions-and-regular-expressions.sql), blob `0825294f22fc538ecb71deb21557afb719fdd1af`, retrieved from main. Manual source reasoning only.

| ID | Trimmed email length | Code status | Case-insensitive flag | Mask |
|---|---:|---|---|---|
| 1 | 17 | valid | true | EVT-XXXX |
| 2 | 15 | valid | true | EVT-XXXX |
| 3 | NULL | invalid | true | evt-XXXX |
| 4 | 13 | invalid | false | BADXX |
| 5 | 17 | missing | false | NULL |

Lengths reconcile by counting local part, @ and domain. Case-sensitive matching rejects lowercase prefix; COALESCE converts the missing-code predicate to false, while masking preserves NULL. Two valid, two invalid, one missing reconcile to five rows. Both EXCEPT ALL directions and all six Boolean checks feed the final division guard. The chapter's standalone examples also reconcile. The lab sets ON_ERROR_STOP before BEGIN READ ONLY, sets local timeouts and rolls back; database/version checks do not establish isolation. No SQL was executed; no parser, comprehensive link audit or independent editorial acceptance claimed. No contradiction identified in this targeted review. This individual evidence does not by itself advance the sequential 079–084 batch counter.
