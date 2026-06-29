# MTChart SDK

SDK inicial para desenvolvedores criarem sistemas semelhantes ao MTChart Pro usando classes e metodos reutilizaveis.

Esta primeira versao fica separada do aplicativo desktop e entrega um nucleo limpo para:

- cadastrar processos termicos;
- validar leituras de temperatura;
- calcular previsao de saida;
- registrar catalogo local de pecas e PN;
- montar dados de rastreabilidade sem depender da interface Flet.

## Instalacao local

```powershell
cd sdk
python -m pip install -e .
```

## Repositorio e deploy

O SDK esta preparado para ser publicado como repositorio separado em:

```text
https://github.com/Romero-Softwares/mtchart_sdk
```

Antes de enviar ou publicar, rode:

```powershell
python tools\validate_release.py
python -m build
```

O passo a passo completo esta em `DEPLOY.md`.

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
- `docs/COMMERCIAL_MODEL.md`: sugestao pratica de empacotamento e venda.
- `docs/RELEASE_CHECKLIST.md`: checklist para entregar ou publicar o SDK.

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

## Validacao de release

Antes de vender, entregar ou publicar uma versao:

```powershell
cd sdk
python tools/validate_release.py
```

O validador confere metadados, compila os modulos, roda testes e executa o
exemplo/CLI de demonstracao.

## Modelo comercial sugerido

Use este SDK como nucleo reutilizavel e mantenha recursos avancados em camadas pagas:

- conectores industriais especificos;
- geracao profissional de PDF/Excel;
- dashboard web/cloud;
- suporte e implantacao;
- templates de sistemas prontos para clientes.

Veja tambem `docs/COMMERCIAL_MODEL.md`.

## Status

Versao inicial de criacao. A API esta pronta para testes locais, demonstracao comercial e evolucao incremental.
