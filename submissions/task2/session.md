# Task 2 — Promotion CLI demo session

Captured 2026-06-01. Empty registry (no aliases set on `travel-assistant`) and no `promotion-log.jsonl` at the start. The session walks through every subcommand and every documented edge case: first promotion (unset → set), overwrite, successful rollback, second rollback (refused), and the multiplicity warning fired both during `set` and inside `rollback`'s re-resolution.

Note: prior to this session the registry already contained two registered versions tagged `config_id=v4` (versions 2 and 3) from earlier development. A second registration of `config_id=v5` (version 6) was created in parallel by running `python -m src.eval --config v5` while the demo ran, which is what powers the multiplicity warning in the final `set production v5` call.

---

### 1. `list` against an empty registry

No aliases exist yet, so the CLI prints the empty-state message.

```
$ python scripts/promote.py list
no aliases set
```

---

### 2. `set production v4` — first promotion

The alias was unset, so the summary shows `(unset) → v4`. The multiplicity warning fires because two MLflow versions are tagged `config_id=v4`; per spec the CLI picks the latest (`version 3`).

```
$ python scripts/promote.py set production v4
warning: multiple versions match config_id=v4 (MLflow versions [2, 3]); using latest (3)
production: (unset) → v4
```

---

### 3. `show production` — confirm the new target

Resolves the alias and prints tags + key metrics from the source eval run.

```
$ python scripts/promote.py show production
travel-assistant @ production
  model_version: 3
  config_id: v4
  model: nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B
  accuracy_overall: 0.95
  verdict_rate_leaked: 0.04
  total_cost_usd: $0.03
```

---

### 4. `set production v5` — overwrite

Moves the alias from v4 to v5. Multiplicity warning fires for v5 too (the parallel eval has finished by this point, leaving two v5 registrations).

```
$ python scripts/promote.py set production v5
warning: multiple versions match config_id=v5 (MLflow versions [4, 6]); using latest (6)
production: v4 → v5
```

---

### 5. `rollback production` — successful rollback

Walks the audit log backward, finds the previous target (`v4`), re-resolves it, and moves the alias back. Multiplicity warning fires a third time during the rollback's version lookup.

```
$ python scripts/promote.py rollback production
warning: multiple versions match config_id=v4 (MLflow versions [2, 3]); using latest (3)
production: v5 → v4 (rolled back)
```

---

### 6. `show production` — confirm rollback applied

Alias now resolves to v4 again (MLflow version 3, same as step 3's target).

```
$ python scripts/promote.py show production
travel-assistant @ production
  model_version: 3
  config_id: v4
  model: nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B
  accuracy_overall: 0.95
  verdict_rate_leaked: 0.04
  total_cost_usd: $0.03
```

---

### 7. `rollback production` — refused (single-step rollback by design)

The most recent log entry for `production` is the rollback we just wrote. Per spec the CLI refuses to roll back twice in a row and exits non-zero.

```
$ python scripts/promote.py rollback production
production was just rolled back; no further history to walk back to
```

---

### 8. `set production v5` — multiplicity warning, canonical demo

Per the spec, after re-running `eval --config v5` (which created MLflow version 6 alongside the existing version 4), a `set production v5` must trigger the multiplicity warning. It does.

```
$ python scripts/promote.py set production v5
warning: multiple versions match config_id=v5 (MLflow versions [4, 6]); using latest (6)
production: v4 → v5
```

---

### 9. `cat promotion-log.jsonl` — full audit trail

Four events were written across the session: the first `set` (with empty `from`), the overwrite, the rollback, and the final multiplicity-warning `set`. The two stop-without-writing cases (rollback-after-rollback in step 7) correctly produce no log lines.

```
$ cat promotion-log.jsonl
{"ts": "2026-06-01T09:57:36.649035+00:00", "alias": "production", "from": "", "to": "v4", "op": "set"}
{"ts": "2026-06-01T09:58:30.643414+00:00", "alias": "production", "from": "v4", "to": "v5", "op": "set"}
{"ts": "2026-06-01T09:58:52.433623+00:00", "alias": "production", "from": "v5", "to": "v4", "op": "rollback"}
{"ts": "2026-06-01T10:02:34.212742+00:00", "alias": "production", "from": "v4", "to": "v5", "op": "set"}
```
