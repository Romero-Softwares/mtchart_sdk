# MTChart SDK

SDK for developers who want to build systems similar to MTChart Pro using reusable classes and methods.

This first version is separate from the desktop application and provides a clean core to:

- register thermal processes;
- validate temperature readings;
- calculate expected exit time;
- register a parts and PN catalog in the backend chosen by the developer;
- build traceability data without depending on the desktop interface;
- calculate output folders by year/month, oven, and file type;
- standardize log names, entry control files, and report numbers.

## Installation

```powershell
python -m pip install mtchart-sdk
```

## Quick Example

```python
from datetime import datetime

from mtchart_sdk import MTChartService, PartItem, PenConfig, ProcessInput

service = MTChartService()

process = service.create_process(
    ProcessInput(
        report_number="CH-0001",
        project="OS-123",
        process_name="Embrittlement relief",
        oven="Oven 01",
        relief_hours=3,
        pen=PenConfig(id="1", name="Pen 1", stabilization_target=189, low_limit=175.9),
        items=[
            PartItem(name="Bracket", pn="PN-001", sn="SN-001", qty=1),
        ],
        started_at=datetime(2026, 6, 28, 8, 0, 0),
    )
)

reading = service.evaluate_reading(process, value=188.7)

print(process.report_number)
print(reading.status)
print(reading.can_start_process)
```

## Structure

- `mtchart_sdk.models`: process data models.
- `mtchart_sdk.rules`: pure temperature and time rules.
- `mtchart_sdk.reports`: report, log, batch, date, and traceability utilities.
- `mtchart_sdk.output_paths`: output folder organization matching MTChart Pro.
- `mtchart_sdk.storage`: catalog contract and default SQLite backend.
- `mtchart_sdk.service`: main facade for use by other systems.
- `mtchart_sdk.cli`: command-line demo to validate installation.
- `examples/basic_process.py`: minimal executable example.

## Main API

- `MTChartService.create_process(data)`: normalizes parts, calculates total quantity, and expected exit time.
- `MTChartService.evaluate_reading(process, value)`: classifies the reading as `OK`, `LOW`, `HIGH`, or `N/A`.
- `MTChartService.search_parts(term)`: searches the local parts catalog by name or PN.
- `MTChartService.build_output_paths(root, reference_date, oven=...)`: calculates LOGS, control, PDF, and chart folders by period.
- `MTChartService.parts_control_path(root, process)`: builds the parts control path using the report number.
- `MTChartService.report_summary(process)`: summarizes items, total quantity, and main report data.
- `clean_identifier(value)`: removes common prefixes such as `PN:`, `P/N:`, `LOTE:`, and `BATCH:`.
- `format_report_number(value)`: replaces `/` with `-` for stable file names.
- `temperature_log_filename(identity)`: generates the Excel log name using report number, PN, and SN.

## Flexible Database

The SDK uses SQLite by default to make the first use simple:

```python
from mtchart_sdk import MTChartService

service = MTChartService(catalog_db="catalog.db")
```

To use PostgreSQL, MySQL, SQL Server, MongoDB, an internal API, or any other storage layer, inject your own backend with `save()` and `search()` methods:

```python
from mtchart_sdk import MTChartService


class MyCatalog:
    def save(self, name: str, pn: str, increment: bool = True) -> None:
        # Store in any database, ORM, or external service.
        ...

    def search(self, term: str = "", limit: int = 100) -> list[dict[str, object]]:
        # Return dictionaries with at least name and pn.
        return []


service = MTChartService(catalog=MyCatalog())
```

This contract keeps MTChart rules independent from the database. SQLite remains available as the default backend, but it is not mandatory for SDK integrations.

## Demo CLI

After installing locally, run:

```powershell
mtchart-sdk-demo --value 188.7
```

Or run it as a script without installing:

```powershell
python -m mtchart_sdk.cli --catalog-db .tmp_demo.db --value 188.7
```

The command creates a sample process, evaluates the reading, and returns JSON with status, expected exit time, and local catalog results.

## Local Validation

To validate a local SDK copy during development:

```powershell
python tools/validate_package.py
```

The validator checks metadata, compiles modules, runs tests, and executes the demo example/CLI.

## Status

Version 0.2.0. The public API follows the latest catalog, traceability, report number, report folder, and log utility updates.
