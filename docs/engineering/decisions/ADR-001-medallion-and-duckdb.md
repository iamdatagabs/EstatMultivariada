# ADR-001 — Arquitetura Medallion e DuckDB

- Status: Accepted
- Data: 2026-11-20

## Contexto
O projeto precisa preservar fontes didáticas, tornar transformações reprodutíveis e oferecer consultas analíticas sem manter infraestrutura de banco gerenciada.

## Decisão
Adotar camadas Raw/Bronze/Silver/Gold, CSV e Parquet em Silver, e DuckDB como warehouse embarcado.

## Consequências
- baixo custo e execução local simples;
- lineage por hash e separação entre origem e transformação;
- SQL analítico sem servidor;
- limite single-node e sem concorrência multiusuário como serviço;
- incrementalidade e histórico completo ainda precisam ser projetados.
