from __future__ import annotations

import integracoes.gerador_documentos as docs_mod


def _dados_base() -> docs_mod.DadosDocumento:
    return docs_mod.DadosDocumento(
        projeto_id='proj-1',
        projeto_nome='Projeto Boa Vista',
        nome_imovel='Fazenda Boa Vista',
        municipio='Morrinhos',
        estado='GO',
        endereco_imovel='Estrada da Serrinha',
        endereco_imovel_numero='Km 12',
        cep_imovel='75650-000',
        comarca='Morrinhos',
        matricula='12345',
        area_ha=12.3456,
        area_m2=123456.0,
        cliente_nome='Hugo Henrique',
        cliente_cpf='123.456.789-01',
        cliente_rg='1234567',
        estado_civil='solteiro',
        profissao='Topografo',
        telefone='62999999999',
        email='hugo@example.com',
        endereco='Rua das Flores',
        endereco_numero='321',
        cliente_municipio='Goiania',
        cliente_estado='GO',
        cep='74000-000',
    )


def test_preencher_distingue_endereco_residencial_do_imovel():
    dados = _dados_base()

    texto = docs_mod._preencher(docs_mod.TEMPLATE_DECL_RESIDENCIA, dados)

    assert 'resido e domicilio em Rua das Flores, N° 321 | Goiania - GO | CEP 74000-000' in texto
    assert 'fica localizado em Estrada da Serrinha, N° Km 12 | Morrinhos - GO | CEP 75650-000' in texto
    assert 'resido e domicilio na Fazenda' not in texto


def test_preencher_requerimento_mostra_duas_referencias_distintas():
    dados = _dados_base()

    texto = docs_mod._preencher(docs_mod.TEMPLATE_REQ_TITULACAO, dados)

    assert 'Endereço residencial: Rua das Flores, N° 321 | Goiania - GO | CEP 74000-000' in texto
    assert 'Localização do Imóvel: Estrada da Serrinha, N° Km 12 | Morrinhos - GO | CEP 75650-000' in texto
