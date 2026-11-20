# Estatística Multivariada | Data Engineering, Analytics, BI & ML

Projeto acadêmico de Estatística Multivariada (UEPG, 2024/2), evoluído para um laboratório reprodutível de engenharia de dados, ciência de dados, BI e machine learning. Os scripts originais em R e os CSVs de origem são preservados.

## Arquitetura

```text
CSV → Bronze (originais + SHA-256) → Silver (normalização)
    → Gold (perfilamento, PCA, clustering, ML e métricas)
    → Dashboard BI em GitHub Pages
```

- `data/raw`: fontes originais.
- `data/bronze`: cópias rastreáveis, sem alteração dos arquivos de origem.
- `data/silver`: dados normalizados.
- `data/gold`: perfis, métricas e artefatos analíticos.
- `python/src/estat_multivariada`: ETL, análise e ML.
- `R/functions` e `R/scripts`: funções reutilizáveis e execução de PCA em R.
- `docs`: dashboard BI.

## Executar localmente

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r python/requirements.txt
PYTHONPATH=python/src python -m estat_multivariada.cli run --input data/raw --output data --docs-data docs/data
PYTHONPATH=python/src pytest -q
```

## Capacidades do pipeline

1. Ingestão CSV com detecção de separador e manifesto SHA-256.
2. Camadas Bronze/Silver/Gold e normalização leve de nomes e espaços.
3. Qualidade: dimensões, duplicatas, valores ausentes, tipos e estatísticas descritivas.
4. PCA com padronização, escores, cargas e variância explicada.
5. K-means exploratório com silhouette quando aplicável.
6. Random Forest supervisionado quando uma variável categórica elegível é detectada, com validação cruzada estratificada e macro-F1.
7. Dashboard BI com catálogo, cobertura, qualidade, PCA, clusters e métricas dos modelos.

A seleção automática de alvo é heurística e deve ser revisada antes de qualquer interpretação. Em bases pequenas, a validação cruzada pode ser instável. PCA e clustering são exploratórios; não implicam causalidade. MANOVA, análise fatorial, discriminante e correlação canônica continuam disponíveis nos scripts originais e serão progressivamente encapsuladas na biblioteca R.

## Automação

O workflow `.github/workflows/data-pipeline.yml` executa testes e pipeline em push relevante, manualmente e em agenda semanal, publica os artefatos do dashboard. O workflow de qualidade Python também roda em pull requests.

## Dashboard

Após ativar GitHub Pages com GitHub Actions, acesse `https://iamdatagabs.github.io/EstatMultivariada/`.
