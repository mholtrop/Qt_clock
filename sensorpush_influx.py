#!/usr/bin/env python3
"""
Read one or more SensorPush HTP.xw sensors over BLE (BlueZ, via bleak)
and write temperature/humidity/pressure/battery to InfluxDB as line protocol.

Protocol reference: https://www.sensorpush.com/bluetooth-api

Usage:
    python3 sensorpush_influx.py \
        --sensor "AA:BB:CC:DD:EE:FF=cabin" \
        --sensor "11:22:33:44:55:66=engine_room" \
        --influx-url http://localhost:8086 \
        --influx-db boat \
        --interval 60

Requires: bleak, requests
    pip install bleak requests
"""

import os
import argparse
import asyncio
import logging
import struct
import time

from bleak import BleakClient
from bleak.exc import BleakError
import requests

SERVICE_UUID = "ef090000-11d6-42ba-93b8-9dd7ec090ab0"
CHAR_TEMP = "ef090080-11d6-42ba-93b8-9dd7ec090aa9"      # also populates humidity
CHAR_HUMIDITY = "ef090081-11d6-42ba-93b8-9dd7ec090aa9"
CHAR_PRESSURE = "ef090082-11d6-42ba-93b8-9dd7ec090aa9"
CHAR_BATTERY = "ef090007-11d6-42ba-93b8-9dd7ec090aa9"

TRIGGER = bytearray([0x01, 0x00, 0x00, 0x00])
READ_SETTLE_S = 0.2  # datasheet says <100ms; margin for BLE latency

log = logging.getLogger("sensorpush")


async def read_sensor(address: str, timeout: float = 15.0) -> dict:
    """Connect to one sensor and return its current readings."""
    async with BleakClient(address, timeout=timeout) as client:
        # Trigger temperature read; this also refreshes humidity.
        await client.write_gatt_char(CHAR_TEMP, TRIGGER, response=True)
        await asyncio.sleep(READ_SETTLE_S)
        temp_raw = await client.read_gatt_char(CHAR_TEMP)
        humidity_raw = await client.read_gatt_char(CHAR_HUMIDITY)

        # Pressure needs its own trigger.
        await client.write_gatt_char(CHAR_PRESSURE, TRIGGER, response=True)
        await asyncio.sleep(READ_SETTLE_S)
        pressure_raw = await client.read_gatt_char(CHAR_PRESSURE)

        battery_raw = await client.read_gatt_char(CHAR_BATTERY)

        temp_c = struct.unpack("<i", temp_raw)[0] / 100.0
        humidity_pct = struct.unpack("<i", humidity_raw)[0] / 100.0
        pressure_pa = struct.unpack("<i", pressure_raw)[0] / 100.0
        batt_mv, batt_temp_c = struct.unpack("<hh", battery_raw)

        return {
            "temp_c": temp_c,
            "humidity_pct": humidity_pct,
            "pressure_pa": pressure_pa,
            "battery_mv": batt_mv,
        }


def to_line_protocol(measurement: str, tags: dict, fields: dict, ts_ns: int) -> str:
    tag_str = ",".join(f"{k}={v}" for k, v in tags.items())
    field_str = ",".join(
        f"{k}={v}" if isinstance(v, (int, float)) else f'{k}="{v}"'
        for k, v in fields.items()
    )
    prefix = f"{measurement},{tag_str}" if tag_str else measurement
    return f"{prefix} {field_str} {ts_ns}"


def write_to_influx(url: str, bucket: str, org: str, token: str, line: str, timeout: float = 5.0):
    resp = requests.post(
        f"{url}/api/v2/write",
        params={"bucket": bucket, "org": org, "precision": "ns"},
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": "text/plain; charset=utf-8",
        },
        data=line.encode("utf-8"),
        timeout=timeout,
    )
    resp.raise_for_status()


async def poll_once(sensors: dict, influx_url: str, influx_db: str, influx_org: str, influx_token: str):
    for address, name in sensors.items():
        try:
            data = await read_sensor(address)
        except (BleakError, asyncio.TimeoutError, EOFError, OSError) as exc:
            log.warning("failed to read %s (%s): %s", name, address, exc)
            continue

        print("Got data:", data)

        ts_ns = time.time_ns()
        line = to_line_protocol(
            "sensorpush",
            tags={"sensor": name},
            fields={
                "temp_c": data["temp_c"],
                "humidity_pct": data["humidity_pct"],
                "pressure_pa": data["pressure_pa"],
                "battery_mv": data["battery_mv"],
            },
            ts_ns=ts_ns,
        )
        try:
            write_to_influx(influx_url, influx_db, influx_org, influx_token, line)
        except requests.RequestException as exc:
            log.warning("failed to write to influx for %s: %s", name, exc)
            continue

        log.info(
            "%-15s temp=%.2fC rh=%.1f%% p=%.0fPa batt=%dmV",
            name,
            data["temp_c"],
            data["humidity_pct"],
            data["pressure_pa"],
            data["battery_mv"],
        )


async def main_loop(sensors: dict, influx_url: str, influx_db: str, influx_org: str, influx_token: str, interval: float):
    while True:
        start = time.monotonic()
        await poll_once(sensors, influx_url, influx_db, influx_org, influx_token)
        elapsed = time.monotonic() - start
        await asyncio.sleep(max(0.0, interval - elapsed))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sensor", action="append", required=True, metavar="MAC=name",
        help="Sensor MAC address and friendly tag name. Repeatable.",
    )
    parser.add_argument("--influx-url", default="http://localhost:8086")
    parser.add_argument("--influx-db", default="Sensors", help="InfluxDB v2 bucket name")
    parser.add_argument("--influx-org", default="Skog", help="InfluxDB v2 organization name")
    parser.add_argument("--influx-token", default=os.environ.get("INFLUX_TOKEN"),
                        help="InfluxDB v2 API token (or set INFLUX_TOKEN env var)")
    parser.add_argument("--interval", type=float, default=60.0, help="seconds between polls")
    parser.add_argument("--once", action="store_true", help="poll once and exit")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    sensors = dict(parse_sensor_arg(s) for s in args.sensor)

    if args.once:
        asyncio.run(poll_once(sensors, args.influx_url, args.influx_db, args.influx_org, args.influx_token))
    else:
        asyncio.run(main_loop(sensors, args.influx_url, args.influx_db, args.influx_org, args.influx_token, args.interval))


def parse_sensor_arg(value: str) -> tuple:
    address, _, name = value.partition("=")
    return address.strip(), (name.strip() or address.strip())




if __name__ == "__main__":
    main()
