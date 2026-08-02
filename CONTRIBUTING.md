# Contributing

Thanks for helping improve رحلة الباحث. Content corrections are especially welcome — if a question,
answer key, or explanation is wrong, that is a bug worth reporting.

## Before you write code

**Open an issue first.** Use the *Content error* template for anything about a question's accuracy,
*Bug report* for broken behaviour, and *Feature request* for new ideas. Discussing first avoids work
that gets rejected on scope.

## Branch and PR flow

```
issue  →  branch  →  PR into dev  →  PR dev into main  →  release vX.Y.Z  →  auto-deploy
```

- Branch from `dev`, named `feat/<issue#>-<slug>` or `fix/<issue#>-<slug>`.
- **All PRs target `dev`.** `main` only ever receives `dev`, and only for a release.
- Both branches are protected: CI must pass, no direct pushes.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `test:`,
`refactor:`, `chore:`, `ci:`. Add a scope where it helps — `feat(seed): …`. Release notes are
generated from these, so write the subject for a reader, not for yourself.

## Tests are not optional

```bash
./scripts/test.sh      # must pass before you open a PR
```

New behaviour needs a test that fails without your change. Backend tests live in `backend/tests/`
(pytest), frontend tests in `frontend/tests/` (Vitest + jsdom).

## Content changes

Quiz content is `content/questions/<station>.json`, validated by `app.content_schema.validate_quiz`.

- Every question needs a non-empty `concept` — it feeds the mastery dashboard.
- Prefer **application** over recall: give an artifact and ask for a decision.
- Factual claims must be groundable. Cite the standard where one applies (ICMJE, COPE, PRISMA,
  STROBE, CONSORT). Illustrative examples are fine when no real artifact exists — mark them as such.
- Content is baked into the release image, so a content change **ships as a release**, not a hotfix.
- Note: reseeding a station resets *that station's* leaderboard. This is expected.

## Architecture rules worth knowing

- **stdlib `sqlite3` only** — no ORM, no new database dependency.
- `concept` lives inside `questions.data_json` and is read in Python; there is no JSON1 dependency
  and no `concept` column.
- Never hand-edit the `?v=` cache-busting stamps in `frontend/index.html` — `main.py` generates them.

## Reporting security issues

Do not open a public issue. See [`SECURITY.md`](SECURITY.md).
