# Operations and security

- Keep .env, Angel One API key, client code, PIN, TOTP secret, JWT, refresh token and feed token out of Git.
- Treat the TOTP secret as equivalent to a password; store it only on the local workstation.
- Never send broker credentials or OTPs through Telegram or chat.
- Keep SDK logs under the ignored logs/ directory and inspect them for accidental sensitive data before sharing.
- Use HTTPS and authentication for any future webhook receiver.
- Validate webhook tokens/signatures and rate-limit endpoints.
- Redact secrets from logs and screenshots.
- Keep local backups encrypted and access-controlled.
- Verify market-data licensing before storing, deriving or redistributing data.
- Do not scrape or reverse engineer charting platforms.
- Keep all orders manual in v1; no order-placement endpoints are called by IADEW.
- Before adding automated order routing, review current SEBI, exchange, broker and API requirements.
