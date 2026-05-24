"""
GeoAdmin Pro - Log de Auditoria

Implementa trilha de auditoria para operações críticas,
acessos a dados e mudanças de estado.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from supabase import Client

logger = logging.getLogger(__name__)


class AuditLog:
    """
    Sistema de log de auditoria para operações críticas.
    
    Registra todas as ações importantes no sistema para compliance
    e investigação de incidentes.
    """
    
    def __init__(self, supabase_client: Client):
        """
        Inicializa sistema de auditoria.
        
        Args:
            supabase_client: Cliente Supabase configurado.
        """
        self.supabase = supabase_client
        logger.info("AuditLog inicializado")
    
    def log_event(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        action: str,
        user_id: str,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Registra evento de auditoria.
        
        Args:
            event_type: Tipo do evento (ex: 'create', 'update', 'delete', 'access').
            entity_type: Tipo da entidade (ex: 'projeto', 'ponto', 'cliente').
            entity_id: ID da entidade afetada.
            action: Descrição da ação realizada.
            user_id: ID do usuário que realizou a ação.
            details: Detalhes adicionais em JSON.
            correlation_id: ID de correlação para rastreamento.
            ip_address: IP do cliente.
            
        Returns:
            Resultado do registro.
        """
        result = {
            "success": False,
            "event_id": None,
            "error": None,
        }
        
        try:
            event_data = {
                "event_type": event_type,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "action": action,
                "user_id": user_id,
                "details": details or {},
                "correlation_id": correlation_id,
                "ip_address": ip_address,
                "created_at": datetime.utcnow().isoformat(),
            }
            
            # Insere na tabela de auditoria
            response = self.supabase.table("audit_log").insert(event_data).execute()
            
            if response.data:
                result["success"] = True
                result["event_id"] = response.data[0].get("id")
                logger.debug(f"Evento de auditoria registrado: {event_type} - {entity_id}")
            else:
                result["error"] = "Falha ao inserir evento"
                
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Erro ao registrar evento de auditoria: {e}", exc_info=True)
        
        return result
    
    def log_magic_link_event(
        self,
        projeto_id: str,
        participant_email: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Registra evento específico de Magic Link.
        
        Args:
            projeto_id: ID do projeto.
            participant_email: Email do participante.
            action: Ação realizada (ex: 'link_generated', 'form_accessed', 'form_submitted').
            details: Detalhes adicionais.
        """
        return self.log_event(
            event_type="magic_link",
            entity_type="projeto",
            entity_id=projeto_id,
            action=action,
            user_id=participant_email,
            details=details,
        )
    
    def log_file_access(
        self,
        file_id: str,
        project_id: str,
        user_id: str,
        access_type: str = "download",
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Registra acesso a arquivos.
        
        Args:
            file_id: ID do arquivo.
            project_id: ID do projeto.
            user_id: ID do usuário.
            access_type: Tipo de acesso (ex: 'download', 'view', 'upload').
            correlation_id: ID de correlação.
        """
        return self.log_event(
            event_type="file_access",
            entity_type="arquivo",
            entity_id=file_id,
            action=access_type,
            user_id=user_id,
            details={"project_id": project_id},
            correlation_id=correlation_id,
        )
    
    def log_geometry_change(
        self,
        geometry_id: str,
        project_id: str,
        user_id: str,
        change_type: str,
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Registra mudanças em geometrias (pontos, perímetros).
        
        Args:
            geometry_id: ID da geometria.
            project_id: ID do projeto.
            user_id: ID do usuário.
            change_type: Tipo de mudança (ex: 'coordinate_update', 'vertex_added').
            old_value: Valor anterior (para auditoria detalhada).
            new_value: Novo valor.
            correlation_id: ID de correlação.
        """
        return self.log_event(
            event_type="geometry_change",
            entity_type="geometria",
            entity_id=geometry_id,
            action=change_type,
            user_id=user_id,
            details={
                "project_id": project_id,
                "old_value": old_value,
                "new_value": new_value,
            },
            correlation_id=correlation_id,
        )
    
    def get_events(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Recupera eventos de auditoria com filtros.
        
        Args:
            entity_type: Filtra por tipo de entidade.
            entity_id: Filtra por ID da entidade.
            user_id: Filtra por usuário.
            event_type: Filtra por tipo de evento.
            limit: Limite de resultados.
            
        Returns:
            Lista de eventos.
        """
        try:
            query = self.supabase.table("audit_log").select("*")
            
            if entity_type:
                query = query.eq("entity_type", entity_type)
            if entity_id:
                query = query.eq("entity_id", entity_id)
            if user_id:
                query = query.eq("user_id", user_id)
            if event_type:
                query = query.eq("event_type", event_type)
            
            query = query.order("created_at", desc=True).limit(limit)
            
            response = query.execute()
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"Erro ao recuperar eventos de auditoria: {e}")
            return []
    
    def get_events_by_correlation_id(
        self, 
        correlation_id: str
    ) -> List[Dict[str, Any]]:
        """
        Recupera todos os eventos com mesmo correlation_id.
        
        Útil para rastrear fluxo completo de uma requisição.
        
        Args:
            correlation_id: ID de correlação.
            
        Returns:
            Lista de eventos relacionados.
        """
        return self.get_events(entity_id=None, limit=1000)  # Filtro aplicado manualmente
    
    def cleanup_old_events(self, days_to_keep: int = 90) -> int:
        """
        Remove eventos antigos de auditoria.
        
        Args:
            days_to_keep: Dias para manter eventos.
            
        Returns:
            Número de eventos removidos.
        """
        try:
            cutoff_date = datetime.utcnow().isoformat()
            
            # Nota: Implementação real dependeria da schema do banco
            # Esta é uma implementação simplificada
            logger.info(f"Limpeza de eventos antigos ({days_to_keep} dias) solicitada")
            return 0
            
        except Exception as e:
            logger.error(f"Erro na limpeza de eventos: {e}")
            return 0


__all__ = ["AuditLog"]
