import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from main import app
from core.database import get_supabase_admin

client = TestClient(app)

def test_auth_invalido_retorna_401():
    response = client.get(
        "/admin/master/resumo",
        headers={"Authorization": "Bearer TOKEN_INVALIDO_XYZ"}
    )
    assert response.status_code == 401

def test_acesso_resumo_sem_token_com_auth_obrigatorio_retorna_401():
    response = client.get("/admin/master/resumo")
    assert response.status_code == 401

# No staging real, para termos um token válido, precisaríamos de uma credencial
# ou criaríamos um usuário em tempo real usando service_role.
# Para evitar vazar senhas em código de teste, vamos fazer um teste usando a API real.

def test_auth_valido_com_projeto_retorna_200():
    # Cria usuario via admin api
    sb_admin = get_supabase_admin()
    
    # Geramos um email randomico para o teste
    import uuid
    uid = str(uuid.uuid4())
    test_email = f"test_{uid}@geoadmin.local"
    test_password = "Password123!"
    
    # Signup
    user_res = sb_admin.auth.admin.create_user({
        "email": test_email,
        "password": test_password,
        "email_confirm": True
    })
    
    user_id = user_res.user.id
    
    try:
        # Sign-in para pegar token real
        login_res = sb_admin.auth.sign_in_with_password({"email": test_email, "password": test_password})
        token = login_res.session.access_token
        
        # Cria projeto
        proj_res = sb_admin.table("projetos").insert({
            "nome": f"Projeto Teste Isolation {uid}",
            "municipio": "São Paulo",
            "uf": "SP",
            "owner_id": user_id
        }).execute()
        projeto_id = proj_res.data[0]["id"]
        
        # Rota resumo com esse token DEVE retornar apenas os dados desse user
        resp = client.get("/admin/master/resumo", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "total_projetos" in data
        assert data["total_projetos"] == 1 # Apenas o projeto que acabei de criar! Prova de isolamento RLS
        
        # Lista projetos
        resp_proj = client.get("/admin/master/projetos", headers={"Authorization": f"Bearer {token}"})
        assert resp_proj.status_code == 200
        projs = resp_proj.json()
        assert len(projs) == 1
        assert projs[0]["id"] == projeto_id
        
    finally:
        # Limpeza
        try:
            sb_admin.auth.admin.delete_user(user_id)
        except Exception as e:
            print(f"Aviso: Nao foi possivel deletar o usuario de teste {user_id}: {e}")
        # Cascade delete cuidará do projeto
