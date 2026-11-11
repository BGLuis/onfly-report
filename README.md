<p align="center">
  <picture><source media="(prefers-color-scheme: dark)" srcset="https://shieldcn.dev/header/graph.svg?title=Onfly+Report&subtitle=Consolidador+de+reservas+de+hotel+em+Python&logo=python&align=left&mode=dark" /><img alt="Onfly Report" src="https://shieldcn.dev/header/graph.svg?title=Onfly+Report&subtitle=Consolidador+de+reservas+de+hotel+em+Python&logo=python&align=left&mode=light" /></picture>
</p>

<p align="center">
  <picture><source media="(prefers-color-scheme: dark)" srcset="https://shieldcn.dev/github/stars/BGLuis/onfly-report.svg?variant=secondary&size=sm&mode=dark" /><img alt="GitHub Stars" src="https://shieldcn.dev/github/stars/BGLuis/onfly-report.svg?variant=secondary&size=sm&mode=light" /></picture>
  <picture><source media="(prefers-color-scheme: dark)" srcset="https://shieldcn.dev/github/forks/BGLuis/onfly-report.svg?variant=secondary&size=sm&mode=dark" /><img alt="GitHub Forks" src="https://shieldcn.dev/github/forks/BGLuis/onfly-report.svg?variant=secondary&size=sm&mode=light" /></picture>
  <picture><source media="(prefers-color-scheme: dark)" srcset="https://shieldcn.dev/github/watchers/BGLuis/onfly-report.svg?variant=secondary&size=sm&mode=dark" /><img alt="Watchers" src="https://shieldcn.dev/github/watchers/BGLuis/onfly-report.svg?variant=secondary&size=sm&mode=light" /></picture>
  <picture><source media="(prefers-color-scheme: dark)" srcset="https://shieldcn.dev/github/contributors/BGLuis/onfly-report.svg?theme=emerald&size=sm&mode=dark" /><img alt="Contributors" src="https://shieldcn.dev/github/contributors/BGLuis/onfly-report.svg?theme=emerald&size=sm&mode=light" /></picture>
  <picture><source media="(prefers-color-scheme: dark)" srcset="https://shieldcn.dev/github/license/BGLuis/onfly-report.svg?variant=ghost&size=sm&mode=dark" /><img alt="License" src="https://shieldcn.dev/github/license/BGLuis/onfly-report.svg?variant=ghost&size=sm&mode=light" /></picture>
</p>

<p align="center">
  <img alt="Python" src="https://shieldcn.dev/badge/Language-Python-3776AB.svg?logo=python&variant=branded&size=sm" />
  <img alt="Pytest" src="https://shieldcn.dev/badge/Tool-Pytest-0A9EDC.svg?logo=pytest&variant=branded&size=sm" />
  <img alt="Ruff" src="https://shieldcn.dev/badge/Tool-Ruff-D7FF64.svg?logo=ruff&variant=branded&size=sm" />
  <img alt="GitHub Actions" src="https://shieldcn.dev/badge/Tool-GitHub_Actions-2088FF.svg?logo=githubactions&variant=branded&size=sm" />
</p>

# 📖 Sobre

O **Onfly Report** é uma ferramenta de linha de comando (CLI) em Python que lê exportações CSV de reservas corporativas de hotel e tabelas de taxas de câmbio, valida regras de domínio e gera um relatório JSON consolidado com resumo financeiro em BRL (usando aritmética exata em `Decimal` e arredondamento `ROUND_HALF_UP`), agregação mensal por check-in e ranking dos principais hotéis.

O relatório final detalhado da investigação e das correções encontra-se em [`entrega/README-ENTREGA.md`](entrega/README-ENTREGA.md).

# 📋 Motivo

Desafio técnico da Onfly para diagnosticar, corrigir e validar um consolidador CLI de reservas de hotel em Python.

# 💻 Como iniciar

### Requisitos

- [Python](https://www.python.org/downloads/) >= 3.11
- [Pytest](https://docs.pytest.org/) 8.3.4
- [Ruff](https://docs.astral.sh/ruff/) 0.8.4

### Instalação

1. Clone o repositório:

   ```sh
   git clone https://github.com/BGLuis/onfly-report.git
   ```

2. Entre no diretório do projeto:

   ```sh
   cd onfly-report
   ```

3. Instale as dependências e inicie:

   ```sh
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements-dev.txt

   PYTHONPATH=src python -m onfly_report \
     --input data/reservas_hoteis.csv \
     --rates data/taxas_cambio.csv \
     --output output/report.json
   ```

O relatório é gravado em `output/report.json`; o CLI cria o diretório. Um resumo é impresso no stdout.

Os testes já estão em `tests/`. Rode:

```sh
pytest -q
```

---

## Estrutura

```text
.
├── README.md              # este arquivo
├── LICENSE                # licença MIT
├── pyproject.toml
├── requirements*.txt
├── data/
│   ├── reservas_hoteis.csv
│   ├── taxas_cambio.csv
│   └── exemplo-validacao.csv
├── src/onfly_report/      # CLI
├── tests/                 # testes fornecidos e complementares
├── entrega/               # documentação da entrega
└── output/                # relatório gerado
```

## Regras de negócio

Os dados fornecidos estão consistentes, os defeitos estavam no CLI e foram corrigidos.

As colunas do CSV são autoexplicativas. O relatório usa hotel, check-in, check-out, quartos, status, moeda e valor; as demais colunas não afetam os totais.

### Status

* Só `CONFIRMED` é faturável.
* `CANCELLED` e `NO_SHOW` contam em `total_reservations` e nas contagens por status, mas não entram em noites, valores, `by_month` nem `top_hotels`.

### Noites

```text
room_nights = (checkout_date - checkin_date).days * rooms
```

A diferença é não inclusiva: check-in 10/01 e check-out 13/01 = 3 noites. Vale também na virada de mês/ano.

### Câmbio

* `amount` está na moeda de `currency`.
* Converta com `amount * rate_to_brl`, usando a tabela `data/taxas_cambio.csv`.
* Todas as moedas do dataset têm taxa.

### Totais

* `total_reservations` = número de reservas no arquivo.
* `confirmed_reservations`, `cancelled_reservations` e `no_show_reservations` = contagens por status.
* `total_room_nights`, `total_amount_brl` e `average_nightly_rate_brl` usam apenas `CONFIRMED`.

### Ordem do processamento

```text
ler → converter tipos → contar status → filtrar CONFIRMED → agregar
```

### Exatidão

* Use `Decimal`, nunca `float`, no dinheiro.
* Some os valores exatos e arredonde **só na serialização**, para 2 casas, com half-up.
* `average_nightly_rate_brl = total_amount_brl / total_room_nights`; sem noites, `"0.00"`.
* Check-in/check-out são datas civis (`YYYY-MM-DD`).
* `generated_at` usa offset fixo `-03:00` e é ignorado na comparação.

### Ordenação

* `by_month`: `month` ascendente.
* `top_hotels`: `total_brl` decrescente; empate por `hotel_id` ascendente.

## Contrato do CLI

```sh
python -m onfly_report \
  --input data/reservas_hoteis.csv \
  --rates data/taxas_cambio.csv \
  --output output/report.json \
  --top 5
```

| Argumento | Obrigatório | Padrão |
| :--- | :--- | :--- |
| `--input` | sim | — |
| `--rates` | sim | — |
| `--output` | não | `output/report.json` |
| `--top` | não | `5` (inteiro ≥ 1) |

Códigos de saída: `0` sucesso, `2` entrada/argumento inválido, `1` erro inesperado.

O relatório deve ter exatamente este formato:

```json
{
  "report_version": "1.0",
  "generated_at": "2025-07-01T10:00:00-03:00",
  "summary": {
    "total_reservations": 0,
    "confirmed_reservations": 0,
    "cancelled_reservations": 0,
    "no_show_reservations": 0,
    "total_room_nights": 0,
    "total_amount_brl": "0.00",
    "average_nightly_rate_brl": "0.00"
  },
  "by_month": [
    {"month": "2025-01", "reservations": 0, "room_nights": 0, "total_brl": "0.00"}
  ],
  "top_hotels": [
    {"hotel_id": "H01", "hotel_name": "Hotel Exemplo", "room_nights": 0, "total_brl": "0.00"}
  ]
}
```

* Dinheiro é string com exatamente 2 casas (`"1234.50"`), sem separador de milhar.
* `report_version` é sempre `"1.0"`.
* `top_hotels` tem `--top` itens (ou menos, se houver menos hotéis).
* `by_month` usa o mês do check-in.
* Não altere nomes, tipos ou semântica dos campos.

## Amostra de validação

Rode o CLI na amostra e compare com o resultado abaixo:

```sh
PYTHONPATH=src python -m onfly_report \
  --input data/exemplo-validacao.csv \
  --rates data/taxas_cambio.csv \
  --output output/exemplo.json
```

<!-- AMOSTRA:INICIO -->

| Campo | Valor esperado |
| :--- | :--- |
| `total_reservations` | 12 |
| `confirmed_reservations` | 9 |
| `cancelled_reservations` | 2 |
| `no_show_reservations` | 1 |
| `total_room_nights` | 28 |
| `total_amount_brl` | 7566.00 |
| `average_nightly_rate_brl` | 270.21 |

| `month` | `reservations` | `room_nights` | `total_brl` |
| :--- | :--- | :--- | :--- |
| 2025-01 | 8 | 25 | 6684.00 |
| 2025-02 | 1 | 3 | 882.00 |

| `hotel_id` | `hotel_name` | `room_nights` | `total_brl` |
| :--- | :--- | :--- | :--- |
| H01 | Hotel Aurora Paulista | 3 | 1200.00 |
| H02 | Hotel Mirante | 2 | 1084.00 |
| H12 | Hotel Miami Beach | 1 | 1000.00 |
| H10 | Hotel Madrid, Gran Vía | 4 | 900.00 |
| H09 | Hotel Lisboa, Centro | 3 | 882.00 |

<!-- AMOSTRA:FIM -->

A amostra cobre apenas parte dos cenários; use as regras acima para os demais.

## Entrega

Suba o projeto, incluindo a pasta `entrega/`, em um repositório público no GitHub e compartilhe o acesso com nosso time via forms.

```text
entrega/
├── README-ENTREGA.md
└── uso-de-ia/                 # apenas se usou IA
    ├── sessao.md (ou .txt/.jsonl; várias: sessao-01.md, sessao-02.md...)
    └── declaracao.md
```

**[`entrega/README-ENTREGA.md`](entrega/README-ENTREGA.md)** contém: defeitos corrigidos, causa raiz em uma frase por defeito, como investigou/abordou o problema, como validar e resultado do `pytest`.

## Checklist

* [x] O CLI roda com Python 3.11 (`PYTHONPATH=src python -m onfly_report ...`).
* [x] O comando de execução gera `output/report.json` sem erro.
* [x] O relatório segue o contrato acima.
* [x] `pytest -q` passa com os testes fornecidos.
* [x] `entrega/README-ENTREGA.md` preenchido.
* [x] Sessão + declaração apenas no caminho com IA; investigação no README-ENTREGA nos dois caminhos.
* [ ] Repositório público no GitHub com o projeto e o link enviado.

# 🤝 Contribuidores

<a href="https://github.com/BGLuis/onfly-report/graphs/contributors">
  <picture><source media="(prefers-color-scheme: dark)" srcset="https://shieldcn.dev/contributors/BGLuis/onfly-report.svg?title=false&preset=transparent&border=false&mode=dark" /><img alt="Contribuidores" src="https://shieldcn.dev/contributors/BGLuis/onfly-report.svg?title=false&preset=transparent&border=false&mode=light" /></picture>
</a>

# 📄 Licença

Distribuído sob a licença [MIT](LICENSE).
