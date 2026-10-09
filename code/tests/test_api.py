"""API integration tests: the demo script end-to-end, server side (FR-1..FR-8, NFR-SEC-*, NFR-REL-*)."""

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from api.config import Settings
from api.testing import ScriptedBrowser
from crypto import ShamirError
from crypto.envelope import rsa_generate_jwk_pair
from vault.db import Database

TRUSTEES = ["alice@example.com", "bob@example.com", "carol@example.com"]
ADMIN = {"X-Demo-Token": "admin-token"}


def make_client(**overrides) -> TestClient:
    options = dict(database_url="sqlite://", demo_mode=True, demo_admin_token="admin-token",
                   cron_secret="cron-secret", app_base_url="http://testserver")
    settings = Settings(**{**options, **overrides})
    return TestClient(create_app(settings, db=Database("sqlite://")))


@pytest.fixture
def client():
    with make_client() as c:
        yield c


def register(client, email="owner@example.com", password="correct horse"):
    return client.post("/api/auth/register", json={"email": email, "password": password})


def advance(client, seconds):
    client.post("/api/demo/clock/advance", json={"seconds": seconds}, headers=ADMIN).raise_for_status()
    return client.post("/api/demo/tick", headers=ADMIN).json()


def demo_vault(client, k=2, interval=120, grace=60, message="the will is in the blue box"):
    return ScriptedBrowser(client).create_vault(owner_email="owner@example.com", password="correct horse",
                                                trustee_emails=TRUSTEES, k=k, interval_s=interval, grace_s=grace,
                                                message=message)


# --- FR-1 auth -------------------------------------------------------------------------

def test_register_login_logout_me(client):
    assert register(client).status_code == 201
    assert client.get("/api/me").json()["email"] == "owner@example.com"
    assert register(client).status_code == 409
    client.post("/api/auth/logout")
    assert client.get("/api/me").status_code == 401
    bad = {"email": "owner@example.com", "password": "wrong pass"}
    assert client.post("/api/auth/login", json=bad).status_code == 401
    good = {"email": "OWNER@example.com", "password": "correct horse"}  # emails are case-insensitive
    assert client.post("/api/auth/login", json=good).status_code == 200


def test_session_cookie_is_httponly_and_lax(client):
    header = register(client).headers["set-cookie"].lower()
    assert "httponly" in header and "samesite=lax" in header


def test_passwords_are_argon2_hashed(client):
    register(client)
    with client.app.state.db.session() as s:
        from vault.models import Owner

        owner = s.query(Owner).one()
        assert owner.password_hash.startswith("$argon2id$") and "correct horse" not in owner.password_hash


def test_validation_errors_use_one_shape(client):
    r = client.post("/api/auth/register", json={"email": "nope", "password": "x"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


# --- FR-3 / FR-4 configuration ------------------------------------------------------------

@pytest.mark.parametrize("k,code", [(1, "invalid_threshold"), (4, "invalid_threshold")])
def test_threshold_rules(client, k, code):
    register(client)
    r = client.post("/api/vaults", json={"trustee_emails": TRUSTEES, "k": k, "interval_s": 120, "grace_s": 60})
    assert r.status_code == 422 and r.json()["error"]["code"] == code


def test_k_equals_n_warns_and_reports_loss_tolerance(client):
    register(client)
    r = client.post("/api/vaults", json={"trustee_emails": TRUSTEES, "k": 3, "interval_s": 120, "grace_s": 60})
    assert r.status_code == 201
    body = r.json()
    assert body["loss_tolerance"] == 0 and "unrecoverable" in body["warnings"][0]


def test_one_vault_per_owner_and_owner_cannot_be_trustee(client):
    register(client)
    r = client.post("/api/vaults", json={"trustee_emails": ["owner@example.com", "b@x.io"], "k": 2,
                                          "interval_s": 120, "grace_s": 60})
    assert r.json()["error"]["code"] == "owner_as_trustee"
    ok = {"trustee_emails": TRUSTEES, "k": 2, "interval_s": 120, "grace_s": 60}
    assert client.post("/api/vaults", json=ok).status_code == 201
    assert client.post("/api/vaults", json=ok).status_code == 409


def test_duplicate_trustees_rejected(client):
    register(client)
    r = client.post("/api/vaults", json={"trustee_emails": ["a@x.io", "A@x.io"], "k": 2, "interval_s": 120,
                                          "grace_s": 60})
    assert r.status_code == 422


def test_production_mode_requires_a_one_day_interval():
    with make_client(demo_mode=False) as c:
        register(c)
        r = c.post("/api/vaults", json={"trustee_emails": TRUSTEES, "k": 2, "interval_s": 3600, "grace_s": 60})
        assert r.json()["error"]["code"] == "interval_too_short"
        assert c.post("/api/demo/clock/advance", json={"seconds": 5}, headers=ADMIN).status_code == 403


def test_jwt_secret_required_over_https():
    with pytest.raises(RuntimeError):
        create_app(Settings(app_base_url="https://aegis.example"), db=Database("sqlite://"))


# --- enrolment ----------------------------------------------------------------------------

def test_enrolment_rejects_private_keys_and_wrong_sizes(client):
    register(client)
    created = client.post("/api/vaults", json={"trustee_emails": TRUSTEES, "k": 2, "interval_s": 120,
                                               "grace_s": 60}).json()
    token = created["invites"][0]["link"].rsplit("/", 1)[1]
    public, private = rsa_generate_jwk_pair()
    assert client.post(f"/api/trustee/enrol/{token}", json={"public_key_jwk": private}).json()["error"]["code"] == \
        "private_key_uploaded"
    small = {**public, "n": public["n"][:100]}
    assert client.post(f"/api/trustee/enrol/{token}", json={"public_key_jwk": small}).status_code == 422
    assert client.get(f"/api/trustee/invite/{token}").json()["can_enrol"] is True
    assert client.post(f"/api/trustee/enrol/{token}", json={"public_key_jwk": public}).status_code == 200
    vault_id = created["vault_id"]
    r = client.post(f"/api/vaults/{vault_id}/payload", json={"ciphertext_b64": "AAAA", "iv_b64": "AAAA", "blobs": []})
    assert r.json()["error"]["code"] == "trustees_not_enrolled"


def test_invite_links_can_be_reissued_before_enrolment(client):
    register(client)
    created = client.post("/api/vaults", json={"trustee_emails": TRUSTEES, "k": 2, "interval_s": 120,
                                               "grace_s": 60}).json()
    old = created["invites"][0]
    new = client.post(f"/api/vaults/{created['vault_id']}/trustees/{old['trustee_id']}/invite").json()
    assert new["link"] != old["link"]
    assert client.get(f"/api/trustee/invite/{old['link'].rsplit('/', 1)[1]}").status_code == 404


# --- FR-2 / FR-2a upload and the zero-knowledge server ---------------------------------------

def test_upload_arms_the_vault_and_server_holds_only_ciphertext(client):
    v = demo_vault(client)
    summary = client.get("/api/vaults/mine").json()["vault"]
    assert summary["state"] == "active" and summary["payload_uploaded"] and summary["loss_tolerance"] == 1
    view = client.get(f"/api/vaults/{v.vault_id}/server-view").json()
    assert len(view["share_blobs"]) == 3 and view["row"]["payload_ciphertext"]["length_bytes"] > 16
    raw = repr(view)
    assert v.message not in raw and v.key.hex() not in raw
    # second upload refused
    assert client.post(f"/api/vaults/{v.vault_id}/payload", json={"ciphertext_b64": "AAAA", "iv_b64": "AAAA",
                                                                  "blobs": []}).status_code == 409


# --- FR-5 .. FR-8 lifecycle --------------------------------------------------------------------

def test_dashboard_check_in_resets_the_deadline(client):
    demo_vault(client)
    before = client.get("/api/vaults/mine").json()["vault"]["deadline_at"]
    client.post("/api/demo/clock/advance", json={"seconds": 100}, headers=ADMIN)
    vault_id = client.get("/api/vaults/mine").json()["vault"]["id"]
    after = client.post(f"/api/vaults/{vault_id}/checkin").json()["vault"]["deadline_at"]
    assert after > before


def test_full_lifecycle_prompt_link_release_and_k_of_n_recovery(client):
    v = demo_vault(client)
    browser = ScriptedBrowser(client)
    assert client.get(f"/api/trustee/blob/{v.trustee_tokens[0]}").json()["error"]["code"] == "not_released"

    tick = advance(client, 121)  # past the deadline -> Warning + prompt
    assert tick["transitions"][0]["to_state"] == "warning"
    prompt = next(e for e in client.get("/api/demo/outbox", headers=ADMIN).json()["emails"]
                  if e["kind"] == "checkin_prompt")
    token = prompt["body"].split("/checkin/")[1].split()[0]
    assert client.get(f"/api/checkin/{token}").json()["status"] == "valid"   # preview, no side effect
    assert client.post(f"/api/checkin/{token}").json()["state"] == "active"  # one click (FR-6)
    assert client.post(f"/api/checkin/{token}").json()["error"]["code"] == "token_used"

    advance(client, 120 + 59)  # 1 s before deadline + grace: still not released (NFR-REL-1)
    assert client.get("/api/vaults/mine").json()["vault"]["state"] == "grace"
    tick = advance(client, 1)
    assert tick["transitions"][0]["to_state"] == "released"
    emails = client.get("/api/demo/outbox", headers=ADMIN).json()["emails"]
    assert sorted(e["to"] for e in emails if e["kind"] == "release") == sorted(TRUSTEES)
    assert advance(client, 5)["transitions"] == []  # no duplicate release

    # a release-email magic link opens the trustee portal
    release_link = next(e["body"] for e in emails if e["kind"] == "release").split("/trustee?t=")[1].split()[0]
    portal = client.get("/api/trustee/vaults", params={"t": release_link}).json()["vaults"][0]
    assert portal["blob_available"] is True

    assert browser.recover(v, [0, 2])["message"] == v.message  # any 2 of 3 (FR-8)
    assert browser.recover(v, [1, 2])["message"] == v.message
    with pytest.raises(ShamirError):  # one share alone is refused / meaningless (NFR-SEC-2)
        browser.recover(v, [1])

    vault_id = client.get("/api/vaults/mine").json()["vault"]["id"]
    assert client.post(f"/api/vaults/{vault_id}/checkin").json()["error"]["code"] == "checkin_rejected"


def test_lazy_due_check_releases_on_read(client):
    demo_vault(client, interval=60, grace=30)
    client.post("/api/demo/clock/advance", json={"seconds": 91}, headers=ADMIN)
    assert client.get("/api/vaults/mine").json()["vault"]["state"] == "released"  # no tick was run


def test_late_dashboard_check_in_is_refused(client):
    demo_vault(client, interval=60, grace=30)
    vault_id = client.get("/api/vaults/mine").json()["vault"]["id"]
    client.post("/api/demo/clock/advance", json={"seconds": 90}, headers=ADMIN)
    r = client.post(f"/api/vaults/{vault_id}/checkin")
    assert r.status_code == 409 and r.json()["error"]["state"] == "released"


# --- cron, demo, health ---------------------------------------------------------------------

def test_cron_requires_its_secret(client):
    assert client.post("/api/cron/tick").status_code == 403
    assert client.post("/api/cron/tick", headers={"X-Cron-Secret": "wrong"}).status_code == 403
    assert client.post("/api/cron/tick", headers={"X-Cron-Secret": "cron-secret"}).json()["trigger"] == "github-actions"
    assert client.get("/api/cron/tick", headers={"Authorization": "Bearer cron-secret"}).json()["trigger"] == \
        "vercel-cron"


def test_demo_console_requires_token_and_can_reset(client):
    assert client.get("/api/demo/outbox").status_code == 403
    demo_vault(client)
    assert len(client.get("/api/demo/vaults", headers=ADMIN).json()["vaults"]) == 1
    assert client.get("/api/demo/ticks", headers=ADMIN).status_code == 200
    vault_id = client.get("/api/demo/vaults", headers=ADMIN).json()["vaults"][0]["id"]
    assert client.get(f"/api/demo/server-view/{vault_id}", headers=ADMIN).json()["table"] == "vault"
    assert client.get("/api/demo/clock", headers=ADMIN).json()["demo_mode"] is True
    client.post("/api/demo/reset", headers=ADMIN)
    assert client.get("/api/demo/vaults", headers=ADMIN).json()["vaults"] == []


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["database"] == "sqlite"
