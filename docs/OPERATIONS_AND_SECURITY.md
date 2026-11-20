# Operations and security

- Keep .env, tokens, broker statements and personal trade logs out of Git.
- Use least-privilege app permissions where available.
- Never send broker credentials through Telegram.
- Use HTTPS and authentication for webhook receivers.
- Validate webhook tokens/signatures and rate-limit endpoints.
- Redact secrets from logs.
- Keep local backups encrypted and access-controlled.
- Verify market-data licensing before storing, deriving or redistributing data.
- Do not scrape or reverse engineer charting platforms.
- Keep all orders manual in v1; no order-placement endpoints are included.
- Before adding automated order routing, review current SEBI, exchange, broker and API requirements.
