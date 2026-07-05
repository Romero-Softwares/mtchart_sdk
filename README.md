# MTChart SDK

SDK para desenvolvedores criarem sistemas semelhantes ao MTChart Pro usando classes e metodos reutilizaveis.

Esta primeira versao fica separada do aplicativo desktop e entrega um nucleo limpo para:

- cadastrar processos termicos;
- validar leituras de temperatura;
- calcular previsao de saida;
- registrar catalogo de pecas e PN em backend escolhido pelo desenvolvedor;
- montar dados de rastreabilidade sem depender da interface Flet;
- calcular pastas de saida por ano/mes, forno e tipo de arquivo;
- padronizar nomes de logs, controle de entradas e numeros de relatorio.

## Instalacao

```powershell
python -m pip install mtchart-sdk
```

## Exemplo rapido

```python
from datetime import datetime

from mtchart_sdk import MTChartService, PartItem, PenConfig, ProcessInput

service = MTChartService()

process = service.create_process(
    ProcessInput(
        report_number="CH-0001",
        project="OS-123",
        process_name="Alivio de fragilizacao",
        oven="Forno 01",
        relief_hours=3,
        pen=PenConfig(id="1", name="Pena 1", stabilization_target=189, low_limit=175.9),
        items=[
            PartItem(name="Suporte", pn="PN-001", sn="SN-001", qty=1),
        ],
        started_at=datetime(2026, 6, 28, 8, 0, 0),
    )
)

reading = service.evaluate_reading(process, value=188.7)

print(process.report_number)
print(reading.status)
print(reading.can_start_process)
```

## Estrutura

- `mtchart_sdk.models`: modelos de dados do processo.
- `mtchart_sdk.rules`: regras puras de temperatura e tempo.
- `mtchart_sdk.reports`: utilitarios de relatorio, log, lote, data e rastreabilidade.
- `mtchart_sdk.output_paths`: organizacao de pastas de saida igual ao MTChart Pro.
- `mtchart_sdk.storage`: contrato de catalogo e backend SQLite padrao.
- `mtchart_sdk.service`: fachada principal para uso por outros sistemas.
- `mtchart_sdk.cli`: demonstracao de linha de comando para validar instalacao.
- `examples/basic_process.py`: exemplo minimo executavel.

## API principal

- `MTChartService.create_process(data)`: normaliza pecas, calcula quantidade total e previsao de saida.
- `MTChartService.evaluate_reading(process, value)`: classifica leitura como `OK`, `LOW`, `HIGH` ou `N/A`.
- `MTChartService.search_parts(term)`: consulta o catalogo local de pecas por nome ou PN.
- `MTChartService.build_output_paths(root, reference_date, oven=...)`: calcula LOGS, controle, PDFs e graficos por periodo.
- `MTChartService.parts_control_path(root, process)`: monta o caminho do controle de pecas usando o numero do relatorio.
- `MTChartService.report_summary(process)`: resume itens, quantidade total e dados principais do relatorio.
- `clean_identifier(value)`: remove prefixos comuns como `PN:`, `P/N:`, `LOTE:` e `BATCH:`.
- `format_report_number(value)`: troca `/` por `-` para nomes de arquivo estaveis.
- `temperature_log_filename(identity)`: gera o nome do log Excel por report number, PN e SN.

## Banco de dados flexivel

O SDK usa SQLite por padrao para facilitar o primeiro uso:

```python
from mtchart_sdk import MTChartService

service = MTChartService(catalog_db="catalogo.db")
```

Para usar PostgreSQL, MySQL, SQL Server, MongoDB, uma API interna ou qualquer
outro armazenamento, injete um backend proprio com os metodos `save()` e
`search()`:

```python
from mtchart_sdk import MTChartService


class MeuCatalogo:
    def save(self, name: str, pn: str, increment: bool = True) -> None:
        # Grave em qualquer banco, ORM ou servico externo.
        ...

    def search(self, term: str = "", limit: int = 100) -> list[dict[str, object]]:
        # Retorne dicts com, no minimo, name e pn.
        return []


service = MTChartService(catalog=MeuCatalogo())
```

Esse contrato deixa as regras do MTChart independentes do banco. SQLite continua
disponivel como backend padrao, mas nao e uma obrigacao para quem integra o SDK.

## CLI de demonstracao

Depois de instalar localmente, rode:

```powershell
mtchart-sdk-demo --value 188.7
```

Ou sem instalar como script:

```powershell
python -m mtchart_sdk.cli --catalog-db .tmp_demo.db --value 188.7
```

O comando cria um processo ficticio, avalia a leitura e retorna um JSON com
status, previsao de saida e resultados do catalogo local.

## Validacao local

Para validar uma copia local do SDK durante desenvolvimento:

```powershell
python tools/validate_package.py
```

O validador confere metadados, compila os modulos, roda testes e executa o
exemplo/CLI de demonstracao.

## Status

Versao 0.2.0. A API publica acompanha as atualizacoes recentes de catalogo,
rastreabilidade, report number, pastas de relatorio e utilitarios de log.
