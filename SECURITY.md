# Security Policy

## Reporting a vulnerability

**Please do not open a public issue for a security problem.**

Report it privately through
[GitHub Security Advisories](https://github.com/mulhamfetna/boundless-src-researcher-journey-game/security/advisories/new),
or by email to **contact@mulhamfetna.com**.

Please include what you found, how to reproduce it, and what an attacker could achieve. You can
expect an acknowledgement within a few days, and credit in the fix release unless you prefer
otherwise.

## Supported versions

The latest release is supported. Fixes ship in a new release rather than as patches to older tags.

## Known and accepted design trade-offs

These are documented decisions, not vulnerabilities — please don't report them as such:

- **Answer keys reach the client.** `GET /questions` returns a concept-balanced sample *including*
  answer keys, and the client checks answers locally (Khan-Academy style) so feedback is instant.
  Scores are therefore **not tamper-proof**. This is a deliberate trade-off in a teaching tool with
  no stakes attached to the leaderboard.
- **Attempt submission is authenticated** via Telegram `initData` HMAC, so attempts are attributed
  to a real Telegram user even though the score itself is client-computed.

## What is genuinely in scope

Anything that lets someone read or modify **other users' data**, escape the container, reach the
host, leak secrets from the environment, or take over the bot — for example `initData` verification
flaws, SQL injection, path traversal in static file serving, or secrets exposure in logs or images.
