## Runbook

### Preconditions
- `.env` contains a valid OpenAI-compatible key (`OPENAI_API_KEY`; legacy `DIGEST_*`/`DASHSCOPE_*` variables remain supported).
- `credentials.json` holds Gmail OAuth client credentials with Gmail API enabled.
- Local Python environment has dependencies installed (`pip install -e .[dev]`).
- `artifacts/summary.csv` (or `DIGEST_SUMMARY_CSV_PATH`) persists prior summaries; delete it to force reprocessing.

### Generating a Digest
1. Run the CLI:
   ```bash
   python scripts/run_digest.py generate --unread
   ```
   - Optional: add `--from-datetime` / `--to-datetime` in ISO 8601 format.
   - Use `--all` to include read messages.
2. On first run, complete the browser-based OAuth consent flow; token writes to `token.json`.
3. Review the console output for the digest file path.
4. Inspect `artifacts/summary.csv` (newest first, with ISO timestamps) for the cumulative ledger of processed emails.
5. Open the generated file under `artifacts/digests/` to review summaries.

### Troubleshooting
- **Missing OAuth Token**: Delete `token.json` and rerun the CLI to reauthenticate.
- **Invalid LLM Key**: Update `.env` with a valid `OPENAI_API_KEY` and rerun.
- **Missing Summaries**: Confirm the target email IDs are absent from `summary.csv`; remove rows to reprocess.
- **Empty Digest**: Confirm time range and unread flag; check Gmail inbox for matching messages.
- **API Quota Errors**: Retry after quota resets; consider narrowing the time window.

### Maintenance
- Rotate the LLM key by updating `.env` and restarting the process.
- Refresh Gmail OAuth credentials by regenerating `credentials.json` if client secret rotates.
- Keep dependencies up-to-date via `pip install -e .[dev] --upgrade`.
- Run `pytest` and static analysis (`ruff`, `mypy`) before committing changes.
