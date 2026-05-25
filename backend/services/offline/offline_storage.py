"""
GeoAdmin Pro - Armazenamento Offline

Implementa armazenamento local SQLite para dados de projetos,
pontos e perímetros quando offline.
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class OfflineStorage:
    """
    Armazenamento local offline para dados críticos.
    
    Permite operação contínua sem conectividade e sincronização posterior.
    """
    
    def __init__(self, db_path: str = ":memory:"):
        """
        Inicializa armazenamento offline.
        
        Args:
            db_path: Caminho para banco SQLite ou ':memory:' para teste.
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        logger.info(f"OfflineStorage inicializado em {db_path}")
    
    def _create_tables(self) -> None:
        """Cria tabelas para armazenamento offline."""
        cursor = self.conn.cursor()
        
        # Tabela de projetos locais
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projetos_local (
                id TEXT PRIMARY KEY,
                nome TEXT NOT NULL,
                cliente TEXT,
                tipo_processo TEXT,
                perimetro_ativo TEXT,
                dados_completos TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                sync_status TEXT DEFAULT 'pending',
                version INTEGER DEFAULT 1
            )
        """)
        
        # Tabela de pontos locais
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pontos_local (
                id TEXT PRIMARY KEY,
                projeto_id TEXT NOT NULL,
                nome TEXT NOT NULL,
                coordenada_x REAL NOT NULL,
                coordenada_y REAL NOT NULL,
                codigo TEXT,
                descricao TEXT,
                dados_completos TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                sync_status TEXT DEFAULT 'pending',
                version INTEGER DEFAULT 1,
                FOREIGN KEY (projeto_id) REFERENCES projetos_local(id)
            )
        """)
        
        # Tabela de perímetros locais
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS perimetros_local (
                id TEXT PRIMARY KEY,
                projeto_id TEXT NOT NULL,
                nome TEXT NOT NULL,
                pontos TEXT NOT NULL,
                area REAL,
                perimetro REAL,
                dados_completos TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                sync_status TEXT DEFAULT 'pending',
                version INTEGER DEFAULT 1,
                FOREIGN KEY (projeto_id) REFERENCES projetos_local(id)
            )
        """)
        
        # Índices para performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pontos_projeto 
            ON pontos_local(projeto_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_perimetros_projeto 
            ON perimetros_local(projeto_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_projetos_sync 
            ON projetos_local(sync_status)
        """)
        
        self.conn.commit()
    
    # ========== Projetos ==========
    
    def save_projeto(self, projeto: Dict[str, Any]) -> None:
        """Salva ou atualiza projeto localmente."""
        cursor = self.conn.cursor()
        
        now = datetime.utcnow().isoformat()
        
        cursor.execute("""
            INSERT OR REPLACE INTO projetos_local 
            (id, nome, cliente, tipo_processo, perimetro_ativo, dados_completos, 
             created_at, updated_at, sync_status, version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', 
                    COALESCE((SELECT version FROM projetos_local WHERE id = ?), 0) + 1)
        """, (
            projeto['id'],
            projeto.get('nome', ''),
            projeto.get('cliente', ''),
            projeto.get('tipo_processo', ''),
            json.dumps(projeto.get('perimetro_ativo', [])),
            json.dumps(projeto),
            projeto.get('created_at', now),
            now,
            projeto['id'],
        ))
        
        self.conn.commit()
        logger.debug(f"Projeto {projeto['id']} salvo localmente")
    
    def get_projeto(self, projeto_id: str) -> Optional[Dict[str, Any]]:
        """Recupera projeto do armazenamento local."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT dados_completos FROM projetos_local 
            WHERE id = ?
        """, (projeto_id,))
        
        row = cursor.fetchone()
        if row:
            return json.loads(row['dados_completos'])
        return None
    
    def get_all_projetos(self) -> List[Dict[str, Any]]:
        """Recupera todos os projetos locais."""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT dados_completos FROM projetos_local ORDER BY updated_at DESC")
        
        return [json.loads(row['dados_completos']) for row in cursor.fetchall()]
    
    # ========== Pontos ==========
    
    def save_ponto(self, ponto: Dict[str, Any]) -> None:
        """Salva ou atualiza ponto localmente."""
        cursor = self.conn.cursor()
        
        now = datetime.utcnow().isoformat()
        
        cursor.execute("""
            INSERT OR REPLACE INTO pontos_local 
            (id, projeto_id, nome, coordenada_x, coordenada_y, codigo, descricao,
             dados_completos, created_at, updated_at, sync_status, version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending',
                    COALESCE((SELECT version FROM pontos_local WHERE id = ?), 0) + 1)
        """, (
            ponto['id'],
            ponto['projeto_id'],
            ponto.get('nome', ''),
            ponto.get('coordenada_x', 0),
            ponto.get('coordenada_y', 0),
            ponto.get('codigo', ''),
            ponto.get('descricao', ''),
            json.dumps(ponto),
            ponto.get('created_at', now),
            now,
            ponto['id'],
        ))
        
        self.conn.commit()
        logger.debug(f"Ponto {ponto['id']} salvo localmente")
    
    def get_pontos_by_projeto(self, projeto_id: str) -> List[Dict[str, Any]]:
        """Recupera pontos de um projeto."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT dados_completos FROM pontos_local 
            WHERE projeto_id = ?
            ORDER BY nome
        """, (projeto_id,))
        
        return [json.loads(row['dados_completos']) for row in cursor.fetchall()]
    
    # ========== Perímetros ==========
    
    def save_perimetro(self, perimetro: Dict[str, Any]) -> None:
        """Salva ou atualiza perímetro localmente."""
        cursor = self.conn.cursor()
        
        now = datetime.utcnow().isoformat()
        
        cursor.execute("""
            INSERT OR REPLACE INTO perimetros_local 
            (id, projeto_id, nome, pontos, area, perimetro, dados_completos,
             created_at, updated_at, sync_status, version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending',
                    COALESCE((SELECT version FROM perimetros_local WHERE id = ?), 0) + 1)
        """, (
            perimetro['id'],
            perimetro['projeto_id'],
            perimetro.get('nome', ''),
            json.dumps(perimetro.get('pontos', [])),
            perimetro.get('area', 0),
            perimetro.get('perimetro', 0),
            json.dumps(perimetro),
            perimetro.get('created_at', now),
            now,
            perimetro['id'],
        ))
        
        self.conn.commit()
        logger.debug(f"Perímetro {perimetro['id']} salvo localmente")
    
    def get_perimetros_by_projeto(self, projeto_id: str) -> List[Dict[str, Any]]:
        """Recupera perímetros de um projeto."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT dados_completos FROM perimetros_local 
            WHERE projeto_id = ?
            ORDER BY updated_at DESC
        """, (projeto_id,))
        
        return [json.loads(row['dados_completos']) for row in cursor.fetchall()]
    
    # ========== Sync Status ==========
    
    def mark_synced(self, entity_type: str, entity_id: str) -> None:
        """Marca entidade como sincronizada."""
        cursor = self.conn.cursor()
        
        table_map = {
            'projeto': 'projetos_local',
            'ponto': 'pontos_local',
            'perimetro': 'perimetros_local',
        }
        
        table = table_map.get(entity_type)
        if not table:
            logger.warning(f"Tipo de entidade desconhecido: {entity_type}")
            return
        
        cursor.execute(f"""
            UPDATE {table} 
            SET sync_status = 'synced', updated_at = ?
            WHERE id = ?
        """, (datetime.utcnow().isoformat(), entity_id))
        
        self.conn.commit()
    
    def get_pending_sync(self, entity_type: str) -> List[Dict[str, Any]]:
        """Recupera entidades pendentes de sincronização."""
        cursor = self.conn.cursor()
        
        table_map = {
            'projeto': 'projetos_local',
            'ponto': 'pontos_local',
            'perimetro': 'perimetros_local',
        }
        
        table = table_map.get(entity_type)
        if not table:
            return []
        
        cursor.execute(f"""
            SELECT dados_completos FROM {table} 
            WHERE sync_status != 'synced'
            ORDER BY updated_at ASC
        """)
        
        return [json.loads(row['dados_completos']) for row in cursor.fetchall()]
    
    def clear_synced(self, older_than_days: int = 7) -> int:
        """Remove entidades sincronizadas antigas."""
        cursor = self.conn.cursor()
        removed = 0
        
        cutoff_date = datetime.utcnow().isoformat()
        
        for table in ['projetos_local', 'pontos_local', 'perimetros_local']:
            cursor.execute(f"""
                DELETE FROM {table} 
                WHERE sync_status = 'synced' 
                  AND updated_at < ?
            """, (cutoff_date,))
            
            removed += cursor.rowcount
        
        self.conn.commit()
        
        if removed > 0:
            logger.info(f"Removidas {removed} entidades sincronizadas antigas")
        
        return removed
    
    def close(self) -> None:
        """Fecha conexão com banco de dados."""
        if self.conn:
            self.conn.close()
            logger.info("OfflineStorage fechado")


__all__ = ["OfflineStorage"]
