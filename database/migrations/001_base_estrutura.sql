-- Migration 001: Estrutura base GeoAdmin Pro

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS projetos (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  nome TEXT NOT NULL,
  cliente_id UUID,
  status TEXT CHECK (status IN ('medicao','montagem','protocolado','aprovado')),
  zona_utm TEXT DEFAULT '23S',
  srid INTEGER DEFAULT 4674, -- SIRGAS 2000
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pontos (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  projeto_id UUID REFERENCES projetos(id) ON DELETE CASCADE,
  nome TEXT NOT NULL,
  coordenada GEOMETRY(POINT, 4674) NOT NULL,
  altitude NUMERIC(10,4),
  descricao TEXT,
  camada TEXT DEFAULT 'PONTOS',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS clientes (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  nome TEXT NOT NULL,
  cpf_cnpj TEXT UNIQUE,
  telefone TEXT,
  email TEXT,
  magic_link_token UUID,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

