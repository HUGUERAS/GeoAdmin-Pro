"""
Testes para o endpoint POST /auth/login (routes/auth.py).
Chamadas diretas à função, sem TestClient, seguindo o padrão do projeto.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

import routes.auth as auth_mod
from routes.auth import LoginPayload, login, logout


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_supabase(access_token="jwt.abc.123", refresh_token="ref.xyz",
                   uid="user-uuid-001", email="hugo@geoadmin.com",
                   session_none=False, user_none=False, raise_exc=None):
    sessao = None
    if not session_none:
        sessao = MagicMock()
        sessao.access_token = access_token
        sessao.refresh_token = refresh_token
        sessao.expires_in = 3600

    usuario = None
    if not user_none:
        usuario = MagicMock()
        usuario.id = uid
        usuario.email = email

    auth_resp = MagicMock()
    auth_resp.session = sessao
    auth_resp.user = usuario

    fake_auth = MagicMock()
    if raise_exc:
        fake_auth.sign_in_with_password.side_effect = raise_exc
    else:
        fake_auth.sign_in_with_password.return_value = auth_resp

    fake_sb = MagicMock()
    fake_sb.auth = fake_auth
    return fake_sb, fake_auth


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

def test_login_credenciais_validas(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "fake-key")

    fake_sb, fake_auth = _fake_supabase()
    monkeypatch.setattr(auth_mod, "_criar_cliente_supabase", lambda url, key: fake_sb)

    resultado = login(LoginPayload(email="hugo@geoadmin.com", senha="senhaforte"))

    assert resultado.access_token == "jwt.abc.123"
    assert resultado.refresh_token == "ref.xyz"
    assert resultado.token_type == "bearer"
    assert resultado.user_id == "user-uuid-001"
    assert resultado.email == "hugo@geoadmin.com"
    fake_auth.sign_in_with_password.assert_called_once_with(
        {"email": "hugo@geoadmin.com", "password": "senhaforte"}
    )


def test_login_credenciais_invalidas_session_none(monkeypatch):
    """session=None → HTTPException 401."""
    monkeypatch.setenv("SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "fake-key")

    fake_sb, _ = _fake_supabase(session_none=True, user_none=True)
    monkeypatch.setattr(auth_mod, "_criar_cliente_supabase", lambda url, key: fake_sb)

    with pytest.raises(HTTPException) as exc_info:
        login(LoginPayload(email="x@x.com", senha="errado"))

    assert exc_info.value.status_code == 401
    assert "inválidos" in exc_info.value.detail["erro"]


def test_login_supabase_lanca_excecao(monkeypatch):
    """Exceção genérica do Supabase → HTTPException 401."""
    monkeypatch.setenv("SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "fake-key")

    fake_sb, _ = _fake_supabase(raise_exc=Exception("AuthApiError: Invalid login credentials"))
    monkeypatch.setattr(auth_mod, "_criar_cliente_supabase", lambda url, key: fake_sb)

    with pytest.raises(HTTPException) as exc_info:
        login(LoginPayload(email="x@x.com", senha="errado"))

    assert exc_info.value.status_code == 401


def test_login_sem_supabase_configurado(monkeypatch):
    """Sem URL/KEY → HTTPException 500."""
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_KEY", "")

    with pytest.raises(HTTPException) as exc_info:
        login(LoginPayload(email="x@x.com", senha="abc"))

    assert exc_info.value.status_code == 500
    assert "não configurado" in exc_info.value.detail["erro"]


def test_login_retorna_expires_in(monkeypatch):
    """expires_in deve estar presente no retorno."""
    monkeypatch.setenv("SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "fake-key")

    fake_sb, _ = _fake_supabase()
    monkeypatch.setattr(auth_mod, "_criar_cliente_supabase", lambda url, key: fake_sb)

    resultado = login(LoginPayload(email="a@b.com", senha="123456"))
    assert resultado.expires_in == 3600


def test_logout_retorna_ok():
    """logout() deve retornar {"ok": True} sem precisar de Supabase."""
    resultado = logout()
    assert resultado == {"ok": True}
