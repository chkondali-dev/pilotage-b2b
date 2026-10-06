"""Phase 1.2 — statuts explicites de push_csv_to_github. MOCKS uniques, zéro réseau,
zéro écriture sur le dépôt réel (REPO_ROOT redirigé vers tmp_path)."""
import base64

import pytest

import utils.github as gh


class _Resp:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class _FakeRequests:
    """Double de utils.github.requests."""

    def __init__(self, get_resp=None, put_resp=None, get_raises=None):
        self.get_resp = get_resp
        self.put_resp = put_resp
        self.get_raises = get_raises
        self.get_calls = []
        self.put_calls = []

    def get(self, url, **kw):
        self.get_calls.append(url)
        if self.get_raises is not None:
            raise self.get_raises
        return self.get_resp

    def put(self, url, **kw):
        self.put_calls.append((url, kw))
        return self.put_resp


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(gh, "REPO_ROOT", tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "registre.csv").write_text(
        "code;statut\nX;Prospection\n", encoding="utf-8")
    return tmp_path


def _run(monkeypatch, req, token="tok-secret-XYZ", **kw):
    monkeypatch.setattr(gh, "_get_token", lambda: token)
    monkeypatch.setattr(gh, "requests", req)
    return gh.push_csv_to_github("data/registre.csv", "test [auto]", **kw)


def test_no_token_status_explicite(repo, monkeypatch):
    req = _FakeRequests()
    res = _run(monkeypatch, req, token="")
    assert res["ok"] is False and res["status"] == "no_token"
    assert req.get_calls == []  # aucun appel réseau sans token


def test_synced_sends_sha_and_content(repo, monkeypatch):
    req = _FakeRequests(get_resp=_Resp(200, {"sha": "aaa111"}),
                        put_resp=_Resp(201))
    res = _run(monkeypatch, req, base_sha="aaa111")
    assert res["ok"] is True and res["status"] == "synced"
    assert len(req.put_calls) == 1
    payload = req.put_calls[0][1]["json"]
    assert payload["sha"] == "aaa111"
    content = base64.b64decode(payload["content"])
    assert b"X;Prospection" in content
    assert payload["branch"] == "main"


def test_remote_changed_refuse_ecrasement(repo, monkeypatch):
    """Le distant a changé depuis la lecture → REFUS, PUT jamais appelé."""
    req = _FakeRequests(get_resp=_Resp(200, {"sha": "bbb222"}),
                        put_resp=_Resp(200))
    res = _run(monkeypatch, req, base_sha="aaa111")
    assert res["ok"] is False and res["status"] == "remote_changed"
    assert "aaa111" in res["detail"] and "bbb222" in res["detail"]
    assert req.put_calls == []


def test_sans_base_pas_de_comparaison(repo, monkeypatch):
    """base_sha=None (compat) : pas de détection, push possible."""
    req = _FakeRequests(get_resp=_Resp(200, {"sha": "bbb222"}),
                        put_resp=_Resp(200))
    res = _run(monkeypatch, req)
    assert res["ok"] is True


def test_distant_absent_creation(repo, monkeypatch):
    req = _FakeRequests(get_resp=_Resp(404), put_resp=_Resp(201))
    res = _run(monkeypatch, req, base_sha=None)
    assert res["ok"] is True
    payload = req.put_calls[0][1]["json"]
    assert "sha" not in payload  # création, pas d'écrasement


def test_put_ko_http_error(repo, monkeypatch):
    req = _FakeRequests(get_resp=_Resp(200, {"sha": "aaa111"}),
                        put_resp=_Resp(422))
    res = _run(monkeypatch, req, base_sha="aaa111")
    assert res["ok"] is False and res["status"] == "http_error"
    assert "422" in res["detail"]


def test_exception_attrapee_sans_jamais_le_token(repo, monkeypatch):
    req = _FakeRequests(get_raises=RuntimeError("boom reseau"))
    res = _run(monkeypatch, req, token="tok-secret-XYZ", base_sha=None)
    assert res["ok"] is False and res["status"] == "exception"
    assert "boom reseau" in res["detail"]
    assert "tok-secret" not in res["detail"]
    # jamais de trace de token dans les valeurs retournées
    assert "tok-secret" not in str(res)


def test_local_absent(repo, monkeypatch):
    (repo / "data" / "registre.csv").unlink()
    req = _FakeRequests()
    res = _run(monkeypatch, req)
    assert res["ok"] is False and res["status"] == "no_local_file"
    assert req.get_calls == []


def test_file_sha_est_le_blob_git(tmp_path):
    """file_sha = sha blob git (même algorithme que l'API contents GitHub)."""
    f = tmp_path / "f.csv"
    f.write_bytes(b"hello")
    assert gh.file_sha(f) == gh.git_blob_sha1(b"hello")
    # contenu différent → sha différent (détection de changement)
    f.write_bytes(b"hello!")
    assert gh.file_sha(f) != gh.git_blob_sha1(b"hello")
    assert gh.file_sha(tmp_path / "absent.csv") is None
