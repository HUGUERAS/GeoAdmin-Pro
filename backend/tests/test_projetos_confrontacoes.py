from routes import projetos as projetos_mod


def test_resumo_confrontacoes_conta_status_e_areas():
    assert hasattr(projetos_mod, "_resumo_confrontacoes")

    confrontacoes = [
        {"area_id": "area-1", "status_revisao": "pendente"},
        {"area_id": "area-1", "status_revisao": "confirmada"},
        {"area_id": "area-2", "status": "descartada"},
        {"area_id": None},
    ]
    confrontantes = [{"id": "conf-1"}, {"id": "conf-2"}]

    resumo = projetos_mod._resumo_confrontacoes(confrontacoes, confrontantes)

    assert resumo == {
        "total": 4,
        "confrontantes_total": 2,
        "areas_com_confrontacao": 2,
        "pendentes": 2,
        "confirmadas": 1,
        "descartadas": 1,
        "por_status": {
            "confirmada": 1,
            "descartada": 1,
            "pendente": 2,
        },
    }


def test_prontidao_piloto_resume_requisitos_minimos():
    assert hasattr(projetos_mod, "_prontidao_piloto")

    projeto = {
        "id": "projeto-1",
        "cliente_id": "cliente-1",
        "clientes": [{"id": "cliente-1"}],
        "participantes": [{"cliente_id": "cliente-1"}],
        "perimetro_ativo": {"id": "perimetro-1"},
        "formulario": {"formulario_ok": True},
    }

    resumo = projetos_mod._prontidao_piloto(projeto)

    assert resumo == {
        "status": "pronto",
        "pronto": True,
        "pendencias": [],
        "requisitos": {
            "projeto_cadastrado": True,
            "cliente_vinculado": True,
            "participantes_mapeados": True,
            "perimetro_definido": True,
            "formulario_cliente": True,
        },
    }
