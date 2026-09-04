from __future__ import annotations

import configparser
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


class ValidationError(ValueError):
    """Erro de validação de parâmetros fornecidos pelo usuário."""


@dataclass(frozen=True)
class SimulationConfig:
    node_count: int = 10
    area_m: float = 1000.0
    activation_min_s: float = 0.0
    activation_max_s: float = 3600.0
    simulation_time_s: float = 14400.0
    seed: int = 1
    initial_message_interval_s: float = 300.0
    max_hops: int = 8
    max_retries: int = 2
    payload_bytes: int = 24
    output_dir: Path = Path("runs")
    radio_range_m: float = 450.0
    spreading_factor_min: int = 7
    spreading_factor_max: int = 12
    bandwidth_hz: int = 125_000
    tx_power_dbm: float = 14.0
    au915_uplink_base_hz: int = 915_200_000
    au915_uplink_channels: int = 64

    def __post_init__(self) -> None:
        integer_fields = {
            "node_count": self.node_count,
            "seed": self.seed,
            "max_hops": self.max_hops,
            "max_retries": self.max_retries,
            "payload_bytes": self.payload_bytes,
            "spreading_factor_min": self.spreading_factor_min,
            "spreading_factor_max": self.spreading_factor_max,
            "bandwidth_hz": self.bandwidth_hz,
            "au915_uplink_channels": self.au915_uplink_channels,
        }
        for name, value in integer_fields.items():
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValidationError(f"{name} deve ser um inteiro")

        numeric_fields = {
            "area_m": self.area_m,
            "activation_min_s": self.activation_min_s,
            "activation_max_s": self.activation_max_s,
            "simulation_time_s": self.simulation_time_s,
            "initial_message_interval_s": self.initial_message_interval_s,
            "radio_range_m": self.radio_range_m,
            "tx_power_dbm": self.tx_power_dbm,
        }
        for name, value in numeric_fields.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValidationError(f"{name} deve ser numérico")
            if not math.isfinite(float(value)):
                raise ValidationError(f"{name} deve ser finito")

        if self.node_count < 1:
            raise ValidationError("a quantidade de nodos deve ser no mínimo 1")
        if self.area_m <= 0:
            raise ValidationError("o lado da área deve ser maior que zero")
        if self.activation_min_s < 0 or self.activation_max_s < 0:
            raise ValidationError("o intervalo de ativação não pode ser negativo")
        if self.activation_min_s > self.activation_max_s:
            raise ValidationError("a ativação mínima não pode superar a máxima")
        if self.activation_max_s > self.simulation_time_s:
            raise ValidationError(
                "a ativação máxima não pode superar o tempo da simulação"
            )
        if self.simulation_time_s <= 0:
            raise ValidationError("o tempo simulado deve ser maior que zero")
        if self.initial_message_interval_s <= 0:
            raise ValidationError("o intervalo de mensagens deve ser maior que zero")
        if self.max_hops < 1 or self.max_retries < 0 or self.payload_bytes < 0:
            raise ValidationError("TTL, retransmissões e payload têm valores inválidos")
        if self.radio_range_m <= 0:
            raise ValidationError("o alcance do rádio deve ser maior que zero")
        if not 7 <= self.spreading_factor_min <= self.spreading_factor_max <= 12:
            raise ValidationError("os fatores de espalhamento devem estar entre SF7 e SF12")
        if self.bandwidth_hz <= 0 or self.au915_uplink_channels < 1:
            raise ValidationError("a configuração AU915 tem valores inválidos")

    def to_dict(self) -> dict[str, Any]:
        values = asdict(self)
        values["output_dir"] = str(self.output_dir)
        return values

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def write_ini(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str
        parser["General"] = {
            "network": "LoRaMesh",
            "sim-time-limit": f"{self.simulation_time_s:g}s",
            "seed-set": str(self.seed),
        }
        parser["Config Mesh"] = {
            "*.simulation.numNodes": str(self.node_count),
            "*.simulation.areaSize": f"{self.area_m:g}m",
            "*.simulation.activationMin": f"{self.activation_min_s:g}s",
            "*.simulation.activationMax": f"{self.activation_max_s:g}s",
            "*.simulation.initialMessageInterval": f"{self.initial_message_interval_s:g}s",
            "*.simulation.maxHops": str(self.max_hops),
            "*.simulation.maxRetries": str(self.max_retries),
            "*.simulation.payloadBytes": str(self.payload_bytes),
            "*.simulation.radioRange": f"{self.radio_range_m:g}m",
            "*.simulation.bandwidth": str(self.bandwidth_hz),
            "*.simulation.txPower": f"{self.tx_power_dbm:g}",
            "*.simulation.spreadingFactorMin": str(self.spreading_factor_min),
            "*.simulation.spreadingFactorMax": str(self.spreading_factor_max),
            "*.simulation.au915UplinkBase": str(self.au915_uplink_base_hz),
            "*.simulation.au915UplinkChannels": str(self.au915_uplink_channels),
            "*.simulation.outputDir": json.dumps(str(Path(self.output_dir).resolve())),
        }
        with path.open("w", encoding="utf-8") as stream:
            parser.write(stream)
