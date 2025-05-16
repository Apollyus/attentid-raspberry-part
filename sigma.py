#!/usr/bin/env python3

import asyncio
from bleak import BleakScanner
from mqttportabo import send_payload
import time
import os
from datetime import datetime

# Hardcode a test UUID or read from file
def get_uuid():
    try:
        with open("production/uuid.txt", "r") as file:
            return file.read().strip()
    except FileNotFoundError:
        return "test-uuid-1234-5678-90ab"

# Generate or read raspberry UUID
def get_raspberry_uuid():
    try:
        folder_path = os.path.join(os.getcwd(), "production", "raspberry_uuid")
        file_path = os.path.join(folder_path, "uuid.txt")
        if os.path.exists(file_path):
            with open(file_path, "r") as file:
                return file.read().strip()
        else:
            return "test-raspberry-uuid-1234"
    except Exception as e:
        print(f"Error reading Raspberry UUID: {e}")
        return "test-raspberry-uuid-1234"

# Helper functions
def normalize_mac_address(mac_address):
    """Normalize MAC address to uppercase with colons."""
    if not mac_address:
        return None
    return mac_address.upper().replace("-", ":")

def is_working_hours():
    current_hour = datetime.now().hour
    return 7 <= current_hour < 19

# Device type detection
KNOWN_DEVICE_UUIDS = {
    "0000180f-0000-1000-8000-00805f9b34fb": "Battery Service",
    "0000180a-0000-1000-8000-00805f9b34fb": "Device Information",
    "0000fe9f-0000-1000-8000-00805f9b34fb": "Google Fast Pair",
    "0000fd6f-0000-1000-8000-00805f9b34fb": "Windows Device",
    "9fa480e0-4967-4542-9390-d343dc5d04ae": "Apple Device"
}

def get_device_type(uuids):
    device_types = []
    for uuid_str in uuids:
        uuid_lower = uuid_str.lower()
        if uuid_lower in KNOWN_DEVICE_UUIDS:
            device_types.append(KNOWN_DEVICE_UUIDS[uuid_lower])
    return device_types if device_types else ["Unknown Device"]

def get_manufacturer_info(manufacturer_data):
    """Zjistí výrobce a typ zařízení z manufacturer_data"""
    manufacturer_info = []
    manufacturer_mapping = {
        76: "Apple",
        6: "Microsoft",
        117: "Samsung",
        224: "Google",
        89: "Sony",
        15: "Intel",
        2: "IBM",
        48: "Nokia",
        85: "Qualcomm",
        72: "Broadcom",
        112: "Huawei",
        208: "Xiaomi",
        240: "Oppo",
        200: "Vivo",
    }
    for key, value in manufacturer_data.items():
        manufacturer_info.append(manufacturer_mapping.get(key, f"Unknown Manufacturer (ID: {key})"))
    return manufacturer_info

def format_device_data(device):
    uuids = device.metadata.get("uuids", [])
    raw_manufacturer_data = device.metadata.get("manufacturer_data", {})
    processed_manufacturer_data = {str(k): v.hex() for k, v in raw_manufacturer_data.items()}

    return {
        "name": device.name or "Unknown",
        "mac": device.address,
        "rssi": device.rssi,
        "uuids": uuids,
        "device_types": get_device_type(uuids),
        "manufacturer_data": processed_manufacturer_data,
        "manufacturer_info": get_manufacturer_info(processed_manufacturer_data)
    }

async def scan_and_send():
    # Get UUIDs
    uuid_uzivatele = get_uuid()
    raspberry_uuid = get_raspberry_uuid()
    
    print(f"🆔 Using Raspberry UUID: {raspberry_uuid}")
    print(f"👤 Using User UUID: {uuid_uzivatele}")

    while True:
        '''
        if not is_working_hours():
            print("⏰ Outside working hours (7:00-19:00), waiting...")
            await asyncio.sleep(60)
            continue
'''
        try:
            print("🔍 Starting BLE scanning...")
            devices = await BleakScanner.discover(timeout=10.0)

            if not devices:
                print("❌ No BLE devices found.")
                await asyncio.sleep(30)
                continue
            
            # Limit to 5 devices only
            devices = devices[:5]
            print(f"✅ Found 5 devices")
            
            all_discovered_macs = [d.address for d in devices]

            for device in devices:
                device_data = format_device_data(device)
                payload = {
                    "data": device_data,
                    "timestamp": datetime.now().isoformat()
                }
                
                device_types = device_data["device_types"]
                print(f"📱 Device {device.address} (RSSI: {device.rssi}) type: {', '.join(device_types)}")

                # Normalize MAC for topic
                normalized_device_mac_for_topic = normalize_mac_address(device.address)

                # Determine topic based on device MAC
                if normalize_mac_address(device.address) == normalize_mac_address(uuid_uzivatele):
                    topic = f"ble_devices/{raspberry_uuid}/{normalized_device_mac_for_topic}/overenaadresa_uzivatele/{uuid_uzivatele}"
                    print(f"✅ Device {device.address} matches uuid_uzivatele. Sending to MQTT (user): {topic}")
                else:
                    topic = f"ble_devices/{raspberry_uuid}/{normalized_device_mac_for_topic}"
                    print(f"✅ Sending device {device.address} to MQTT: {topic}")

                try:
                    send_payload(topic, payload)
                except Exception as e:
                    print(f"❌ Error sending data to MQTT for {device.address}: {e}")

            await asyncio.sleep(30)

        except Exception as e:
            print(f"❌ Error during scanning or processing: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    print("🚀 Starting BLE monitoring test...")
    print("⏰ Working hours: 7:00 - 19:00")
    asyncio.run(scan_and_send())