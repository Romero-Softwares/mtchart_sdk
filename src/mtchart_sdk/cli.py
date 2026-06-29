from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from mtchart_sdk.models import PartItem, PenConfig, ProcessInput
from mtchart_sdk.service import MTChartService


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mtchart-sdk-demo",
        description="Executa uma demonstracao local do MTChart SDK.",
    )
    parser.add_argument("--catalog-db", default="mtchart_sdk_demo.db", help="Caminho do catalogo SQLite.")
    parser.add_argument("--report-number", default="CH-DEMO-001", help="Numero do relatorio.")
    parser.add_argument("--project", default="OS-DEMO", help="Projeto ou ordem de servico.")
    parser.add_argument("--process-name", default="Alivio de fragilizacao", help="Nome do processo.")
    parser.add_argument("--oven", default="Forno Demo", help="Nome do forno.")
    parser.add_argument("--relief-hours", type=float, default=3.0, help="Horas de permanencia do processo.")
    parser.add_argument("--pen-id", default="1", help="Identificador da pena.")
    parser.add_argument("--target", type=float, default=189.0, help="Temperatura alvo para iniciar processo.")
    parser.add_argument("--low-limit", type=float, default=175.9, help="Limite inferior de temperatura.")
    parser.add_argument("--high-limit", type=float, default=220.0, help="Limite superior de temperatura.")
    parser.add_argument("--value", default="188.7", help="Leitura de temperatura a avaliar.")
    parser.add_argument("--part-name", default="Suporte Demo", help="Nome da peca.")
    parser.add_argument("--pn", default="PN-DEMO-001", help="Part number da peca.")
    parser.add_argument("--sn", default="SN-DEMO-001", help="Serial number da peca.")
    parser.add_argument("--qty", type=int, default=1, help="Quantidade da peca.")
    return parser


def run_demo(args: argparse.Namespace) -> dict[str, object]:
    service = MTChartService(catalog_db=Path(args.catalog_db))
    started_at = datetime.now().replace(microsecond=0)
    process = service.create_process(
        ProcessInput(
            report_number=args.report_number,
            project=args.project,
            process_name=args.process_name,
            oven=args.oven,
            relief_hours=args.relief_hours,
            pen=PenConfig(
                id=args.pen_id,
                name=f"Pena {args.pen_id}",
                stabilization_target=args.target,
                low_limit=args.low_limit,
                high_limit=args.high_limit,
            ),
            items=[
                PartItem(
                    name=args.part_name,
                    pn=args.pn,
                    sn=args.sn,
                    qty=args.qty,
                )
            ],
            started_at=started_at,
        )
    )
    reading = service.evaluate_reading(process, args.value, now=started_at)
    return {
        "report_number": process.report_number,
        "project": process.project,
        "expected_exit_at": process.expected_exit_at.isoformat(),
        "total_quantity": process.total_quantity,
        "reading": {
            "value": reading.value,
            "status": reading.status,
            "can_start_process": reading.can_start_process,
            "remaining_seconds": reading.remaining_seconds,
        },
        "catalog_matches": service.search_parts(args.pn, limit=5),
    }


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    result = run_demo(parser.parse_args(argv))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
