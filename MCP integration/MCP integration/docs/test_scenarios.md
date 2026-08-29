# Test scenarios

## Scenario 1 — Resource discovery

Expected:

- `filesystem://config`
- `filesystem://resumes`

## Scenario 2 — Tool discovery

Expected tools:

- list_files
- read_file
- write_file
- delete_file
- move_file
- watch_directory
- batch_process

## Scenario 3 — Batch processing

Input:

```text
directory=resumes
pattern=*.txt
```

Expected: at least 3 resume records.

## Scenario 4 — Matching

Job:

```text
Python SQL Docker Linux backend REST API
```

Expected: Alice should rank highly because several terms overlap.

## Scenario 5 — Security

Attempt:

```text
../outside.txt
```

Expected: rejected by path validation.

## Scenario 6 — Watch

Call `watch_directory` for 15 seconds and create a new text file in `data/resumes`.

Expected: the newly created file appears in the result.

## Scenario 7 — End-to-end

Run:

```powershell
python matching_agent.py
```

Expected:

1. MCP initializes.
2. Tools/resources are discovered.
3. `batch_process` is called through MCP.
4. LangGraph ranks resumes.
5. `write_file` is called through MCP.
6. `data/output/matching_report.md` is created.
