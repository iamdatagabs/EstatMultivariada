# Runbook Operacional

## Executar localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r python/requirements.txt -r python/requirements-dev.txt
PYTHONPATH=python/src python -m estat_multivariada.cli run \
  --input data/raw --output data --docs-data docs/data \
  --config config/datasets.yml
PYTHONPATH=python/src pytest -q
```

Para tracking MLflow opcional, instale `python/requirements-ml.txt`.

## Verificar produtos

- `data/bronze/`: cópias de fontes;
- `data/silver/`: CSV e Parquet normalizados;
- `data/gold/manifest.json`: lineage e manifesto;
- `data/gold/bi_summary.json`: resumo analítico;
- `data/gold/analytics.duckdb`: warehouse;
- `docs/data/bi_summary.json`: contrato do dashboard.

Consultar SQL:

```python
import duckdb
with duckdb.connect("data/gold/analytics.duckdb", read_only=True) as con:
    print(con.sql("SELECT * FROM bi_dataset_quality").df())
```

## Diagnóstico de falhas

| Sintoma | Causa provável | Ação |
|---|---|---|
| Dataset configurado não encontrado | Nome/caminho não corresponde | Conferir `file` no YAML e nome em `data/raw/` |
| Erro de leitura CSV | Codificação, delimitador ou arquivo malformado | Inspecionar bytes/encoding e delimitador; converter a fonte com rastreabilidade |
| Colunas duplicadas após normalização | Cabeçalhos diferentes colidem | Renomear explicitamente a fonte e revisar o contrato |
| Contrato falha | Nulos, domínio ou unicidade violados | Corrigir fonte ou rever regra com justificativa documentada |
| PCA não gerada | Menos de duas colunas numéricas variáveis ou amostra insuficiente | Verificar tipos, missingness e variação |
| ML falha | Target ausente, classe rara ou poucos registros | Revisar semântica, amostra e desenho; não reduzir critérios apenas para forçar execução |
| Dashboard sem dados | JSON não gerado ou caminho divergente | Rodar pipeline e conferir `docs/data/bi_summary.json` |
| Pages não publica | Build falhou, permissões ou ambiente Pages | Conferir primeiro job de build, depois job deploy e permissões Pages |

## CI/CD

O workflow de pipeline executa:
1. checkout;
2. setup Python;
3. instalação de dependências;
4. compilação e testes;
5. execução sobre os datasets declarados;
6. upload do diretório `docs/` como artifact Pages;
7. deploy após sucesso do build.

Pull Requests devem executar validações sem publicar o site. O job de deploy é dependente do job de build.

## Recuperação e rollback

- Não editar manualmente arquivos Gold para corrigir um erro de transformação; corrigir fonte/config/código e reexecutar.
- Se um artefato publicado estiver incorreto, reverter o commit que introduziu a mudança e executar novamente o workflow.
- Antes de reexecutar, verificar se a fonte e o YAML estão alinhados.
- DuckDB atual é recriado por execução; preservar cópia do arquivo se uma análise exigir comparação entre versões.
- A publicação Pages deve ser considerada concluída apenas quando o job deploy termina com sucesso e a URL publicada é acessível.

## Segurança

Não imprimir secrets nos logs. Não armazenar tokens no YAML, notebooks, datasets ou artifacts. O conteúdo em `docs/` é público.
