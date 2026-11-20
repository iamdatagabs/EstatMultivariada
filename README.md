# Estatística Multivariada — Data Platform, Analytics, BI & ML

Laboratório reprodutível de Engenharia de Dados e Estatística Multivariada. O repositório preserva os materiais didáticos originais em R e os dados de origem, enquanto adiciona uma plataforma de ingestão, qualidade, armazenamento analítico, modelagem dimensional, análise exploratória e experimentação supervisionada configurável.

## Arquitetura

```text
CSV sources + datasets.yml
        │
        ▼
  Ingestion / SHA-256 lineage
        │
        ▼
 Bronze (immutable source copies)
        │
        ▼
 Silver (normalized CSV + Parquet)
        │
        ├── Data contracts / quality results
        ▼
 Gold (profiles, PCA, clustering, ML artifacts)
        │
        ▼
 DuckDB analytical warehouse
   ├── silver_<dataset>
   ├── dim_dataset
   ├── dim_run
   ├── fact_data_quality
   └── bi_dataset_quality (view)
        │
        ▼
 BI JSON → GitHub Pages
        │
        └── MLflow experiment tracking (when a target is explicitly configured)
```

## Engenharia e governança

- **Metadata as code:** `config/datasets.yml` registra datasets, domínio, contratos e configuração de modelos.
- **Lineage:** SHA-256 dos arquivos de origem, identificação da execução e manifesto de artefatos.
- **Medallion architecture:** Bronze preserva cópia da fonte; Silver normaliza cabeçalhos/valores e publica CSV/Parquet; Gold concentra produtos analíticos.
- **Data contracts:** colunas obrigatórias, não nulos, unicidade e domínios aceitos são configuráveis. Violações bloqueiam a execução por padrão.
- **Warehouse:** DuckDB materializa tabelas Silver e modelo dimensional de qualidade, com consulta SQL local.
- **Analytics:** perfilamento, missingness, PCA e clustering exploratório.
- **ML governado:** nenhum target é inferido. O treinamento só ocorre com `model.target` declarado no YAML; validação estratificada, baseline e macro-F1 são registrados. Quando instalado via `python/requirements-ml.txt`, MLflow mantém parâmetros, métricas e artefatos localmente; sem o extra, os resultados permanecem nos artefatos Gold.
- **Automação:** testes unitários/integração, pipeline e publicação do dashboard por GitHub Actions.

## Executar

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r python/requirements.txt -r python/requirements-dev.txt\n# Opcional: tracking de experimentos supervisionados\npip install -r python/requirements-ml.txt
PYTHONPATH=python/src python -m estat_multivariada.cli run \\
  --input data/raw --output data --docs-data docs/data \\
  --config config/datasets.yml
PYTHONPATH=python/src pytest -q
```

Consultar o warehouse:

```python
import duckdb
con = duckdb.connect("data/gold/analytics.duckdb", read_only=True)
print(con.sql("SELECT * FROM bi_dataset_quality").df())
```

## Configurar um experimento supervisionado

Somente após confirmar a semântica da variável resposta e revisar features/leakage, adicione ao item correspondente:

```yaml
model:
  target: classe_confirmada
  exclude_features: [id, identificador_de_vazamento]
```

O pipeline falha explicitamente quando o target configurado não existe ou não há amostra/classe suficiente. Não configure targets apenas para obter métricas.

## Interpretação científica

PCA e clustering são exploratórios. Silhouette não comprova existência de grupos naturais. Métricas de classificação dependem da amostra, desenho de validação e definição do alvo; não sustentam causalidade. Os scripts originais de MANOVA, análise fatorial, discriminante, correlação canônica, escalonamento multidimensional e ordenação permanecem preservados e devem ser avaliados segundo seus pressupostos.

## Estrutura

- `config/`: metadata e contratos.
- `data/raw/`: fontes originais.
- `data/bronze/`, `data/silver/`, `data/gold/`: camadas de dados.
- `python/src/estat_multivariada/`: pipeline e CLI.
- `R/` e scripts `MEM*.R`: métodos e material original.
- `tests/`: testes automatizados.
- `docs/`: dashboard público.
- `.github/workflows/`: CI, pipeline e publicação.

## Dashboard

https://iamdatagabs.github.io/EstatMultivariada/
