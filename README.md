To deploy:
1. Generate `AUTH_KEY`:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(256))"
   ```
2. Paste `AUTH_KEY` into `.env` (see [`.env.example`](.env.example) for a template).,
3. Run from the project's root folder:
   ```bash
   doctl serverless deploy arxiv-feeds --remote-build
   ```
