# MTChart SDK

SDK inicial para desenvolvedores criarem sistemas semelhantes ao MTChart Pro usando classes e metodos reutilizaveis.

Esta primeira versao fica separada do aplicativo desktop e entrega um nucleo limpo para:

- cadastrar processos termicos;
- validar leituras de temperatura;
- calcular previsao de saida;
- registrar catalogo local de pecas e PN;
- montar dados de rastreabilidade sem depender da interface Flet.

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
- `mtchart_sdk.storage`: catalogo SQLite local de pecas.
- `mtchart_sdk.service`: fachada principal para uso por outros sistemas.
- `mtchart_sdk.cli`: demonstracao de linha de comando para validar instalacao.
- `examples/basic_process.py`: exemplo minimo executavel.

## API principal

- `MTChartService.create_process(data)`: normaliza pecas, calcula quantidade total e previsao de saida.
- `MTChartService.evaluate_reading(process, value)`: classifica leitura como `OK`, `LOW`, `HIGH` ou `N/A`.
- `MTChartService.search_parts(term)`: consulta o catalogo local de pecas por nome ou PN.
- `clean_identifier(value)`: remove prefixos comuns como `PN:`, `P/N:`, `LOTE:` e `BATCH:`.

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

Versao inicial. A API esta pronta para instalacao, testes locais e evolucao incremental.
