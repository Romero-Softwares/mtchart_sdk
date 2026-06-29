from datetime import datetime

from mtchart_sdk import MTChartService, PartItem, PenConfig, ProcessInput


service = MTChartService(catalog_db="example_catalog.db")

process = service.create_process(
    ProcessInput(
        report_number="CH-0001",
        project="OS-123",
        process_name="Alivio de fragilizacao",
        oven="Forno 01",
        relief_hours=3,
        pen=PenConfig(id="1", name="Pena 1", stabilization_target=189, low_limit=175.9, high_limit=220),
        items=[PartItem(name="Suporte", pn="PN-001", sn="SN-001", qty=1)],
        started_at=datetime(2026, 6, 28, 8, 0, 0),
    )
)

reading = service.evaluate_reading(process, 188.7, now=datetime(2026, 6, 28, 9, 0, 0))

print(process)
print(reading)
print(service.search_parts("PN-001"))
