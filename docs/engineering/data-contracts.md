# Contratos, Qualidade e Governança

## 1. Configuração

`config/datasets.yml` é a fonte declarativa da execução. Cada item lista um arquivo em `data/raw/`, sua descrição/domínio e regras de qualidade opcionais.

## 2. Regras suportadas

```yaml
datasets:
  - file: experimento.csv
    description: Dados experimentais
    domain: teaching
    contract:
      required_columns: [id, grupo, resposta]
      not_null: [id, grupo, resposta]
      unique: [id]
      accepted_values:
        grupo: [controle, tratamento]
      fail_on_error: true
```

| Regra | Significado | Severidade |
|---|---|---|
| `required_columns` | A coluna precisa existir | error |
| `not_null` | Não aceita valores ausentes | error |
| `unique` | Não aceita duplicatas na coluna | error |
| `accepted_values` | Restringe o domínio permitido | error |
| `fail_on_error` | Interrompe a execução se houver errors | boolean |

A ausência de uma regra significa que ela não é aplicada. Regras de unicidade atuais são por coluna, não por chave composta.

## 3. Lineage

O manifesto Gold registra nome da fonte, SHA-256, linhas, colunas, caminhos de saída, tabela DuckDB e issues identificadas. O hash é calculado sobre o arquivo bruto, antes da normalização.

## 4. Política de ML

O pipeline não infere variável resposta. Para ativar classificação, configure explicitamente:

```yaml
model:
  target: classe
  exclude_features: [id, coluna_com_vazamento]
```

Antes de habilitar:
1. documentar significado, unidade e temporalidade do target;
2. identificar a unidade observacional e independência das amostras;
3. excluir identificadores e variáveis posteriores ao desfecho;
4. avaliar desbalanceamento e tamanho amostral;
5. definir estratégia de validação compatível com o desenho (por grupo, tempo ou indivíduo, quando necessário);
6. comparar com baseline e reportar métricas por classe.

A validação estratificada atual não é apropriada para dados agrupados, temporais ou com observações repetidas dependentes. Nesses casos, a estratégia de CV precisa ser especializada antes de qualquer conclusão.

## 5. Privacidade e publicação

O repositório e GitHub Pages são públicos. Nunca versionar dados sensíveis, prontuários, identificadores pessoais, tokens ou credenciais. Dados didáticos também devem ser revisados quanto a licenças e restrições de redistribuição.

## 6. Limitações conhecidas

- contratos não possuem ainda schema de tipos, ranges ou regras estatísticas;
- qualidade é executada em batch, sem monitoramento contínuo;
- o modelo dimensional é recriado, não um histórico append-only;
- não há catálogo central de dados;
- os hashes rastreiam arquivos, não cada linha/registro;
- não há validação de drift ou reconciliação com fonte externa.
