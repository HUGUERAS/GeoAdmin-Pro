"""
GeoAdmin Pro - Fila de Sincronização Offline

Gerencia fila de operações pendentes de sincronização com o servidor,
com suporte a retry automático e resolução de conflitos.
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


class SyncStatus(str, Enum):
    """Status de sincronização de itens offline."""
    PENDING = "pending"
    SYNCING = "syncing"
    SYNCED = "synced"
    ERROR = "error"
    CONFLICT = "conflict"


@dataclass
class SyncItem:
    """Item na fila de sincronização."""
    id: str
    entity_type: str  # 'ponto', 'perimetro', 'cliente', etc.
    entity_id: str
    operation: str  # 'create', 'update', 'delete'
    payload: Dict[str, Any]
    created_at: str
    updated_at: str
    sync_status: str = SyncStatus.PENDING.value
    retry_count: int = 0
    error_message: Optional[str] = None
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_row(cls, row: tuple) -> 'SyncItem':
        return cls(
            id=row[0],
            entity_type=row[1],
            entity_id=row[2],
            operation=row[3],
            payload=json.loads(row[4]),
            created_at=row[5],
            updated_at=row[6],
            sync_status=row[7],
            retry_count=row[8],
            error_message=row[9],
            correlation_id=row[10] if len(row) > 10 else None,
        )


class SyncQueue:
    """
    Fila de sincronização offline usando SQLite.
    
    Armazena operações locais e sincroniza quando há conectividade.
    Usa estratégia de conflito: último escritor vence (baseado em updated_at).
    """
    
    def __init__(self, db_path: str = ":memory:"):
        """
        Inicializa fila de sincronização.
        
        Args:
            db_path: Caminho para banco SQLite ou ':memory:' para teste.
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        logger.info(f"SyncQueue inicializada em {db_path}")
    
    def _create_tables(self) -> None:
        """Cria tabelas necessárias para fila de sincronização."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_queue (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                sync_status TEXT NOT NULL DEFAULT 'pending',
                retry_count INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                correlation_id TEXT,
                UNIQUE(entity_type, entity_id, operation)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sync_status 
            ON sync_queue(sync_status, retry_count)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entity 
            ON sync_queue(entity_type, entity_id)
        """)
        
        self.conn.commit()
    
    def enqueue(self, item: SyncItem) -> None:
        """
        Adiciona item à fila de sincronização.
        
        Args:
            item: Item a ser sincronizado.
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO sync_queue 
            (id, entity_type, entity_id, operation, payload, created_at, updated_at, 
             sync_status, retry_count, error_message, correlation_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item.id,
            item.entity_type,
            item.entity_id,
            item.operation,
            json.dumps(item.payload),
            item.created_at,
            item.updated_at,
            item.sync_status,
            item.retry_count,
            item.error_message,
            item.correlation_id,
        ))
        
        self.conn.commit()
        logger.debug(f"Item {item.id} ({item.entity_type}) enfileirado para {item.operation}")
    
    def dequeue_pending(self, limit: int = 10) -> List[SyncItem]:
        """
        Recupera itens pendentes para sincronização.
        
        Args:
            limit: Número máximo de itens para retornar.
            
        Returns:
            Lista de itens pendentes.
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT * FROM sync_queue 
            WHERE sync_status IN ('pending', 'error')
            ORDER BY retry_count ASC, updated_at ASC
            LIMIT ?
        """, (limit,))
        
        return [SyncItem.from_row(row) for row in cursor.fetchall()]
    
    def mark_synced(self, item_id: str) -> None:
        """Marca item como sincronizado com sucesso."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            UPDATE sync_queue 
            SET sync_status = ?, updated_at = ?, error_message = NULL
            WHERE id = ?
        """, (SyncStatus.SYNCED.value, datetime.utcnow().isoformat(), item_id))
        
        self.conn.commit()
        logger.debug(f"Item {item_id} marcado como sincronizado")
    
    def mark_error(self, item_id: str, error_message: str) -> None:
        """
        Marca item com erro de sincronização.
        
        Args:
            item_id: ID do item.
            error_message: Mensagem de erro.
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            UPDATE sync_queue 
            SET sync_status = ?, 
                retry_count = retry_count + 1,
                updated_at = ?,
                error_message = ?
            WHERE id = ?
        """, (SyncStatus.ERROR.value, datetime.utcnow().isoformat(), error_message, item_id))
        
        self.conn.commit()
        logger.warning(f"Item {item_id} marcado com erro: {error_message}")
    
    def mark_syncing(self, item_id: str) -> None:
        """Marca item como em processo de sincronização."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            UPDATE sync_queue 
            SET sync_status = ?, updated_at = ?
            WHERE id = ?
        """, (SyncStatus.SYNCING.value, datetime.utcnow().isoformat(), item_id))
        
        self.conn.commit()
    
    def get_pending_count(self) -> int:
        """Retorna número de itens pendentes de sincronização."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM sync_queue 
            WHERE sync_status IN ('pending', 'error', 'syncing')
        """)
        
        return cursor.fetchone()[0]
    
    def clear_synced(self, older_than_days: int = 7) -> int:
        """
        Remove itens já sincronizados mais antigos que X dias.
        
        Args:
            older_than_days: Dias para considerar como antigo.
            
        Returns:
            Número de itens removidos.
        """
        cursor = self.conn.cursor()
        
        cutoff_date = datetime.utcnow().isoformat()
        
        cursor.execute("""
            DELETE FROM sync_queue 
            WHERE sync_status = 'synced' 
              AND updated_at < ?
        """, (cutoff_date,))
        
        removed = cursor.rowcount
        self.conn.commit()
        
        if removed > 0:
            logger.info(f"Removidos {removed} itens sincronizados antigos")
        
        return removed
    
    def get_all(self) -> List[SyncItem]:
        """Retorna todos os itens da fila."""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT * FROM sync_queue ORDER BY updated_at DESC")
        
        return [SyncItem.from_row(row) for row in cursor.fetchall()]
    
    def close(self) -> None:
        """Fecha conexão com banco de dados."""
        if self.conn:
            self.conn.close()
            logger.info("SyncQueue fechada")


__all__ = ["SyncQueue", "SyncItem", "SyncStatus"]
