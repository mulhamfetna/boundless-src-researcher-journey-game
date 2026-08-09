#!/usr/bin/env python3
"""Remove test accounts that were written into the production database (#40).

Three fake contestants were created by running live verification against
production — 9001 "Jinx" and 9002 "Ekko" (duel feature), and 99001
"DebugTester". They are not real people: they inflate the user count and are
unreachable on every broadcast.

Safe by design:
  * refuses to touch an id that has any recorded attempt (that would be a real
    player, and the whole point is to remove only fixtures),
  * prints what it will do and requires --apply to actually write,
  * take a backup first: `~/mulham/src/backup.sh`.

Usage, inside the web container:
    python /srv/scripts/remove_test_fixtures.py            # dry run
    python /srv/scripts/remove_test_fixtures.py --apply
"""
import argparse
import sqlite3
import sys

TEST_IDS = (9001, 9002, 99001)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="/data/quiz.db")
    ap.add_argument("--apply", action="store_true", help="actually delete (default: dry run)")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    marks = ",".join("?" * len(TEST_IDS))

    present = [r["telegram_user_id"] for r in conn.execute(
        f"SELECT telegram_user_id FROM contestants WHERE telegram_user_id IN ({marks})", TEST_IDS)]
    if not present:
        print("nothing to do — no test fixtures found")
        return 0

    # Guard: never remove anyone who has actually played.
    with_attempts = [r["contestant_id"] for r in conn.execute(
        f"SELECT DISTINCT contestant_id FROM attempts WHERE contestant_id IN ({marks})", TEST_IDS)]
    if with_attempts:
        print(f"REFUSING: {with_attempts} have recorded attempts and may be real players.")
        return 1

    badges = conn.execute(
        f"SELECT COUNT(*) n FROM badges WHERE contestant_id IN ({marks})", TEST_IDS).fetchone()["n"]
    duels = conn.execute(
        f"SELECT COUNT(*) n FROM duels WHERE creator_id IN ({marks}) OR opponent_id IN ({marks})",
        TEST_IDS + TEST_IDS).fetchone()["n"]

    print(f"fixtures found : {present}")
    print(f"orphan badges  : {badges}")
    print(f"test duels     : {duels}")
    print(f"attempts       : 0 (guard passed)")

    if not args.apply:
        print("\ndry run — re-run with --apply to delete")
        return 0

    conn.execute(f"DELETE FROM duels WHERE creator_id IN ({marks}) OR opponent_id IN ({marks})",
                 TEST_IDS + TEST_IDS)
    conn.execute(f"DELETE FROM badges WHERE contestant_id IN ({marks})", TEST_IDS)
    conn.execute(f"DELETE FROM contestants WHERE telegram_user_id IN ({marks})", TEST_IDS)
    conn.commit()

    remaining = [dict(r) for r in conn.execute(
        "SELECT telegram_user_id, username, first_name FROM contestants ORDER BY telegram_user_id")]
    print("\ndeleted. remaining contestants:")
    for r in remaining:
        print(f"  {r['telegram_user_id']} | @{r['username'] or '-'} | {r['first_name']}")
    print("integrity:", conn.execute("PRAGMA integrity_check").fetchone()[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
