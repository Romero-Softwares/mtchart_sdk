from datetime import datetime

from mtchart_sdk import (
    MTChartService,
    PartItem,
    PenConfig,
    ProcessInput,
    ReportIdentity,
    build_output_paths,
    clean_identifier,
    format_datetime_display,
    format_report_number,
    normalize_item,
    parts_control_filename,
    report_summary,
    serial_display_for_mass,
    temperature_log_filename,
    temperature_status,
)
from mtchart_sdk.cli import main, run_demo


class MemoryCatalog:
    def __init__(self):
        self.rows = {}

    def save(self, name: str, pn: str, increment: bool = True) -> None:
        key = (name.upper(), pn.upper())
        current = self.rows.get(key, {"id": len(self.rows) + 1, "name": name, "pn": pn, "use_count": 0})
        current["name"] = name
        current["pn"] = pn
        current["use_count"] += 1 if increment else 0
        self.rows[key] = current

    def search(self, term: str = "", limit: int = 100) -> list[dict[str, object]]:
        term = term.upper()
        matches = [
            row
            for (name_norm, pn_norm), row in self.rows.items()
            if not term or term in name_norm or term in pn_norm
        ]
        return matches[:limit]


def test_create_process_and_evaluate_reading(tmp_path):
    service = MTChartService(catalog_db=tmp_path / "catalog.db")
    process = service.create_process(
        ProcessInput(
            report_number="CH-0001",
            project="OS-1",
            process_name="Alivio",
            oven="Forno 01",
            relief_hours=2,
            pen=PenConfig(id="1", stabilization_target=189, low_limit=175.9, high_limit=220),
            items=[PartItem(name="Peca", pn="PN-1", sn="SN-1", qty=2)],
            started_at=datetime(2026, 6, 28, 8, 0, 0),
        )
    )

    reading = service.evaluate_reading(process, 188.6, now=datetime(2026, 6, 28, 9, 0, 0))

    assert process.total_quantity == 2
    assert process.expected_exit_at == datetime(2026, 6, 28, 10, 0, 0)
    assert reading.status == "OK"
    assert reading.can_start_process is True
    assert service.search_parts("PN-1")[0]["name"] == "Peca"


def test_service_accepts_custom_catalog_backend():
    catalog = MemoryCatalog()
    service = MTChartService(catalog=catalog)

    service.create_process(
        ProcessInput(
            report_number="CH-CUSTOM",
            project="OS-CUSTOM",
            process_name="Teste",
            oven="Forno",
            relief_hours=1,
            pen=PenConfig(id="1"),
            items=[PartItem(name="Base", pn="PN-CUSTOM")],
        )
    )

    assert service.search_parts("custom")[0]["pn"] == "PN-CUSTOM"


def test_service_rejects_two_catalog_sources(tmp_path):
    try:
        MTChartService(catalog_db=tmp_path / "catalog.db", catalog=MemoryCatalog())
    except ValueError as exc:
        assert "catalog or catalog_db" in str(exc)
    else:
        raise AssertionError("Expected ValueError when catalog and catalog_db are both provided")


def test_temperature_statuses_are_classified(tmp_path):
    service = MTChartService(catalog_db=tmp_path / "catalog.db")
    process = service.create_process(
        ProcessInput(
            report_number="CH-0002",
            project="OS-2",
            process_name="Teste",
            oven="Forno 02",
            relief_hours=1,
            pen=PenConfig(id="2", stabilization_target=180, low_limit=170, high_limit=200),
            started_at=datetime(2026, 6, 28, 8, 0, 0),
        )
    )

    assert service.evaluate_reading(process, 169).status == "LOW"
    assert service.evaluate_reading(process, 201).status == "HIGH"
    assert service.evaluate_reading(process, "").status == "N/A"


def test_catalog_reuses_part_and_increments_count(tmp_path):
    service = MTChartService(catalog_db=tmp_path / "catalog.db")
    data = ProcessInput(
        report_number="CH-0003",
        project="OS-3",
        process_name="Teste",
        oven="Forno 03",
        relief_hours=1,
        pen=PenConfig(id="3"),
        items=[
            {"name": "Suporte", "pn": "PN: ABC-1"},
            {"name": "Suporte", "pn": "ABC-1"},
        ],
    )

    service.create_process(data)
    result = service.search_parts("ABC-1")

    assert len(result) == 1
    assert result[0]["use_count"] == 2


def test_normalize_item_accepts_portuguese_keys():
    item = normalize_item({"nome": "Peca", "pn": "P/N: X-1", "projeto": "OS-4", "qty": "3"})

    assert item.name == "Peca"
    assert item.pn == "X-1"
    assert item.project == "OS-4"
    assert item.qty == 3


def test_clean_identifier_removes_common_labels():
    assert clean_identifier("PN: ABC-123") == "ABC-123"
    assert clean_identifier("BATCH: L-1") == "L-1"
    assert clean_identifier("P/N: XPTO") == "XPTO"


def test_cli_demo_returns_process_payload(tmp_path):
    parser_args = [
        "--catalog-db",
        str(tmp_path / "demo.db"),
        "--report-number",
        "CH-CLI",
        "--value",
        "188.7",
        "--pn",
        "PN-CLI",
    ]

    assert main(parser_args) == 0


def test_cli_run_demo_payload_can_be_consumed(tmp_path):
    from mtchart_sdk.cli import _build_parser

    args = _build_parser().parse_args(
        [
            "--catalog-db",
            str(tmp_path / "demo.db"),
            "--report-number",
            "CH-CLI",
            "--value",
            "188.7",
            "--pn",
            "PN-CLI",
        ]
    )
    result = run_demo(args)

    assert result["report_number"] == "CH-CLI"
    assert result["reading"]["status"] == "OK"
    assert result["catalog_matches"][0]["pn"] == "PN-CLI"


def test_report_helpers_match_current_traceability_rules(tmp_path):
    identity = ReportIdentity(report_number="CH/010/26", pn="PN: ABC-1", sn="SN-1", oven="Forno 1")

    assert format_report_number(identity.report_number) == "CH-010-26"
    assert temperature_log_filename(identity) == "Log_CH-010-26_ABC-1_SN-1.xlsx"
    assert parts_control_filename(report_number=identity.report_number, reference_date=datetime(2026, 7, 5)) == (
        "Controle_Pecas_CH-010-26_2026-07-05.xlsx"
    )
    assert format_datetime_display(datetime(2026, 7, 5, 14, 30, 0), "EN") == "2026/07/05 14:30:00"
    assert serial_display_for_mass("MULTIPLO", [{"sn": "SN-1"}]) == "MULTIPLO"
    assert serial_display_for_mass("MULTIPLO", [{"sn": ""}]) == ""
    assert temperature_status(188, 175.9, 220) == ("NORMAL / CONFORME", True)

    paths = build_output_paths(tmp_path, datetime(2026, 7, 5), oven=identity.oven)
    assert paths.period == tmp_path / "2026" / "JULHO"
    assert paths.logs == tmp_path / "2026" / "JULHO" / "LOGS" / "FORNO 1"
    assert paths.charts == tmp_path / "2026" / "JULHO" / "RELATORIOS PDF" / "FORNO 1" / "GRAFICOS HISTORICOS"


def test_service_exposes_report_paths_and_summary(tmp_path):
    service = MTChartService(catalog_db=tmp_path / "catalog.db")
    process = service.create_process(
        ProcessInput(
            report_number="CH/011/26",
            project="OS-11",
            process_name="Teste",
            oven="Forno 3",
            relief_hours=1,
            pen=PenConfig(id="3"),
            items=[PartItem(name="Peca A", pn="PN-A", qty=2), PartItem(name="Peca B", pn="PN-B", qty=1)],
            started_at=datetime(2026, 7, 5, 8, 0, 0),
        )
    )

    path = service.parts_control_path(tmp_path, process)
    summary = service.report_summary(process)

    assert path.name == "Controle_Pecas_CH-011-26_2026-07-05.xlsx"
    assert "FORNO 3" in str(path)
    assert summary["report_number"] == "CH/011/26"
    assert summary["total_quantity"] == 3
    assert report_summary(process.items)["has_multiple_items"] is True
