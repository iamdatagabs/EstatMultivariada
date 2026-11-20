# Pipeline de Engenharia — Passo a Passo

Este documento descreve uma execução completa, da configuração à publicação.

## Pré-condições

- Python 3.11 recomendado;
- dependências de `python/requirements.txt`;
- arquivos de origem presentes em `data/raw/`;
- cada fonte declarada uma única vez em `config/datasets.yml`;
- espaço de escrita em `data/` e `docs/data/`.

## Etapa 1 — Declarar a fonte (metadata as code)

Edite `config/datasets.yml`. Cada entrada deve declarar o nome exato do arquivo, descrição, domínio e contrato. A chave `file` deve corresponder ao nome do arquivo em `data/raw/`.

Exemplo:

```yaml
datasets:
  - file: experimento.csv
    description: Ensaio experimental de referência
    domain: teaching
    contract:
      required_columns: [tratamento, resposta]
      not_null: [tratamento, resposta]
      fail_on_error: true
```

Não declarar um target de ML antes de validar seu significado científico, unidade de análise, classes e risco de vazamento.

## Etapa 2 — Descobrir e ingerir

O CLI lê a configuração e percorre apenas os datasets declarados. Para cada fonte:
1. verifica a existência do arquivo;
2. lê o CSV tentando autodetecção e separadores comuns;
3. calcula SHA-256 sobre os bytes originais;
4. registra dimensões e nome da fonte no manifesto.

A descoberta é declarativa, não uma varredura irrestrita do diretório. Isso evita que arquivos auxiliares sejam ingeridos acidentalmente.

## Etapa 3 — Preservar Bronze

O arquivo original é copiado para `data/bronze/`. Essa cópia permite inspecionar a entrada que alimentou a transformação. O hash no manifesto permite detectar alterações no arquivo de origem.

## Etapa 4 — Normalizar e validar

A transformação Silver:
- remove espaços nas extremidades dos nomes de coluna;
- substitui espaços internos dos nomes por underscore;
- remove espaços nas extremidades de valores textuais;
- converte valores infinitos em ausentes;
- rejeita nomes de colunas que colidam após normalização.

Em seguida, os contratos verificam colunas obrigatórias, nulos proibidos, unicidade e valores aceitos. Violações são registradas como issues. Com `fail_on_error: true`, a execução é interrompida.

## Etapa 5 — Materializar Silver

Cada dataset normalizado é publicado em:
- `data/silver/<dataset>.csv`;
- `data/silver/<dataset>.parquet`;
- tabela `silver_<dataset>` em `data/gold/analytics.duckdb`.

CSV facilita inspeção e intercâmbio. Parquet reduz custo de leitura analítica e preserva tipos. DuckDB oferece SQL sobre os dados sem exigir um servidor.

## Etapa 6 — Gerar produtos Gold

Para cada dataset, o pipeline cria:
- `descriptive_profile.csv`: estatísticas descritivas;
- `missingness.csv`: contagem de ausentes;
- `pca_scores.csv` e `pca_loadings.csv`, quando há variáveis numéricas elegíveis;
- `cluster_assignments.csv`, quando a amostra permite K-means;
- `feature_importance.csv` e métricas supervisionadas, apenas com target configurado.

PCA e K-means são exploratórios. A heurística de número de clusters não substitui validação científica nem escolha substantiva do modelo.

## Etapa 7 — Registrar qualidade no warehouse

O pipeline registra uma linha de qualidade por dataset/run e dimensões de dataset e execução. A view `bi_dataset_quality` consolida essas informações para consumo SQL.

## Etapa 8 — Produzir o contrato de BI

O pipeline gera `data/gold/bi_summary.json` e copia o resumo para `docs/data/bi_summary.json`. O dashboard consome o JSON estático; o navegador não consulta DuckDB diretamente.

Mudanças na estrutura do JSON devem ser acompanhadas de testes e atualização do frontend.

## Etapa 9 — Validar

Execute compilação e testes. O teste de integração cria um dataset temporário e confirma a criação de Parquet, tabelas DuckDB e JSON de BI.

```bash
PYTHONPATH=python/src python -m compileall -q python/src
PYTHONPATH=python/src pytest -q
```

## Etapa 10 — Publicar

Em execução não-Pull Request, GitHub Actions executa o pipeline sobre as fontes declaradas, gera o resumo do dashboard, empacota `docs/` como artifact e publica GitHub Pages após sucesso do job de build.

A publicação não deve ocorrer se validação ou pipeline falhar.

## Reprodutibilidade

Uma execução local equivalente:

```bash
PYTHONPATH=python/src python -m estat_multivariada.cli run \
  --input data/raw \
  --output data \
  --docs-data docs/data \
  --config config/datasets.yml
```

O identificador de execução e o manifesto permitem rastrear quais fontes participaram. Para comparação científica entre execuções, registre também versões de dependências, parâmetros e ambiente; esse inventário de ambiente é uma melhoria futura.
