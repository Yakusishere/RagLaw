# Repository Security And Secrets

This repository is intended to be uploaded to GitHub. To reduce accidental leakage, local configuration and credentials must follow the rules below.

## 1. Allowed committed files

These files may be committed:

- `.env.example`
- documentation under `docs/`
- source code, SQL, scripts, frontend source
- curated project data that is intentionally part of the repository

## 2. Forbidden committed files

These files must never be committed:

- real API keys
- access tokens
- local `.env` files
- machine-specific database URLs with real passwords
- temporary exports and private notes
- anything placed under `.secrets/` except `.secrets/README.md`

## 3. Local config convention

Use the following locations:

- `.env.local`
  - main local runtime configuration
  - application env vars such as `DATABASE_URL` and `OPENAI_API_KEY`

- `.secrets/`
  - one-off private files that should never be tracked
  - raw tokens, copied credentials, scratch secrets

Use `.env.example` as the committed template for new machines.

## 4. Recommended workflow

1. Copy `.env.example` to `.env.local`
2. Fill in real local values only in `.env.local`
3. Put any extra sensitive artifacts in `.secrets/`
4. Before pushing, run `git status` and verify no secret files are staged

## 5. Current ignore policy

The root `.gitignore` currently excludes:

- `.codex/`
- Python caches and virtual environments
- `frontend/node_modules/`
- `frontend/dist/`
- `build/`
- `.env` and `.env.local`
- all secret files under `.secrets/` except the committed README

## 6. Notes for future backend work

When the backend application is added, it should load configuration from environment variables only. Do not hardcode keys in:

- Python source files
- shell scripts
- frontend code
- test fixtures that will be committed
