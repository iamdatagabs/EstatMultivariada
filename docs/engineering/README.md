# Engenharia da Plataforma

Esta documentação descreve a arquitetura implementada, o fluxo operacional e as decisões técnicas da plataforma **Estatística Multivariada**.

## Percurso recomendado

1. [Visão arquitetural](architecture.md) — componentes, responsabilidades, fronteiras e fluxo de dados.
2. [Pipeline passo a passo](pipeline-lifecycle.md) — ciclo de vida de uma execução, entradas, saídas e validações.
3. [Contratos e governança](data-contracts.md) — metadata, qualidade, lineage e política de ML.
4. [Runbook operacional](runbook.md) — execução local, CI/CD, falhas, recuperação e publicação.
5. [Decisões arquiteturais](decisions/) — ADRs que registram escolhas e trade-offs.

## Estado de maturidade

| Capacidade | Estado |
|---|---|
| Metadata as Code | Implementado em `config/datasets.yml` |
| Ingestão CSV e SHA-256 | Implementado |
| Bronze / Silver / Gold | Implementado |
| CSV e Parquet | Implementado |
| Contratos básicos de qualidade | Implementado |
| Warehouse DuckDB e modelo dimensional de qualidade | Implementado |
| PCA, K-means e perfilamento | Implementado |
| Classificação supervisionada com target explícito | Implementado, opt-in |
| Tracking MLflow | Implementado como dependência opcional |
| Testes unitários e integração do pipeline | Implementados |
| Deploy de dashboard em GitHub Pages | Implementado via Actions |
| Orquestração distribuída, CDC, incrementalidade e data observability | Evoluções futuras, não implementadas |

Não interpretar itens futuros como capacidades disponíveis. A plataforma atual é uma execução batch orientada a arquivos, em um único processo Python, com warehouse analítico local DuckDB.
