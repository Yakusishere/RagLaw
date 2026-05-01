# Local Secrets Directory

Store non-committed local secrets and machine-only files here.

Recommended contents:

- exported API keys
- one-off OAuth tokens
- database dumps not meant for Git
- personal test notes with sensitive data

Rules:

- do not put source code here
- do not reference this directory from committed scripts unless the path is configurable
- do not rename this directory without updating `.gitignore`

This file is intentionally committed. Other files under `.secrets/` are ignored.

