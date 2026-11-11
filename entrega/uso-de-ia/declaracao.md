# Declaração de Uso de Inteligência Artificial

## 1. Ferramenta e Modelo Utilizados

* **Ferramenta:** Antigravity CLI (Google DeepMind Agentic Coding Assistant)
* **Modelo:** Gemini (Advanced Agentic Coding)

## 2. O que a IA fez e o que o desenvolvedor fez

### Papel do Desenvolvedor
* Definiu o escopo de auditoria e exigiu rigor técnico máximo na verificação de todos os requisitos obrigatórios e opcionais do repositório.
* Revisou os critérios de aceite do `README.md`, a integridade dos dados fornecidos (`data/`) e dos testes originais (`tests/`), validando o relatório final gerado em `output/report.json` e a documentação de entrega.

### Papel da IA
* Executou a suíte de testes inicial (`pytest -q`) para reproduzir as falhas existentes nos 5 testes fornecidos.
* Analisou todos os módulos em `src/onfly_report/` confrontando cada linha com as regras de negócio do `README.md`, identificando os 5 defeitos do projeto:
  1. Limite artificial de leitura de 200 linhas em `CsvReservationRepository.read()`.
  2. Regra de faturamento incorreta em `is_billable()` que incluía `NO_SHOW`.
  3. Cálculo de noites por dia do mês (`checkout.day - checkin.day`) em vez de diferença de datas (`(checkout - checkin).days`).
  4. Conversão cambial invertida (divisão em vez de multiplicação) e com conversão intermediária para `float` em `convert_to_brl()`.
  5. Ordenação ascendente em vez de descendente por valor em BRL no ranking `top_hotels` em `ReportBuilder.build()`.
* Implementou as correções nos módulos de `src/onfly_report/` e reforçou a validação de entradas inválidas (`InputFileError` -> código de saída `2`).
* Criou a suíte complementar `tests/test_domain_and_cli.py` sem modificar os testes fornecidos, validando a amostra oficial, o dataset completo de 300 reservas, casos de borda e contrato de saída do CLI.
* Gerou o relatório consolidado em `output/report.json` e redigiu a documentação técnica em `entrega/README-ENTREGA.md`.
