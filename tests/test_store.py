from app.store import connect, record_event


def test_durable_deduplication(tmp_path):
    path = str(tmp_path / "ledger.db")
    event = {"event_id": "e1", "order_id": "o1", "sku": "SYNTH-1", "quantity": 2}
    db = connect(path)
    assert record_event(db, event) is True
    assert record_event(db, event) is False
    db.close()
    reopened = connect(path)
    assert record_event(reopened, event) is False
    assert reopened.execute("SELECT COUNT(*) FROM processed_events").fetchone()[0] == 1
    reopened.close()
