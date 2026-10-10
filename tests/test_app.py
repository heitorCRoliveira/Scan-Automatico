from app import app


def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_index_ok():
    resp = client().get("/")
    assert resp.status_code == 200


def test_greet_contains_name():
    resp = client().get("/greet?name=Ana")
    assert resp.status_code == 200
    assert b"Ana" in resp.data


def test_user_lookup():
    resp = client().get("/user?name=alice")
    assert resp.status_code == 200
    assert resp.get_json()[0]["email"] == "alice@example.com"
