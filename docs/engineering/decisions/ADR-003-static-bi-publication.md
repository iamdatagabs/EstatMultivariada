# ADR-003 — BI estático em GitHub Pages

- Status: Accepted
- Data: 2026-11-20

## Contexto
O dashboard deve ser acessível publicamente, com custo operacional baixo, sem backend web persistente.

## Decisão
O pipeline produz um JSON estático em `docs/data/`; o frontend o consome e GitHub Pages publica o diretório `docs/` após o build.

## Consequências
- distribuição simples por CDN e sem servidor de aplicação;
- atualização vinculada à execução batch;
- dados publicados são públicos;
- sem consultas SQL interativas ao DuckDB pelo navegador;
- dados sensíveis não podem compor os artefatos públicos.
