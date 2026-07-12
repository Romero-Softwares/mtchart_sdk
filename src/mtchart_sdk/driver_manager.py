from __future__ import annotations

import struct
import threading
from collections.abc import Callable, Mapping
from typing import Any, Protocol


class ConfigReader(Protocol):
    def get_val(self, *keys: str) -> Any:
        ...


class DriverDependencyError(RuntimeError):
    """Raised when optional hardware dependencies are not installed."""


class DriverManager:
    """Modbus driver manager compatible with MTChart Pro hardware settings.

    The SDK keeps Modbus libraries optional. Install ``mtchart-sdk[hardware]``
    for real serial/TCP connections, or inject fake client factories in tests.
    """

    def __init__(
        self,
        config_handler: ConfigReader | Mapping[str, Any],
        *,
        serial_client_factory: Callable[..., Any] | None = None,
        tcp_client_factory: Callable[..., Any] | None = None,
        timeout: float = 0.1,
    ) -> None:
        self.config = config_handler
        self.serial_client_factory = serial_client_factory
        self.tcp_client_factory = tcp_client_factory
        self.timeout = timeout
        self.serial_client: Any | None = None
        self.tcp_client: Any | None = None
        self.conectado = False
        self.lock = threading.RLock()

        pens = self._get_config("penas", default=[]) or []
        self.estabilizado = {str(p.get("id")): p.get("estabilizado", False) for p in pens}
        self.compensacao_aplicada = {
            str(p.get("id")): p.get("compensacao_aplicada", False) for p in pens
        }
        self.horas_estabilizacao = {str(p.get("id")): p.get("hora_estabilizacao", 0) for p in pens}
        self.callback_compensacao: Callable[[str], Any] | None = None
        self._hardware_signature = self._current_hardware_signature()

    def sincronizar_configuracao_runtime(self) -> None:
        pens = self._get_config("penas", default=[]) or []
        current_ids = {str(p.get("id")) for p in pens}

        for state in (self.estabilizado, self.compensacao_aplicada, self.horas_estabilizacao):
            for pen_id in list(state.keys()):
                if pen_id not in current_ids:
                    state.pop(pen_id, None)

        for pen in pens:
            pen_id = str(pen.get("id"))
            self.estabilizado.setdefault(pen_id, pen.get("estabilizado", False))
            self.compensacao_aplicada.setdefault(pen_id, pen.get("compensacao_aplicada", False))
            self.horas_estabilizacao.setdefault(pen_id, pen.get("hora_estabilizacao", 0))

        if self.conectado and self._hardware_changed():
            self.conectar()

    def conectar(self) -> bool:
        method = self._get_config("hardware", "metodo_conexao")

        with self.lock:
            try:
                self._close_clients()
                if method == "TCP":
                    ip = self._get_config("hardware", "ip_fieldlogger", default="192.168.0.100")
                    port = int(self._get_config("hardware", "modbus_port", default=502) or 502)
                    factory = self.tcp_client_factory or self._load_tcp_client_factory()
                    self.tcp_client = factory(host=ip, port=port, auto_open=True, timeout=self.timeout)
                    self.conectado = bool(self.tcp_client.open())
                else:
                    com_port = str(self._get_config("hardware", "porta_com", default="") or "").strip()
                    if not com_port or com_port.lower() == "none":
                        self.conectado = False
                        self._hardware_signature = self._current_hardware_signature()
                        return False
                    baud = int(self._get_config("hardware", "baud_rate", default=9600) or 9600)
                    factory = self.serial_client_factory or self._load_serial_client_factory()
                    self.serial_client = factory(
                        port=com_port,
                        baudrate=baud,
                        timeout=self.timeout,
                        stopbits=1,
                        bytesize=8,
                        parity="N",
                    )
                    self.conectado = bool(self.serial_client.connect())

                self._hardware_signature = self._current_hardware_signature()
                return self.conectado
            except DriverDependencyError:
                self.conectado = False
                raise
            except Exception:
                self.conectado = False
                return False

    def ler_valor_universal(
        self,
        slave_id: int,
        endereco: int,
        tipo_dado: str,
        escala: float,
    ) -> float | None:
        with self.lock:
            try:
                count = 2 if tipo_dado in ["float32", "int32"] else 1
                regs = self._read_holding_registers(slave_id, endereco, count)

                if not regs or not isinstance(regs, list) or len(regs) < count:
                    return None

                if tipo_dado == "float32":
                    raw = struct.pack(">HH", regs[0], regs[1])
                    value = struct.unpack(">f", raw)[0]
                elif tipo_dado == "int32":
                    raw = struct.pack(">HH", regs[0], regs[1])
                    value = struct.unpack(">i", raw)[0]
                else:
                    value = regs[0]
                    if value > 32767:
                        value -= 65536

                return value * float(escala or 1)
            except Exception:
                return None

    def escrever_registrador(self, slave_id: int, endereco: int, valor: float | int) -> bool:
        with self.lock:
            try:
                if isinstance(valor, float):
                    payload = list(struct.unpack(">HH", struct.pack(">f", valor)))
                    if self.tcp_client:
                        return bool(self.tcp_client.write_multiple_registers(endereco, payload))
                    result = self.serial_client.write_registers(
                        address=endereco,
                        values=payload,
                        device_id=slave_id,
                    )
                    return not result.isError()

                if self.tcp_client:
                    return bool(self.tcp_client.write_single_register(endereco, int(valor)))
                result = self.serial_client.write_register(
                    address=endereco,
                    value=int(valor),
                    device_id=slave_id,
                )
                return not result.isError()
            except Exception:
                return False

    def ler_registrador_unico(self, slave_id: int, endereco: int) -> int | None:
        with self.lock:
            try:
                regs = self._read_holding_registers(slave_id, endereco, 1)
                return regs[0] if regs else None
            except Exception:
                return None

    def capturar_todas_penas(self) -> tuple[dict[str, float], bool]:
        self.sincronizar_configuracao_runtime()

        if not self.conectado:
            self.conectar()
            if not self.conectado:
                return {}, False

        readings: dict[str, float] = {}
        success = False

        for pen in self._get_config("penas", default=[]) or []:
            pen_id = str(pen.get("id"))
            if not pen.get("ativa", True):
                continue

            value = self.ler_valor_universal(
                int(pen.get("slave_id", 1)),
                int(pen.get("endereco_modbus", 0)),
                str(pen.get("tipo_dado", "int16")),
                float(pen.get("escala", 1.0) or 1.0),
            )

            if value is None:
                continue

            final_value = round(value, 1)
            readings[pen_id] = final_value
            success = True

            limit = self._float_or_none(pen.get("limite_queda_compensacao"))
            if self.estabilizado.get(pen_id) and limit is not None and final_value <= limit:
                if not self.compensacao_aplicada.get(pen_id):
                    self.compensacao_aplicada[pen_id] = True
                    self._set_pen_value(pen_id, "compensacao_aplicada", True)
                    if self.callback_compensacao:
                        self.callback_compensacao(pen_id)

        return readings, success

    def _read_holding_registers(self, slave_id: int, address: int, count: int) -> list[int] | None:
        if self.tcp_client:
            result = self.tcp_client.read_holding_registers(address, count)
            return list(result) if result is not None else None

        result = self.serial_client.read_holding_registers(
            address=address,
            count=count,
            device_id=slave_id,
        )
        if result and not result.isError():
            return list(result.registers)
        return None

    def _close_clients(self) -> None:
        for client in (self.tcp_client, self.serial_client):
            if client:
                client.close()
        self.tcp_client = None
        self.serial_client = None

    def _current_hardware_signature(self) -> tuple[str, str, str, str, str]:
        return (
            str(self._get_config("hardware", "metodo_conexao", default="") or ""),
            str(self._get_config("hardware", "porta_com", default="") or ""),
            str(self._get_config("hardware", "baud_rate", default="") or ""),
            str(self._get_config("hardware", "ip_fieldlogger", default="") or ""),
            str(self._get_config("hardware", "modbus_port", default="") or ""),
        )

    def _hardware_changed(self) -> bool:
        return self._current_hardware_signature() != self._hardware_signature

    def _get_config(self, *keys: str, default: Any = None) -> Any:
        if hasattr(self.config, "get_val"):
            try:
                value = self.config.get_val(*keys)  # type: ignore[attr-defined]
                return default if value is None else value
            except TypeError:
                pass

        value: Any = self.config
        for key in keys:
            if isinstance(value, Mapping):
                value = value.get(key)
            else:
                return default
        return default if value is None else value

    def _set_pen_value(self, pen_id: str, key: str, value: Any) -> None:
        setter = getattr(self.config, "set_pena_valor", None)
        if setter:
            setter(pen_id, key, value)

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        try:
            if value in ("", None):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _load_serial_client_factory() -> Callable[..., Any]:
        try:
            from pymodbus.client import ModbusSerialClient
        except ImportError as exc:
            raise DriverDependencyError(
                "Install mtchart-sdk[hardware] to use serial Modbus connections."
            ) from exc
        return ModbusSerialClient

    @staticmethod
    def _load_tcp_client_factory() -> Callable[..., Any]:
        try:
            from pyModbusTCP.client import ModbusClient
        except ImportError as exc:
            raise DriverDependencyError(
                "Install mtchart-sdk[hardware] to use TCP Modbus connections."
            ) from exc
        return ModbusClient
