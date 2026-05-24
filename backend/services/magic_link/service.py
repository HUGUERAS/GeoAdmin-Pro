"""
Serviço centralizado para gerenciamento de Magic Link.

Este módulo consolida toda a lógica de geração, validação e rastreamento
de Magic Links, separando as regras de negócio dos endpoints HTTP.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Constantes de validação
PAPEIS_VALIDOS = {
    'principal',
    'coproprietario',
    'possuidor',
    'herdeiro',
    'representante',
    'outro',
}

EVENTOS_MAGIC_LINK_VALIDOS = {'gerado', 'reenviado', 'revogado', 'consumido', 'legado'}
CANAIS_MAGIC_LINK_VALIDOS = {'whatsapp', 'email', 'sms', 'manual', 'interno'}


class MagicLinkService:
    """
    Serviço responsável por todas as operações relacionadas a Magic Links.
    
    Responsabilidades:
    - Gerar tokens únicos com expiração configurável
    - Validar tokens e verificar expiração
    - Registrar eventos de auditoria
    - Integrar com participantes de projetos e clientes
    - Gerar URLs e mensagens padronizadas
    """

    def __init__(self, supabase_client):
        """
        Inicializa o serviço com cliente Supabase.
        
        Args:
            supabase_client: Instância do cliente Supabase
        """
        self.sb = supabase_client

    # =========================================================================
    # Métodos utilitários internos
    # =========================================================================

    @staticmethod
    def _normalizar_documento(valor: str | None) -> str:
        """Remove caracteres não numéricos de documentos."""
        return ''.join(ch for ch in str(valor or '') if ch.isdigit())

    @staticmethod
    def _normalizar_papel(valor: str | None) -> str:
        """Normaliza papel do participante para valores válidos."""
        papel = (valor or 'outro').strip().lower()
        return papel if papel in PAPEIS_VALIDOS else 'outro'

    @staticmethod
    def _normalizar_tipo_evento(valor: str | None) -> str:
        """Normaliza tipo de evento para valores válidos."""
        chave = (valor or 'gerado').strip().lower()
        return chave if chave in EVENTOS_MAGIC_LINK_VALIDOS else 'gerado'

    @staticmethod
    def _normalizar_canal(valor: str | None) -> str:
        """Normaliza canal de envio para valores válidos."""
        chave = (valor or 'whatsapp').strip().lower()
        return chave if chave in CANAIS_MAGIC_LINK_VALIDOS else 'whatsapp'

    @staticmethod
    def _dados(resposta: Any) -> list[dict[str, Any]]:
        """Extrai lista de dados de resposta Supabase."""
        return getattr(resposta, 'data', None) or []

    def _erro_schema(self, exc: Exception, trecho: str) -> bool:
        """Verifica se erro está relacionado a schema específico."""
        return trecho.lower() in str(exc).lower()

    # =========================================================================
    # Geração de Magic Link
    # =========================================================================

    def gerar_token(
        self,
        projeto_id: str,
        cliente_id: str | None = None,
        projeto_cliente_id: str | None = None,
        dias: int = 7,
        canal: str = "whatsapp",
        autor: str | None = None,
    ) -> dict[str, Any]:
        """
        Gera um novo Magic Link para um participante ou cliente.

        Args:
            projeto_id: ID do projeto
            cliente_id: ID do cliente (opcional, usado em fluxo legado)
            projeto_cliente_id: ID do vínculo projeto-cliente (opcional)
            dias: Dias até expiração do token
            canal: Canal de envio (whatsapp, email, sms, etc.)
            autor: Identificação de quem gerou o link

        Returns:
            Dicionário com informações do link gerado:
            - link: URL completa de acesso
            - expira_em: Data/hora formatada da expiração
            - cliente_nome: Nome do cliente destinatário
            - cliente_id: ID do cliente
            - projeto_cliente_id: ID do vínculo (se aplicável)
            - papel: Papel do participante
            - area_id: ID da área vinculada (se aplicável)
            - projeto_nome: Nome do projeto
            - mensagem_whatsapp: Mensagem pronta para envio

        Raises:
            HTTPException: Se projeto não encontrado ou participante inválido
        """
        from fastapi import HTTPException

        # Buscar informações do projeto
        try:
            res = self.sb.table("vw_projetos_completo").select(
                "id, projeto_nome, cliente_id, cliente_nome"
            ).eq("id", projeto_id).single().execute()
        except Exception:
            raise HTTPException(404, {"erro": "[ERRO-401] Projeto não encontrado.", "codigo": 401})

        projeto = res.data
        
        # Determinar se usa fluxo de participantes ou legado
        participantes = self._listar_participantes(projeto_id)
        participante_base = self._participante_base(
            participantes,
            projeto_cliente_id=projeto_cliente_id,
            cliente_id=cliente_id
        )
        usa_fluxo_participante = bool(participante_base) or bool(participantes) or bool(projeto_cliente_id)

        # Gerar token no fluxo apropriado
        participante = None
        token: str | None = None
        expira = datetime.now(timezone.utc) + timedelta(days=max(dias, 1))
        cliente_destino_id = cliente_id or projeto.get("cliente_id")
        cliente_nome = projeto.get("cliente_nome")
        tipo_evento = "gerado"

        if usa_fluxo_participante:
            participante = self.gerar_magic_link_participante(
                projeto_id,
                projeto_cliente_id=projeto_cliente_id,
                cliente_id=cliente_id,
                dias=dias,
            )
            if not participante:
                raise HTTPException(
                    422,
                    {"erro": "[ERRO-102] Nenhum participante elegível foi encontrado para gerar o link.", "codigo": 102}
                )
            token = participante.get("magic_link_token")
            cliente_destino_id = participante.get("cliente_id") or cliente_destino_id
            cliente_nome = participante.get("nome") or cliente_nome
            tipo_evento = "reenviado" if (participante_base or {}).get("magic_link_token") else "gerado"
            if participante.get("magic_link_expira"):
                expira = datetime.fromisoformat(
                    str(participante["magic_link_expira"]).replace("Z", "+00:00")
                )
        else:
            # Fluxo legado
            if not cliente_destino_id:
                raise HTTPException(422, {"erro": "[ERRO-102] Projeto sem cliente vinculado.", "codigo": 102})
            token = str(uuid.uuid4())
            expira = datetime.now(timezone.utc) + timedelta(days=7)
            self.sb.table("clientes").update({
                "magic_link_token": token,
                "magic_link_expira": expira.isoformat(),
            }).eq("id", cliente_destino_id).execute()
            tipo_evento = "legado"

        # Atualizar nome do cliente se necessário
        if cliente_destino_id:
            cliente_info = (
                self.sb.table("clientes")
                .select("id, nome")
                .eq("id", cliente_destino_id)
                .maybe_single()
                .execute()
                .data
            )
            if cliente_info:
                cliente_nome = cliente_info.get("nome") or cliente_nome

        # Construir URL e registrar evento
        base_url = self._resolver_app_url()
        link = f"{base_url}/formulario/cliente?token={token}"
        area_id = participante.get("area_id") if participante else None
        
        self.registrar_evento(
            projeto_id=projeto_id,
            projeto_cliente_id=participante.get("id") if participante else projeto_cliente_id,
            cliente_id=cliente_destino_id,
            area_id=area_id,
            token=token,
            tipo_evento=tipo_evento,
            canal=canal,
            autor=autor or "sistema",
            expira_em=expira.isoformat(),
            payload={"link": link, "modo": "participante" if participante else "legado"},
        )

        logger.info("Magic Link gerado para projeto '%s'", projeto["projeto_nome"])

        return {
            "link": link,
            "expira_em": expira.strftime("%d/%m/%Y às %H:%M"),
            "cliente_nome": cliente_nome,
            "cliente_id": cliente_destino_id,
            "projeto_cliente_id": participante.get("id") if participante else projeto_cliente_id,
            "papel": participante.get("papel") if participante else "principal",
            "area_id": area_id,
            "projeto_nome": projeto.get("projeto_nome"),
            "mensagem_whatsapp": (
                f"Olá {cliente_nome or ''}!\n\n"
                f"Para darmos andamento ao processo de regularização do imóvel *{projeto.get('projeto_nome', '')}*, "
                "preciso que você preencha um formulário com seus dados e um esboço simples da área.\n\n"
                f"Acesse pelo celular: {link}\n\n"
                "O link expira em 7 dias.\n\n"
                "Qualquer dúvida é só chamar!"
            ),
        }

    def gerar_magic_link_participante(
        self,
        projeto_id: str,
        *,
        projeto_cliente_id: str | None = None,
        cliente_id: str | None = None,
        dias: int = 7,
    ) -> dict[str, Any] | None:
        """
        Gera token Magic Link para um participante específico do projeto.

        Args:
            projeto_id: ID do projeto
            projeto_cliente_id: ID do vínculo projeto-cliente
            cliente_id: ID do cliente
            dias: Dias até expiração

        Returns:
            Dados do participante com token gerado, ou None se não encontrado
        """
        participante = self._obter_participante_base(
            projeto_id,
            projeto_cliente_id=projeto_cliente_id,
            cliente_id=cliente_id
        )
        if not participante:
            return None

        token = str(uuid.uuid4())
        expira = datetime.now(timezone.utc) + timedelta(days=dias)
        
        if participante.get('id'):
            try:
                (
                    self.sb.table('projeto_clientes')
                    .update({'magic_link_token': token, 'magic_link_expira': expira.isoformat()})
                    .eq('id', participante['id'])
                    .execute()
                )
            except Exception:
                pass

        participante['magic_link_token'] = token
        participante['magic_link_expira'] = expira.isoformat()
        return participante

    # =========================================================================
    # Validação de Token
    # =========================================================================

    def validar_token(self, token: str) -> tuple[dict[str, Any], str | None, dict[str, Any] | None]:
        """
        Valida um token Magic Link e retorna contexto associado.

        Args:
            token: Token a ser validado

        Returns:
            Tupla com:
            - Cliente: Dados do cliente associado
            - Projeto ID: ID do projeto vinculado (ou None)
            - Vínculo: Dados do vínculo projeto-cliente (ou None)

        Raises:
            HTTPException: Se token inválido, expirado ou ambíguo
        """
        from fastapi import HTTPException

        vinculo = self.obter_vinculo_por_token(token)
        
        if vinculo:
            # Verificar expiração
            expira = vinculo.get("magic_link_expira")
            if expira and datetime.fromisoformat(str(expira).replace("Z", "+00:00")) < datetime.now(timezone.utc):
                raise HTTPException(401, {"erro": "[ERRO-602] Link expirado. Solicite um novo link.", "codigo": 602})

            # Buscar dados do cliente
            cliente_res = (
                self.sb.table("clientes")
                .select("id, nome, magic_link_expira, magic_link_token, formulario_ok, formulario_em")
                .eq("id", vinculo.get("cliente_id"))
                .maybe_single()
                .execute()
            )
            cliente = cliente_res.data
            
            if not cliente:
                raise HTTPException(404, {"erro": "[ERRO-404] Cliente não encontrado.", "codigo": 404})
            
            return cliente, vinculo.get("projeto_id"), vinculo

        # Tentar fluxo legado (token na tabela clientes)
        cliente_res = (
            self.sb.table("clientes")
            .select("id, nome, magic_link_expira, magic_link_token, formulario_ok, formulario_em")
            .eq("magic_link_token", token)
            .maybe_single()
            .execute()
        )
        cliente = cliente_res.data
        
        if not cliente:
            raise HTTPException(401, {"erro": "[ERRO-601] Link inválido. Verifique o token informado.", "codigo": 601})

        expira = cliente.get("magic_link_expira")
        if expira and datetime.fromisoformat(str(expira).replace("Z", "+00:00")) < datetime.now(timezone.utc):
            raise HTTPException(401, {"erro": "[ERRO-602] Link expirado. Solicite um novo link.", "codigo": 602})

        # Resolver contexto legado
        projeto_id, vinculo = self._resolver_contexto_legacy_cliente(cliente.get("id"))
        
        if projeto_id:
            projeto_id, vinculo = self._garantir_vinculo_legacy_cliente(
                cliente=cliente,
                projeto_id=projeto_id,
                vinculo=vinculo,
                token=token,
            )

        return cliente, projeto_id, vinculo

    # =========================================================================
    # Consulta de Participantes
    # =========================================================================

    def _listar_participantes(self, projeto_id: str, cliente_principal: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Lista participantes de um projeto."""
        try:
            resposta = (
                self.sb.table('projeto_clientes')
                .select('id, projeto_id, cliente_id, papel, principal, recebe_magic_link, ordem, area_id, magic_link_token, magic_link_expira, criado_em, clientes!inner(id, nome, cpf_cnpj, cpf, telefone, email, formulario_ok, formulario_em, deleted_at)')
                .eq('projeto_id', projeto_id)
                .is_('deleted_at', 'null')
                .order('ordem', desc=False)
                .execute()
            )
            itens = self._dados(resposta)
            participantes: list[dict[str, Any]] = []
            for item in itens:
                cliente = item.get('clientes') or {}
                if cliente.get('deleted_at'):
                    continue
                participantes.append({
                    'id': item.get('id'),
                    'projeto_id': item.get('projeto_id'),
                    'cliente_id': item.get('cliente_id') or cliente.get('id'),
                    'papel': item.get('papel') or 'outro',
                    'principal': bool(item.get('principal')),
                    'recebe_magic_link': bool(item.get('recebe_magic_link')),
                    'ordem': item.get('ordem') or 0,
                    'area_id': item.get('area_id'),
                    'magic_link_token': item.get('magic_link_token'),
                    'magic_link_expira': item.get('magic_link_expira'),
                    'nome': cliente.get('nome'),
                    'cpf': cliente.get('cpf') or cliente.get('cpf_cnpj'),
                    'telefone': cliente.get('telefone'),
                    'email': cliente.get('email'),
                    'formulario_ok': bool(cliente.get('formulario_ok')),
                    'formulario_em': cliente.get('formulario_em'),
                })
            if participantes:
                return participantes
        except Exception as exc:
            logger.warning("Falha ao listar participantes do projeto %s: %s", projeto_id, exc)

        if cliente_principal:
            return [{
                'id': None,
                'projeto_id': projeto_id,
                'cliente_id': cliente_principal.get('id'),
                'papel': 'principal',
                'principal': True,
                'recebe_magic_link': True,
                'ordem': 0,
                'area_id': None,
                'magic_link_token': cliente_principal.get('magic_link_token'),
                'magic_link_expira': cliente_principal.get('magic_link_expira'),
                'nome': cliente_principal.get('nome'),
                'cpf': cliente_principal.get('cpf') or cliente_principal.get('cpf_cnpj'),
                'telefone': cliente_principal.get('telefone'),
                'email': cliente_principal.get('email'),
                'formulario_ok': bool(cliente_principal.get('formulario_ok')),
                'formulario_em': cliente_principal.get('formulario_em'),
            }]
        return []

    def _participante_base(
        self,
        participantes: list[dict[str, Any]],
        *,
        projeto_cliente_id: str | None = None,
        cliente_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Retorna participante base baseado em critérios de busca."""
        if projeto_cliente_id:
            return next((item for item in participantes if str(item.get('id')) == str(projeto_cliente_id)), None)
        if cliente_id:
            return next((item for item in participantes if str(item.get('cliente_id')) == str(cliente_id)), None)
        return next((item for item in participantes if item.get('principal')), None) or \
               next((item for item in participantes if item.get('recebe_magic_link')), None) or \
               (participantes[0] if participantes else None)

    def _obter_participante_base(
        self,
        projeto_id: str,
        projeto_cliente_id: str | None = None,
        cliente_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Obtém participante base para um projeto."""
        participantes = self._listar_participantes(projeto_id)
        return self._participante_base(
            participantes,
            projeto_cliente_id=projeto_cliente_id,
            cliente_id=cliente_id
        )

    # =========================================================================
    # Registro de Eventos
    # =========================================================================

    def registrar_evento(
        self,
        *,
        projeto_id: str,
        projeto_cliente_id: str | None,
        cliente_id: str | None,
        area_id: str | None,
        token: str | None,
        tipo_evento: str,
        canal: str = 'whatsapp',
        autor: str | None = None,
        expira_em: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Registra evento de auditoria do Magic Link.

        Args:
            projeto_id: ID do projeto
            projeto_cliente_id: ID do vínculo projeto-cliente
            cliente_id: ID do cliente
            area_id: ID da área (se aplicável)
            token: Token do Magic Link
            tipo_evento: Tipo do evento (gerado, reenviado, consumido, etc.)
            canal: Canal de envio
            autor: Identificação do autor
            expira_em: Data de expiração ISO
            payload: Dados adicionais do evento

        Returns:
            Registro do evento criado
        """
        registro = {
            'projeto_id': projeto_id,
            'projeto_cliente_id': projeto_cliente_id,
            'cliente_id': cliente_id,
            'area_id': area_id,
            'token': token,
            'tipo_evento': self._normalizar_tipo_evento(tipo_evento),
            'canal': self._normalizar_canal(canal),
            'autor': autor,
            'expira_em': expira_em,
            'payload_json': payload or {},
            'deleted_at': None,
        }
        try:
            resposta = self.sb.table('eventos_magic_link').insert(registro).execute()
            dados = self._dados(resposta)
            return dados[0] if dados else registro
        except Exception as exc:
            if 'eventos_magic_link' in str(exc).lower():
                return registro
            raise

    def listar_eventos(
        self,
        projeto_id: str,
        *,
        projeto_cliente_id: str | None = None,
        area_id: str | None = None,
        limite: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Lista eventos de Magic Link de um projeto.

        Args:
            projeto_id: ID do projeto
            projeto_cliente_id: Filtrar por vínculo específico (opcional)
            area_id: Filtrar por área específica (opcional)
            limite: Número máximo de eventos a retornar

        Returns:
            Lista de eventos ordenados por data decrescente
        """
        try:
            consulta = (
                self.sb.table('eventos_magic_link')
                .select('*')
                .eq('projeto_id', projeto_id)
                .is_('deleted_at', 'null')
                .order('criado_em', desc=True)
                .limit(limite)
            )
            if projeto_cliente_id:
                consulta = consulta.eq('projeto_cliente_id', projeto_cliente_id)
            if area_id:
                consulta = consulta.eq('area_id', area_id)
            resposta = consulta.execute()
            return self._dados(resposta)
        except Exception as exc:
            if 'eventos_magic_link' in str(exc).lower():
                return []
            raise

    # =========================================================================
    # Utilitários auxiliares
    # =========================================================================

    def obter_vinculo_por_token(self, token: str) -> dict[str, Any] | None:
        """Busca vínculo projeto-cliente por token."""
        try:
            resposta = (
                self.sb.table('projeto_clientes')
                .select('id, projeto_id, cliente_id, papel, principal, recebe_magic_link, ordem, area_id, magic_link_token, magic_link_expira')
                .eq('magic_link_token', token)
                .is_('deleted_at', 'null')
                .limit(1)
                .execute()
            )
        except Exception as exc:
            if 'projeto_clientes' in str(exc).lower():
                return None
            raise
        dados = self._dados(resposta)
        return dados[0] if dados else None

    def _resolver_contexto_legacy_cliente(self, cliente_id: str) -> tuple[str | None, dict[str, Any] | None]:
        """
        Resolve contexto para cliente em fluxo legado.
        
        Returns:
            Tupla com (projeto_id, vínculo)
        """
        from fastapi import HTTPException

        try:
            resposta_vinculos = (
                self.sb.table("projeto_clientes")
                .select("id, projeto_id, cliente_id, papel, principal, recebe_magic_link, ordem, area_id, magic_link_token, magic_link_expira")
                .eq("cliente_id", cliente_id)
                .is_("deleted_at", "null")
                .execute()
            )
            vinculos = self._dados(resposta_vinculos)
        except Exception as exc:
            if "projeto_clientes" in str(exc).lower():
                vinculos = []
            else:
                raise

        if len(vinculos) == 1:
            vinculo = vinculos[0]
            return vinculo.get("projeto_id"), vinculo
        if len(vinculos) > 1:
            raise HTTPException(409, {
                "erro": "[ERRO-603] Este link antigo ficou ambíguo porque o cliente participa de mais de um projeto. Solicite um novo link individual.",
                "codigo": 603,
            })

        projeto_res = (
            self.sb.table("projetos")
            .select("id")
            .eq("cliente_id", cliente_id)
            .is_("deleted_at", "null")
            .order("criado_em", desc=True)
            .execute()
        )
        projetos = self._dados(projeto_res)
        if len(projetos) == 1:
            return projetos[0].get("id"), None
        if len(projetos) > 1:
            raise HTTPException(409, {
                "erro": "[ERRO-603] Este link antigo ficou ambíguo porque o cliente tem mais de um projeto ativo. Solicite um novo link individual.",
                "codigo": 603,
            })
        return None, None

    def _garantir_vinculo_legacy_cliente(
        self,
        *,
        cliente: dict[str, Any],
        projeto_id: str | None,
        vinculo: dict[str, Any] | None,
        token: str,
    ) -> tuple[str | None, dict[str, Any] | None]:
        """Garante existência de vínculo para cliente legado."""
        from fastapi import HTTPException
        from integracoes.projeto_clientes import salvar_participantes_projeto

        if not projeto_id:
            return None, None

        if not vinculo:
            participantes = salvar_participantes_projeto(
                self.sb,
                projeto_id,
                [{
                    "cliente_id": cliente.get("id"),
                    "nome": cliente.get("nome"),
                    "cpf": cliente.get("cpf") or cliente.get("cpf_cnpj"),
                    "telefone": cliente.get("telefone"),
                    "email": cliente.get("email"),
                    "papel": "principal",
                    "principal": True,
                    "recebe_magic_link": True,
                    "ordem": 0,
                    "area_id": None,
                }],
            )
            vinculo = next((item for item in participantes if str(item.get("cliente_id")) == str(cliente.get("id"))), None)

        if not vinculo or not vinculo.get("id"):
            raise HTTPException(409, {
                "erro": "[ERRO-603] Este link antigo precisa ser substituído por um novo link individual.",
                "codigo": 603,
            })

        expira = cliente.get("magic_link_expira")
        (
            self.sb.table("projeto_clientes")
            .update({
                "magic_link_token": token,
                "magic_link_expira": expira,
            })
            .eq("id", vinculo.get("id"))
            .execute()
        )
        (
            self.sb.table("clientes")
            .update({
                "magic_link_token": None,
                "magic_link_expira": None,
            })
            .eq("id", cliente.get("id"))
            .execute()
        )
        self.registrar_evento(
            projeto_id=projeto_id,
            projeto_cliente_id=vinculo.get("id"),
            cliente_id=cliente.get("id"),
            area_id=vinculo.get("area_id"),
            token=token,
            tipo_evento="legado",
            canal="interno",
            autor="migracao_legacy",
            expira_em=expira,
            payload={"migrado_de_cliente": True},
        )

        vinculo["magic_link_token"] = token
        vinculo["magic_link_expira"] = expira
        return projeto_id, vinculo

    @staticmethod
    def _resolver_app_url() -> str:
        """Resolve URL base da aplicação a partir de variáveis de ambiente."""
        import os
        
        for chave in ("APP_URL", "PUBLIC_APP_URL", "PUBLIC_BASE_URL"):
            valor = (os.environ.get(chave) or "").strip()
            if valor:
                return valor.rstrip("/")

        railway = (os.environ.get("RAILWAY_PUBLIC_DOMAIN") or "").strip()
        if railway:
            return f"https://{railway.lstrip('/')}".rstrip("/")

        vercel = (os.environ.get("VERCEL_URL") or "").strip()
        if vercel:
            return f"https://{vercel.lstrip('/')}".rstrip("/")

        return "http://127.0.0.1:8000"
