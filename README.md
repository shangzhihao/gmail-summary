## Gmail LLM Digest Tool

This project generates a local Gmail digest by summarizing emails with an OpenAI-compatible multilingual LLM. Run it manually from your workstation, filter by unread/all messages, and optionally restrict the time range.

For now, this is only tested on Apple Silicon (arm64) macOS environment.


### Features
- OAuth-backed Gmail client that reads inbox messages (excluding spam/trash).
- Configurable filters for unread status and time window (`from`/`to` or rolling 24 hours).
- OpenAI-compatible summarization with retry logic.
- Digest rendering to timestamped text files under `artifacts/digests/`.
- Cumulative summary log stored in `artifacts/summary.csv` (newest-first, with received timestamps) to skip already-processed emails.
- Typer-powered CLI with structured logging and configuration via `.env`.

### Requirements
- Python 3.12+
- Google Workspace or Gmail account with API access enabled.
- OpenAI API key (Dashscope or other compatible providers work as well).


### Setup
1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -e .[dev]
   ```
3. Copy credential templates:
   ```bash
   cp .env.example .env
   cp credentials.template.json credentials.json
   ```
4. Populate `.env` with your LLM credentials (`OPENAI_API_KEY`, optional `OPENAI_BASE_URL`, and `OPENAI_MODEL` if you want to override the default). Legacy variables (`DIGEST_*` / `DASHSCOPE_*`) remain supported for backward compatibility. Optionally adjust `DIGEST_SUMMARY_CSV_PATH` to relocate the summary ledger.
5. Provide Gmail OAuth client credentials in `credentials.json`.

### Running the Digest
```bash
python scripts/run_digest.py generate --unread \
  --from-datetime 2024-01-01T00:00:00Z \
  --to-datetime 2024-01-02T00:00:00Z
```
Omit the datetime parameters to default to the trailing 24 hours. Use `--all` to include read messages.

The generated digest path is echoed and stored in `artifacts/digests/`.

Every run rewrites `artifacts/summary.csv` (`email_id,sender,summary,received_at`) in newest-first order and skips any Gmail messages that were previously summarized.

### Testing
Run static checks and unit tests:
```bash
ruff check src tests
ruff format --check src tests
mypy src
pytest
```
GitHub Actions (workflow `CI`) runs `pytest` automatically for pushes to `main` and all pull requests using Python 3.12 on Ubuntu 24.04.

### OAuth Token Handling
The first run launches a browser-based OAuth flow. Tokens persist to `token.json` (configurable) and are refreshed automatically on subsequent runs.
