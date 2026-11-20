# Estatística Multivariada | Data Engineering, Analytics, BI & ML

Projeto acadêmico de Estatística Multivariada (UEPG, 2024/2), evoluído para um laboratório reprodutível de engenharia de dados, ciência de dados, BI e machine learning. Os scripts originais em R e os CSVs históricos na raiz são preservados.

## Arquitetura

```text
CSV → Bronze (cópias + SHA-256) → Silver (dados limpos CSV/Parquet)
    → Gold (qualidade, perfis, PCA, clusters, ML, DuckDB)
    → Dashboard BI (GitHub Pages)
```

- **Bronze:** cópias rastreáveis dos arquivos de entrada, sem alterar as fontes.
- **Silver:** nomes de colunas padronizados, espaços removidos, valores infinitos tratados e armazenamento CSV + Parquet.
- **Gold:** manifesto SHA-256, perfil de qualidade, estatística descritiva, cargas/escores PCA, atribuições de clusters, importância de variáveis e métricas de classificação.
- **DuckDB:** banco analítico local com uma tabela por dataset, consultável em SQL.
- **BI:** dashboard estático alimentado por um resumo JSON produzido pelo pipeline.

## Capacidades

1. Ingestão CSV com detecção de delimitador e rastreabilidade SHA-256.
2. Qualidade: dimensões, duplicatas, ausências por coluna, tipos e colunas constantes.
3. Estatística descritiva e análise de componentes principais (PCA).
4. Clusterização K-means exploratória e coeficiente silhouette quando aplicável.
5. Classificação Random Forest quando há alvo categórico com amostras suficientes, validação cruzada estratificada, acurácia, macro-F1 e importância de atributos.
6. Persistência em Parquet e consultas analíticas com DuckDB.
7. Dashboard BI com catálogo de dados, cobertura, qualidade, variância explicada, agrupamentos e métricas de ML.
8. R: funções reutilizáveis para PCA e clusterização hierárquica, além dos scripts didáticos originais.

A seleção automática de alvo é heurística e deve ser revisada antes de qualquer interpretação. Em bases pequenas, a validação cruzada pode ser instável. PCA e clustering são exploratórios e não implicam causalidade. Matrizes de distância e similaridade requerem interpretação específica e não devem ser tratadas automaticamente como observações independentes.

## Estrutura

```text
data/
  raw/       # fontes de trabalho, cópias dos CSVs originais
  bronze/    # cópias imutáveis + manifesto
  silver/    # CSV e Parquet normalizados
  gold/      # relatórios, modelos, banco DuckDB
python/src/estat_multivariada/
R/functions/ # funções reutilizáveis
R/scripts/   # execução parametrizada
tests/       # testes automatizados
docs/        # dashboard BI
.github/workflows/
```

## Execução local

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r python/requirements.txt -r python/requirements-dev.txt
PYTHONPATH=python/src python -m estat_multivariada.cli run --input data/raw --output data --docs-data docs/data
PYTHONPATH=python/src pytest -q
Rscript R/scripts/run_multivariate.R data/raw/Euroemp.csv /tmp/r-multivariate
```

## Business Intelligence

Depois de ativar GitHub Pages com GitHub Actions, acesse:
https://iamdatagabs.github.io/EstatMultivariada/

O dashboard apresenta o catálogo, volume, qualidade, PCA, clustering e modelos supervisionados. Os artefatos detalhados ficam em `data/gold/`.

## Automação

O workflow `.github/workflows/data-pipeline.yml` testa o código Python, valida e executa o fluxo R, roda o ETL/analytics/ML e publica o dashboard. É acionado por alterações em dados/código, execução manual e agenda semanal. O workflow `.github/workflows/tests.yml` mantém a checagem de qualidade em pull requests.

## Limites metodológicos e proveniência

Os resultados dependem das características de cada base. A classificação é omitida quando as classes não sustentam validação cruzada. O algoritmo e o alvo selecionados devem ser confirmados por quem conduz a análise. Os materiais da disciplina permanecem na raiz para preservar autoria e proveniência. Consulte a licença/origem de cada base antes de redistribuí-la.
