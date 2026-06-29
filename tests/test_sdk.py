from datetime import datetime

from mtchart_sdk import MTChartService, PartItem, PenConfig, ProcessInput, clean_identifier, normalize_item
from mtchart_sdk.cli import main, run_demo


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
