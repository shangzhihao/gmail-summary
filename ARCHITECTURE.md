## Architecture Overview

### Components
- **CLI (`src/gmail_digest_tool/cli.py`)** – Parses user inputs, resolves defaults from settings, and invokes the orchestrator.
- **Configuration (`config/settings.py`)** – Pydantic settings layered over `.env`, storing path locations, LLM configuration, and logging level.
- **Logging (`utils/logging.py`)** – Centralized Loguru configuration used across the project.
- **Gmail Client (`clients/gmail_client.py`)** – Handles OAuth token acquisition/refresh and message retrieval via the Gmail API.
- **Filtering (`services/filters.py`)** – Resolves unread/time-range criteria and generates Gmail search queries.
- **Email Fetcher (`services/email_fetcher.py`)** – Applies filter logic, invokes the Gmail client, and returns normalized messages.
- **LLM Client (`clients/openai_client.py`)** – Wraps the OpenAI-compatible API with retry semantics.
- **Summarizer (`services/summarizer.py`)** – Crafts prompts for the LLM and produces structured summaries.
- **Digest Builder (`services/digest_builder.py`)** – Formats summaries into a human-readable text digest.
- **File Writer (`services/file_writer.py`)** – Persists the digest to a timestamped text file.

### Data Flow
1. **CLI Input** → Validate/normalize parameters (`unread`, `from`, `to`).
2. **Settings & Logging** → Load environment configuration and configure log output.
3. **Email Retrieval** → `EmailFetcher` builds filters, queries Gmail, and returns normalized `EmailMessage` objects.
4. **Summarization** → `Summarizer` sends prompts to the OpenAI-compatible client per email and returns `EmailSummary`.
5. **Digest Creation** → `build_digest` aggregates summaries and `write_digest` stores the result.
6. **Output** → CLI echoes the destination path for manual review.

### Key Decisions
- **Local Execution** – The workflow runs manually; there is no scheduler or AWS dependency.
- **Text Output** – Digests are stored locally as text files for portability and simplicity.
- **Strict Typing & Testing** – Pydantic models ensure structured data; unit tests cover core logic.
- **Retry Strategy** – LLM calls retry up to three times with exponential backoff to handle transient failures.

### Extension Points
- Add HTML digest rendering or alternative output channels (e.g., Slack).
- Introduce caching for Gmail message bodies to minimize API calls.
- Schedule periodic runs via cron or task runners if automation becomes necessary.
