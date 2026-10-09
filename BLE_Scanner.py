#!/usr/bin/env python3
import sys
import argparse
import asyncio
from bleak import BleakScanner
from datetime import datetime
from datetime import timezone

show_all = False
verbose = False
debug = 0
filter_name = None
filter_uuid = None
device_list = {}
last_seen_count = -1
all_seen_counts = []

def print_decoded_data(value):
    """Print the decoded data from the ESP32 device"""
    # uuid = value[0]+(value[1] << 8)
    # Temp (2 bytes, int16, little-endian)

    # temperature = (value[0] + (value[1] << 8))/100.
    temperature = int.from_bytes(value[0:2], 'little', signed=True)/100.
    pressure = int.from_bytes(value[2:4], 'little', signed=False) / 10.0
    humidity = int.from_bytes(value[4:6] , 'little', signed=False) / 100.0
    # Battery ( 1 byte)
    battery = int.from_bytes(value[6:7] , 'little', signed=False) / 2.5

    # count (4 bytes, int32, little-endian)
    count = int.from_bytes(value[7:10], 'little', signed=False)
    timestamp = int.from_bytes(value[10:14], 'little', signed=False)

    utc_time = datetime.fromtimestamp(timestamp)

    print(f"temp: {temperature:.2f}C, humid: {humidity:.2f}%, pres: {pressure:.1f}hPa, "
          f"battery: {battery:.1f}% count: {count}, timestamp: {timestamp} = {utc_time}")


async def scanner():
    stop_event = asyncio.Event()

    def callback(device, advertisement_data):

        global last_seen_count
        global all_seen_counts

        if show_all:
            device_list[device.address] = device
            print("---------------------------------------------------------------------")
            for adress, device in device_list.items():
                if device.name:
                    print(f"{device.name:<20s} -- {adress}")
                else:
                    print(f"{'???':<20s} -- {adress}")
        elif device.address == filter_uuid or device.name == filter_name:
            print(f"\nName: {device.name} -- {device.address}")
            print(f"  RSSI: {advertisement_data.rssi}")
            print(f"  local_name: {advertisement_data.local_name}")
            print(f"  manufacturer_data: {advertisement_data.manufacturer_data}")
            print(f"  service_data: {advertisement_data.service_data}")
            print(f"  service_uuids: {advertisement_data.service_uuids}")
            print(f"  tx_power: {advertisement_data.tx_power}")
            print("----------------------------------------- end -----------------------------")
            if not advertisement_data.service_data:
                print("No service data")
                return
            if not service_data or len(values) < 14:
                return
            values = next(iter(advertisement_data.service_data.values()))
            count = int.from_bytes(values[7:10], 'little', signed=False)
            if count != last_seen_count:
                last_seen_count = count
                all_seen_counts.append(count)
                if verbose or count==0:
                    print(f"Name: {device.name:<20s} -- {device.address}")
                    print("Manufacturer data:", advertisement_data.manufacturer_data)
                for key, value in advertisement_data.service_data.items():
                    if verbose:
                        print("Service data:", key," Value:", value.hex(' '))
                    print_decoded_data(value)

                print("-------------------------")


    async with BleakScanner(callback) as scanner:
        print("Scanning...")
        # Important! Wait for an event to trigger stop, otherwise scanner
        # will stop immediately.
        await stop_event.wait()

    print("End scanning")

    # scanner = BleakScanner(detection_callback)
    # await scanner.start()
    # await asyncio.sleep(10)
    # await scanner.stop()


def main():
    """Main function to run the code."""
    global show_all
    global filter_name
    global filter_uuid
    global verbose
    global debug
    # Parse the arguments
    parser = argparse.ArgumentParser("A simple Bluetooth (LE) scanner.")
    parser.add_argument("--debug", "-d", action="count", help="Increase debug level.", default=0)
    parser.add_argument("--all", "-a", action="store_true", help="Scan and tabulate all found devices.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print more about the device.")
    parser.add_argument("--name", "-n", type=str, help="Only show device with name.", default="ESP32-Sensor")
    parser.add_argument("--uuid", type=str, help="Only show device with UUID.", default=None)

    args = parser.parse_args(sys.argv[1:])
    if args.debug:
        print("Debug flag is set to:", args.debug)
        debug = args.debug

    if args.verbose:
        verbose = True

    if args.all:
        show_all = True

    if args.name:
        filter_name = args.name

    if args.uuid:
        filter_uuid = args.uuid
    else:
        filter_uuid = "14904146-9F2F-7095-F735-AD4316A7929B"

    asyncio.run(scanner())


if __name__ == '__main__':
    main()
