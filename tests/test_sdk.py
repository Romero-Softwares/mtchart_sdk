from datetime import datetime
import struct

from mtchart_sdk import (
    AuditOperation,
    DriverDependencyError,
    DriverManager,
    MTChartService,
    PartItem,
    PenConfig,
    ProcessInput,
    ReportIdentity,
    build_output_paths,
    clean_identifier,
    export_audit_operations,
    format_audit_log_for_display,
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


class FakeTcpClient:
    def __init__(self, *, registers=None, open_result=True, **kwargs):
        self.kwargs = kwargs
        self.registers = registers or [0]
        self.open_result = open_result
        self.closed = False
        self.writes = []

    def open(self):
        return self.open_result

    def close(self):
        self.closed = True

    def read_holding_registers(self, address, count):
        return self.registers[address : address + count]

    def write_single_register(self, address, value):
        self.writes.append(("single", address, value))
        return True

    def write_multiple_registers(self, address, values):
        self.writes.append(("multiple", address, values))
        return True


class MemoryConfig(dict):
    def get_val(self, *keys):
        value = self
        for key in keys:
            value = value.get(key)
            if value is None:
                return None
        return value

    def set_pena_valor(self, pen_id, key, value):
        for pen in self["penas"]:
            if str(pen["id"]) == str(pen_id):
                pen[key] = value


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


def test_audit_operations_are_recorded_listed_and_filtered(tmp_path):
    service = MTChartService(catalog_db=tmp_path / "catalog.db")

    assert service.has_audit_operations() is False
    first_id = service.record_audit_operation(
        "op-1",
        "REGISTROU_ENTRADA",
        "DASHBOARD",
        "pn=PN-1; inicio_imediato=False",
        occurred_at="2026-07-11 10:30:00",
    )
    service.save_audit_operation(
        AuditOperation(
            operator_id="op-2",
            action="TROCA_ABA",
            tab="CONFIGURACOES",
            details="CONFIGURACOES -> HISTORY",
            occurred_at="2026-07-11 10:31:00",
        )
    )

    logs = service.list_audit_operations(start="2026-07-11 10:30", end="2026-07-11 10:30")

    assert first_id == 1
    assert service.has_audit_operations() is True
    assert len(logs) == 1
    assert logs[0]["matricula"] == "OP-1"
    assert logs[0]["acao"] == "REGISTROU_ENTRADA"


def test_audit_log_formatting_and_export_match_system_updates(tmp_path):
    labels = {
        "audit_logs_title": "Operation logs",
        "audit_export_generated_at": "Generated at",
        "audit_export_total": "Total records",
        "audit_col_datetime": "Date/time",
        "audit_col_operator": "Operator ID",
        "audit_col_tab": "Tab",
        "audit_col_action": "Action",
        "audit_col_details": "Details",
        "audit_action_registrou_entrada": "Registered entry",
        "audit_tab_dashboard": "Dashboard",
        "audit_detail_projeto": "Project",
        "audit_detail_inicio_imediato": "Immediate start",
        "txt_nao": "NO",
    }
    log = {
        "data_hora": "2026-07-11 10:30:00",
        "matricula": "OP-1",
        "aba": "DASHBOARD",
        "acao": "REGISTROU_ENTRADA",
        "detalhes": "projeto=OS-1; inicio_imediato=False",
    }

    formatted = format_audit_log_for_display(log, labels)
    output = export_audit_operations([log], tmp_path / "operation_logs.xlsx", labels)

    assert formatted["aba"] == "Dashboard"
    assert formatted["acao"] == "Registered entry"
    assert formatted["detalhes"] == "Project: OS-1; Immediate start: NO"
    assert output.exists()


def test_driver_manager_connects_to_tcp_with_injected_client():
    created = []

    def factory(**kwargs):
        client = FakeTcpClient(registers=[188], **kwargs)
        created.append(client)
        return client

    driver = DriverManager(
        {
            "hardware": {"metodo_conexao": "TCP", "ip_fieldlogger": "10.0.0.5", "modbus_port": 1502},
            "penas": [],
        },
        tcp_client_factory=factory,
    )

    assert driver.conectar() is True
    assert driver.conectado is True
    assert created[0].kwargs["host"] == "10.0.0.5"
    assert created[0].kwargs["port"] == 1502
    assert driver.ler_registrador_unico(slave_id=1, endereco=0) == 188


def test_driver_manager_reads_int16_and_float32_values():
    raw_float = list(struct.unpack(">HH", struct.pack(">f", 188.75)))
    driver = DriverManager(
        {"hardware": {"metodo_conexao": "TCP"}, "penas": []},
        tcp_client_factory=lambda **kwargs: FakeTcpClient(registers=[65535, *raw_float], **kwargs),
    )

    assert driver.conectar() is True
    assert driver.ler_valor_universal(1, 0, "int16", 0.5) == -0.5
    assert round(driver.ler_valor_universal(1, 1, "float32", 1), 2) == 188.75


def test_driver_manager_captures_configured_pens_and_marks_compensation():
    config = MemoryConfig(
        {
            "hardware": {"metodo_conexao": "TCP"},
            "penas": [
                {
                    "id": "1",
                    "ativa": True,
                    "estabilizado": True,
                    "slave_id": 1,
                    "endereco_modbus": 0,
                    "tipo_dado": "int16",
                    "escala": 1,
                    "limite_queda_compensacao": 190,
                }
            ],
        }
    )
    callbacks = []
    driver = DriverManager(
        config,
        tcp_client_factory=lambda **kwargs: FakeTcpClient(registers=[188], **kwargs),
    )
    driver.callback_compensacao = callbacks.append

    readings, ok = driver.capturar_todas_penas()

    assert ok is True
    assert readings == {"1": 188}
    assert config["penas"][0]["compensacao_aplicada"] is True
    assert callbacks == ["1"]


def test_driver_manager_raises_clear_error_without_hardware_extra(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pyModbusTCP.client":
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    driver = DriverManager({"hardware": {"metodo_conexao": "TCP"}, "penas": []})

    try:
        driver.conectar()
    except DriverDependencyError as exc:
        assert "mtchart-sdk[hardware]" in str(exc)
    else:
        raise AssertionError("Expected DriverDependencyError without optional hardware dependency")
