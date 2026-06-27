from app.models import insert_issue_report, list_issue_reports


def test_insert_and_list_issue_reports(conn):
    insert_issue_report(conn, {
        "telegram_user_id": 5, "username": "lina", "first_name": "Lina",
        "language_code": "ar", "is_premium": 1, "text": "زر لا يعمل",
        "platform": "ios", "raw_json": "{}",
    })
    insert_issue_report(conn, {"telegram_user_id": 6, "text": "ملاحظة"})
    rows = list_issue_reports(conn, limit=10)
    assert len(rows) == 2
    assert rows[0]["telegram_user_id"] == 6
    assert rows[1]["username"] == "lina"
    assert rows[1]["text"] == "زر لا يعمل"
