# CONTEXTO DO PROJETO — GeoAdmin-Pro

> Abra ou cole este arquivo no início de conversas para fornecer contexto ao Claude.
> Última atualização: 2026-03-16

---

## 👤 Perfil Pessoal

- **Nome:** Hugo
- **Time:** Desenrola Team

---

## 🎯 Projeto: GeoAdmin-Pro

**Descrição:** Sistema de administração geoespacial integrado com Métrica TOPO, React Native (Expo) no frontend e FastAPI no backend.

---

## 🛠️ Stack Técnica

| Camada | Tecnologia |
|---|---|
| Frontend / Mobile | React Native (Expo) |
| Backend | FastAPI |
| Banco de Dados | Supabase (PostGIS) — projeto `jrlrlsotwsiidglcbifo` |
| Integração externa | Métrica TOPO |

---

## 🏗️ Decisões de Arquitetura

- **Fonte única de dados:** GeoAdmin-Pro é a fonte de verdade; **evitar replicar em múltiplos sistemas**.
- **Exportação Métrica:** via `POST /metrica/txt` — recebe JSON, retorna TXT.
- **Credenciais:** exclusivamente em `.env`; nunca commitar.
- **Supabase:** instância `jrlrlsotwsiidglcbifo`.

---

## 💬 Preferências de Resposta

- Responder **sempre em português**.
- Ser direto; evitar explicações longas.
- Priorizar integração com Métrica TOPO.

---

## 📌 Como usar

No início de uma conversa: **"Use o CONTEXTO_PROJETO.md de GeoAdmin-Pro"**
