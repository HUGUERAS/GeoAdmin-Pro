from __future__ import annotations

import integracoes.projeto_clientes as projeto_clientes_mod


def test_normalizar_participantes_respeita_magic_link_e_um_principal():
    participantes = projeto_clientes_mod.normalizar_participantes_entrada([
        {
            'nome': 'Cliente Principal',
            'cpf': '123.456.789-01',
            'papel': 'principal',
            'principal': True,
            'gerar_magic_link': False,
        },
        {
            'nome': 'Coproprietario',
            'cpf': '987.654.321-00',
            'papel': 'coproprietario',
            'principal': True,
            'gerar_magic_link': True,
        },
    ])

    assert len(participantes) == 2
    assert participantes[0]['principal'] is True
    assert participantes[1]['principal'] is False
    assert participantes[0]['papel'] == 'principal'
    assert participantes[0]['recebe_magic_link'] is False
    assert participantes[1]['recebe_magic_link'] is True
    assert participantes[0]['cpf'] == '12345678901'
