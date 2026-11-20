# ADR-002 — Target supervisionado explícito

- Status: Accepted
- Data: 2026-11-20

## Contexto
Inferir automaticamente uma variável resposta pela cardinalidade pode produzir modelos sem significado científico, com leakage ou interpretação incorreta.

## Decisão
Treinar modelos supervisionados somente quando `model.target` estiver explicitamente definido em metadata. Exigir target presente, amostra mínima e mais de uma classe. Registrar baseline, accuracy e macro-F1.

## Consequências
- evita classificações automáticas sem semântica;
- transfere ao responsável pelo dataset a decisão científica sobre o target;
- a validação estratificada atual é baseline técnico, não solução universal para dados agrupados ou temporais.
