"""P2-102/P2-103 — every /session/* route requires a valid Firebase token,
and a token that's valid for one user must not unlock another user's session.
"""

from unittest.mock import patch

from conftest import fake_decoded_token, seed_session


def _auth_header(uid: str) -> dict:
    # The token value itself doesn't matter — verify_id_token is mocked below
    # to always resolve to `uid` regardless of what string is passed.
    return {"Authorization": f"Bearer token-for-{uid}"}


OWNED_ROUTES = [
    ("get", "/session/{sid}/state"),
    ("get", "/session/{sid}/report"),
    ("get", "/session/{sid}/logs"),
]


def test_missing_authorization_header_is_401(client):
    seed_session("S_noauth", owner_uid="user_A")
    resp = client.get("/session/S_noauth/state")
    assert resp.status_code == 401


def test_malformed_authorization_header_is_401(client):
    seed_session("S_badauth", owner_uid="user_A")
    resp = client.get("/session/S_badauth/state", headers={"Authorization": "Basic notabearertoken"})
    assert resp.status_code == 401


@patch("firebase_admin.auth.verify_id_token")
def test_invalid_token_is_401(mock_verify, client):
    mock_verify.side_effect = Exception("token expired")
    seed_session("S_expired", owner_uid="user_A")
    resp = client.get("/session/S_expired/state", headers=_auth_header("user_A"))
    assert resp.status_code == 401


@patch("firebase_admin.auth.verify_id_token")
def test_owner_can_read_their_own_session(mock_verify, client):
    mock_verify.return_value = fake_decoded_token("user_A")
    seed_session("S_owned", owner_uid="user_A")
    resp = client.get("/session/S_owned/state", headers=_auth_header("user_A"))
    assert resp.status_code == 200
    assert resp.json()["session_id"] == "S_owned"


@patch("firebase_admin.auth.verify_id_token")
def test_cross_user_access_is_403_on_state_report_and_logs(mock_verify, client):
    seed_session("S_cross", owner_uid="user_A", status="completed", final_scores={"overall": 80})

    for method, path_tpl in OWNED_ROUTES:
        path = path_tpl.format(sid="S_cross")
        mock_verify.return_value = fake_decoded_token("user_B")
        resp = getattr(client, method)(path, headers=_auth_header("user_B"))
        assert resp.status_code == 403, f"{path} leaked to a non-owner: {resp.status_code} {resp.text}"


@patch("firebase_admin.auth.verify_id_token")
def test_cross_user_answer_is_403(mock_verify, client):
    seed_session("S_cross_answer", owner_uid="user_A")
    mock_verify.return_value = fake_decoded_token("user_B")
    resp = client.post(
        "/session/S_cross_answer/answer",
        json={"answer_text": "hello"},
        headers=_auth_header("user_B"),
    )
    assert resp.status_code == 403


@patch("firebase_admin.auth.verify_id_token")
def test_cross_user_end_is_403(mock_verify, client):
    seed_session("S_cross_end", owner_uid="user_A")
    mock_verify.return_value = fake_decoded_token("user_B")
    resp = client.post(
        "/session/S_cross_end/end",
        json={"reason": "manual_end"},
        headers=_auth_header("user_B"),
    )
    assert resp.status_code == 403


@patch("firebase_admin.auth.verify_id_token")
def test_nonexistent_session_is_404_even_with_valid_auth(mock_verify, client):
    # No session seeded at all — should 404 before any ownership check runs.
    mock_verify.return_value = fake_decoded_token("user_A")
    resp = client.get("/session/S_does_not_exist/state", headers=_auth_header("user_A"))
    assert resp.status_code == 404
