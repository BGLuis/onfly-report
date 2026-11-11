# Entrega — Consolidador de Reservas de Hotel (Onfly)

## 1. Defeitos Corrigidos e Causa Raiz (em uma frase por defeito)

Foram identificados e corrigidos **5 defeitos funcionais** no código original do CLI, além de reforços de validação de domínio e tratamento de erros de entrada:

1. **Truncamento silencioso na leitura do CSV de reservas (`src/onfly_report/repositories/csv_reservation_repository.py:47-48`)**
   * **Causa raiz:** O método `CsvReservationRepository.read()` interrompia o laço de leitura ao atingir 200 linhas (`if len(rows) == 200: break`), descartando silenciosamente as 100 reservas restantes de `data/reservas_hoteis.csv`.
2. **Inclusão indevida de reservas `NO_SHOW` nos cálculos faturáveis (`src/onfly_report/services/status_policy.py:8`)**
   * **Causa raiz:** A função `is_billable(status)` verificava `status != "CANCELLED"` em vez de `status == "CONFIRMED"`, fazendo com que reservas `NO_SHOW` fossem somadas em noites, valores financeiros, `by_month` e `top_hotels`.
3. **Cálculo incorreto de noites na virada de mês/ano (`src/onfly_report/services/stay_calculator.py:10`)**
   * **Causa raiz:** A função `calculate_room_nights` subtraía apenas o número do dia do mês (`checkout.day - checkin.day`) em vez da diferença entre objetos `date` (`(checkout - checkin).days`), gerando valores negativos ou incorretos quando a estadia cruzava meses ou anos.
4. **Inversão da operação cambial e uso de `float` em valores monetários (`src/onfly_report/services/currency_converter.py:11`)**
   * **Causa raiz:** A função `convert_to_brl` dividia o valor pela taxa de câmbio após converter os operandos para `float` (`Decimal(str(float(amount) / float(rate)))`), quando a regra exige multiplicação exata em `Decimal` (`amount * rate`).
5. **Ordenação invertida do ranking `top_hotels` (`src/onfly_report/services/report_builder.py:91`)**
   * **Causa raiz:** A chave de ordenação `key=lambda item: (item[1]["amount"], item[0])` ordenava os hotéis por valor acumulado em BRL de forma crescente em vez de decrescente (`(-item[1]["amount"], item[0])`).

---

## 2. Como o Problema Foi Investigado e Abordado

1. **Leitura da especificação e execução inicial da suíte de testes:**
   * A investigação começou pela leitura integral do contrato e das regras de negócio no `README.md`, seguida da execução de `pytest -q`, na qual todos os 5 testes fornecidos falhavam (`test_currency.py`, `test_nights.py`, `test_regression_report.py`, `test_status_rules.py`, `test_top_hotels.py`).
2. **Inspeção estática ponta a ponta do fluxo de execução:**
   * Seguindo a cadeia `cli.py` → `CsvReservationRepository` / `CsvRateRepository` → `RowParser` → `status_policy` → `stay_calculator` → `currency_converter` → `ReportBuilder`, cada etapa da ordem de processamento (`ler → converter tipos → contar status → filtrar CONFIRMED → agregar`) foi confrontada com a especificação.
   * Essa inspeção revelou não apenas os 4 defeitos cobertos diretamente pelos testes unitários fornecidos (status, noites, câmbio e ordenação de `top_hotels`), mas também um **5º defeito oculto** em `CsvReservationRepository.read()` (`if len(rows) == 200: break`), que não era acionado pelos testes fornecidos por usarem amostras de 1 a 4 linhas, mas truncava o arquivo principal `data/reservas_hoteis.csv` (300 reservas).
3. **Endurecimento de validações e cobertura complementar de testes:**
   * Sem alterar nenhum teste fornecido, foram adicionadas validações de invariantes de domínio em `RowParser`, `CsvReservationRepository`, `CsvRateRepository`, `convert_to_brl`, `calculate_room_nights` e `ReportBuilder` para garantir o retorno consistente do código de saída `2` (`InputFileError`) em entradas inválidas.
   * Foi criado o arquivo `tests/test_domain_and_cli.py` cobrindo a amostra oficial (`data/exemplo-validacao.csv`), o dataset completo de 300 reservas (`data/reservas_hoteis.csv`), precisão `Decimal` com arredondamento `ROUND_HALF_UP` apenas na serialização, empates no ranking, virada de ano/ano bissexto e códigos de saída do CLI (`0`, `1`, `2`).

---

## 3. Detalhamento Técnico das Correções e Impacto nos Dados

| Arquivo | Antes | Depois |
| :--- | :--- | :--- |
| `src/onfly_report/repositories/csv_reservation_repository.py` | Interrompia a leitura em `if len(rows) == 200: break` | Lê todas as linhas do CSV e valida integridade de colunas e codificação UTF-8 |
| `src/onfly_report/services/status_policy.py` | `return status != "CANCELLED"` | `return status == "CONFIRMED"` |
| `src/onfly_report/services/stay_calculator.py` | `return (checkout.day - checkin.day) * rooms` | `return (checkout - checkin).days * rooms` (com validação de `checkout > checkin` e `rooms >= 1`) |
| `src/onfly_report/services/currency_converter.py` | `return Decimal(str(float(amount) / float(rate)))` | `return amount * rate` (em `Decimal` exato, levantando `InputFileError` se a moeda não existir) |
| `src/onfly_report/services/report_builder.py` | `key=lambda item: (item[1]["amount"], item[0])` | `key=lambda item: (-item[1]["amount"], item[0])` |

### Comparativo de Resultados (Antes vs. Depois)

#### Amostra de validação (`data/exemplo-validacao.csv`)

| Métrica | Antes das correções | Depois das correções | Esperado (`README.md`) |
| :--- | ---: | ---: | ---: |
| `total_reservations` | `12` | `12` | `12` |
| `confirmed_reservations` | `9` | `9` | `9` |
| `cancelled_reservations` | `2` | `2` | `2` |
| `no_show_reservations` | `1` | `1` | `1` |
| `total_room_nights` | `-33` | `28` | `28` |
| `total_amount_brl` | `"5962.41"` | `"7566.00"` | `"7566.00"` |
| `average_nightly_rate_brl` | `"0.00"` | `"270.21"` | `"270.21"` |

#### Base completa (`data/reservas_hoteis.csv`)

| Métrica | Antes das correções | Depois das correções |
| :--- | ---: | ---: |
| `total_reservations` | `200` (truncado) | `300` |
| `confirmed_reservations` | `153` | `235` |
| `cancelled_reservations` | `22` | `31` |
| `no_show_reservations` | `25` | `34` |
| `total_room_nights` | `-1393` | `1347` |
| `total_amount_brl` | `"193218.53"` | `"396170.00"` |
| `average_nightly_rate_brl` | `"0.00"` | `"294.11"` |

---

## 4. Como Validar

### 4.1. Preparar o ambiente

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### 4.2. Executar os testes e o linter

```bash
pytest -q
ruff check .
```

### 4.3. Validar com a amostra oficial (`data/exemplo-validacao.csv`)

```bash
PYTHONPATH=src python -m onfly_report \
  --input data/exemplo-validacao.csv \
  --rates data/taxas_cambio.csv \
  --output output/exemplo.json
```

Saída esperada em `stdout`:

```text
Reservas: 12 | Confirmadas: 9 | Noites: 28 | Total BRL: 7566.00
```

### 4.4. Gerar o relatório principal (`output/report.json`)

```bash
PYTHONPATH=src python -m onfly_report \
  --input data/reservas_hoteis.csv \
  --rates data/taxas_cambio.csv \
  --output output/report.json
```

Saída esperada em `stdout`:

```text
Reservas: 300 | Confirmadas: 235 | Noites: 1347 | Total BRL: 396170.00
```

---

## 5. Resultado do `pytest`

```text
$ pytest -v
============================= test session starts ==============================
configfile: pyproject.toml
testpaths: tests
collected 23 items

tests/test_currency.py::test_currency_conversion_to_brl PASSED           [  4%]
tests/test_domain_and_cli.py::test_validation_sample_matches_readme_contract PASSED [  8%]
tests/test_domain_and_cli.py::test_full_dataset_reads_all_300_rows_without_truncation PASSED [ 13%]
tests/test_domain_and_cli.py::test_decimal_exact_sum_and_round_half_up_only_at_serialization PASSED [ 17%]
tests/test_domain_and_cli.py::test_empty_or_unconfirmed_reservations_produce_zero_totals PASSED [ 21%]
tests/test_domain_and_cli.py::test_room_nights_across_year_leap_year_and_multiple_rooms PASSED [ 26%]
tests/test_domain_and_cli.py::test_top_hotels_tie_breaking_by_hotel_id_and_by_month_ordering PASSED [ 30%]
tests/test_domain_and_cli.py::test_status_policy_and_currency_converter_validation PASSED [ 34%]
tests/test_domain_and_cli.py::test_row_parser_rejects_invalid_domain_values[overrides0-checkout .* posterior ao checkin] PASSED [ 39%]
tests/test_domain_and_cli.py::test_row_parser_rejects_invalid_domain_values[overrides1-checkout .* posterior ao checkin] PASSED [ 43%]
tests/test_domain_and_cli.py::test_row_parser_rejects_invalid_domain_values[overrides2-rooms deve ser >= 1] PASSED [ 47%]
tests/test_domain_and_cli.py::test_row_parser_rejects_invalid_domain_values[overrides3-status desconhecido] PASSED [ 52%]
tests/test_domain_and_cli.py::test_row_parser_rejects_invalid_domain_values[overrides4-amount inválido] PASSED [ 56%]
tests/test_domain_and_cli.py::test_row_parser_rejects_invalid_domain_values[overrides5-campos obrigatórios vazios] PASSED [ 60%]
tests/test_domain_and_cli.py::test_row_parser_rejects_invalid_domain_values[overrides6-linha 2 inválida] PASSED [ 65%]
tests/test_domain_and_cli.py::test_cli_exit_codes_and_stdout_contract PASSED [ 69%]
tests/test_domain_and_cli.py::test_csv_repositories_and_report_builder_error_handling PASSED [ 73%]
tests/test_domain_and_cli.py::test_non_report_columns_do_not_affect_totals_or_fail_when_empty PASSED [ 78%]
tests/test_domain_and_cli.py::test_csv_files_with_utf8_bom_are_accepted PASSED [ 82%]
tests/test_nights.py::test_nights_across_month_boundary PASSED           [ 86%]
tests/test_regression_report.py::test_regression_report_on_sample PASSED [ 91%]
tests/test_status_rules.py::test_status_rules_exclude_cancelled_and_no_show PASSED [ 95%]
tests/test_top_hotels.py::test_top_hotels_are_ranked_descending PASSED   [100%]

============================== 23 passed in 0.55s ==============================
```

```text
$ pytest -q
.......................                                                  [100%]
23 passed in 0.49s
```
