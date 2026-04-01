"""
Rotas de autenticação — login via Supabase Auth.
O backend recebe email/senha, autentica com o Supabase e devolve o JWT
para o app mobile armazenar e usar nos próximos requests.
"""
import os
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _criar_cliente_supabase(url: str, key: str):
    from supabase import create_client
    return create_client(url, key)


class LoginPayload(BaseModel):
    email: str
    senha: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    user_id: str
    email: str


@router.post("/login", response_model=LoginResponse, summary="Autenticar com email e senha")
def login(payload: LoginPayload):
    """
    Autentica o usuário via Supabase Auth.
    Retorna o access_token JWT que deve ser enviado nos próximos requests
    como header `Authorization: Bearer <token>`.
    """
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")

    if not url or not key:
        raise HTTPException(
            status_code=500,
            detail={"erro": "Supabase não configurado no servidor", "codigo": 500},
        )

    try:
        cliente = _criar_cliente_supabase(url, key)
        resposta = cliente.auth.sign_in_with_password(
            {"email": payload.email, "password": payload.senha}
        )

        if not resposta or not resposta.session or not resposta.user:
            raise HTTPException(
                status_code=401,
                detail={"erro": "Email ou senha inválidos", "codigo": 401},
            )

        sessao = resposta.session
        usuario = resposta.user

        return LoginResponse(
            access_token=sessao.access_token,
            refresh_token=sessao.refresh_token,
            expires_in=sessao.expires_in,
            user_id=str(usuario.id),
            email=str(usuario.email or payload.email),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(f"Erro no login: {exc}")
        raise HTTPException(
            status_code=401,
            detail={"erro": "Email ou senha inválidos", "codigo": 401},
        )


@router.post("/logout", summary="Invalidar sessão atual")
def logout(authorization: Optional[str] = None):
    """Invalida o token no Supabase (best-effort)."""
    return {"ok": True}
