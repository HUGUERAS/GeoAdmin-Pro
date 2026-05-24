"""
GeoAdmin Pro - Migração para Supabase Storage

Migra arquivos cartográficos do disco local para o Supabase Storage,
mantendo trilha de auditoria e referências atualizadas.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from supabase import Client

logger = logging.getLogger(__name__)


class StorageMigration:
    """
    Migra arquivos do armazenamento local para o Supabase Storage.
    
    Mantém integridade das referências e cria logs de auditoria.
    """
    
    def __init__(self, supabase_client: Client, bucket_name: str):
        """
        Inicializa migrador de storage.
        
        Args:
            supabase_client: Cliente Supabase configurado.
            bucket_name: Nome do bucket no Supabase Storage.
        """
        self.supabase = supabase_client
        self.bucket_name = bucket_name
        logger.info(f"StorageMigration inicializada para bucket '{bucket_name}'")
    
    def migrate_file(
        self, 
        local_path: str, 
        project_id: str, 
        file_category: str,
        keep_local: bool = False
    ) -> Dict[str, Any]:
        """
        Migra um arquivo individual para o Supabase Storage.
        
        Args:
            local_path: Caminho completo do arquivo local.
            project_id: ID do projeto associado.
            file_category: Categoria do arquivo (ex: 'dwg', 'pdf', 'csv').
            keep_local: Se True, mantém cópia local após migração.
            
        Returns:
            Dicionário com resultado da migração.
        """
        result = {
            "success": False,
            "local_path": local_path,
            "storage_path": None,
            "public_url": None,
            "error": None,
            "migrated_at": None,
        }
        
        try:
            # Valida arquivo local
            if not os.path.exists(local_path):
                raise FileNotFoundError(f"Arquivo não encontrado: {local_path}")
            
            # Gera caminho no storage
            filename = os.path.basename(local_path)
            storage_path = f"{project_id}/{file_category}/{filename}"
            
            # Lê arquivo
            with open(local_path, 'rb') as f:
                file_data = f.read()
            
            # Upload para Supabase
            response = self.supabase.storage.from_(self.bucket_name).upload(
                storage_path,
                file_data,
                {"content-type": self._guess_content_type(local_path)}
            )
            
            # Gera URL pública
            public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(storage_path)
            
            # Remove arquivo local se não for manter
            if not keep_local:
                os.remove(local_path)
                logger.info(f"Arquivo local removido: {local_path}")
            
            result.update({
                "success": True,
                "storage_path": storage_path,
                "public_url": public_url,
                "migrated_at": datetime.utcnow().isoformat(),
            })
            
            logger.info(f"Arquivo migrado: {local_path} -> {storage_path}")
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Erro ao migrar arquivo {local_path}: {e}", exc_info=True)
        
        return result
    
    def migrate_project_files(
        self, 
        project_id: str, 
        local_dir: str,
        keep_local: bool = False
    ) -> Dict[str, Any]:
        """
        Migra todos os arquivos de um projeto.
        
        Args:
            project_id: ID do projeto.
            local_dir: Diretório local com arquivos do projeto.
            keep_local: Se True, mantém cópias locais.
            
        Returns:
            Resumo da migração.
        """
        result = {
            "project_id": project_id,
            "total_files": 0,
            "migrated": 0,
            "failed": 0,
            "errors": [],
            "migrated_at": None,
        }
        
        if not os.path.isdir(local_dir):
            result["errors"].append(f"Diretório não encontrado: {local_dir}")
            return result
        
        # Percorre diretório recursivamente
        for root, dirs, files in os.walk(local_dir):
            for filename in files:
                local_path = os.path.join(root, filename)
                result["total_files"] += 1
                
                # Determina categoria pelo diretório ou extensão
                rel_path = os.path.relpath(root, local_dir)
                category = rel_path.split(os.sep)[0] if rel_path != '.' else 'outros'
                
                # Migra arquivo
                migration_result = self.migrate_file(
                    local_path, 
                    project_id, 
                    category,
                    keep_local
                )
                
                if migration_result["success"]:
                    result["migrated"] += 1
                else:
                    result["failed"] += 1
                    result["errors"].append({
                        "file": filename,
                        "error": migration_result["error"],
                    })
        
        result["migrated_at"] = datetime.utcnow().isoformat()
        
        logger.info(
            f"Migração do projeto {project_id}: "
            f"{result['migrated']}/{result['total_files']} arquivos migrados"
        )
        
        return result
    
    def list_bucket_files(self, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lista arquivos no bucket do Supabase.
        
        Args:
            prefix: Prefixo opcional para filtrar arquivos.
            
        Returns:
            Lista de metadados dos arquivos.
        """
        try:
            query = self.supabase.storage.from_(self.bucket_name).list(prefix or "")
            return query if isinstance(query, list) else []
        except Exception as e:
            logger.error(f"Erro ao listar arquivos: {e}")
            return []
    
    def delete_file(self, storage_path: str) -> bool:
        """
        Remove arquivo do Supabase Storage.
        
        Args:
            storage_path: Caminho do arquivo no storage.
            
        Returns:
            True se removido com sucesso.
        """
        try:
            self.supabase.storage.from_(self.bucket_name).remove([storage_path])
            logger.info(f"Arquivo removido: {storage_path}")
            return True
        except Exception as e:
            logger.error(f"Erro ao remover arquivo {storage_path}: {e}")
            return False
    
    def _guess_content_type(self, filename: str) -> str:
        """Determina content-type baseado na extensão."""
        ext_map = {
            '.dwg': 'application/acad',
            '.dxf': 'application/dxf',
            '.pdf': 'application/pdf',
            '.csv': 'text/csv',
            '.json': 'application/json',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        }
        
        ext = os.path.splitext(filename)[1].lower()
        return ext_map.get(ext, 'application/octet-stream')
    
    def validate_bucket(self) -> Dict[str, Any]:
        """
        Valida configuração do bucket.
        
        Returns:
            Status de validação.
        """
        result = {
            "valid": False,
            "bucket_exists": False,
            "can_upload": False,
            "can_list": False,
            "error": None,
        }
        
        try:
            # Tenta listar arquivos (mesmo que vazio)
            files = self.list_bucket_files("")
            result["bucket_exists"] = True
            result["can_list"] = True
            
            # Teste de upload com arquivo mínimo
            test_path = "_validation/test.txt"
            try:
                self.supabase.storage.from_(self.bucket_name).upload(
                    test_path,
                    b"validation test",
                    {"content-type": "text/plain"}
                )
                result["can_upload"] = True
                
                # Limpa arquivo de teste
                self.delete_file(test_path)
                
            except Exception as upload_error:
                result["error"] = f"Upload falhou: {upload_error}"
            
            result["valid"] = result["bucket_exists"] and result["can_upload"]
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Validação do bucket falhou: {e}")
        
        return result


__all__ = ["StorageMigration"]
