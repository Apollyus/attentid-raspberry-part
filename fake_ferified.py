#!/usr/bin/env python3

import asyncio
from bleak import BleakScanner
from mqttportabo import send_payload
import os
from datetime import datetime

# Hardcoded UUIDs
FAKE_USER_UUID = "us-a712b43f-65ab-4e72-b1ca-7de98301d274"
FAKE_VERIFIED_MAC = "11:22:33:44:55:66"  # This MAC will be treated as verified

# Raspberry UUID handling
def get_raspberry_uuid():
    try:
        folder_path = os.path.join(os.getcwd(), "raspberry_uuid")
        file_path = os.path.join(folder_path, "uuid.txt")
        if os.path.exists(file_path):
            with open(file_path, "r") as file:
                return file.read().strip()
        else:
            return "default-raspberry-uuid-1234"
    except Exception as e:
        print(f"Error reading Raspberry UUID: {e}")
        return "default-raspberry-uuid-1234"

# Helper functions
def is_working_hours():
    """Checks if current time is within working hours (7:00 - 19:00)"""
    current_hour = datetime.now().hour
    return 7 <= current_hour < 19

def normalize_mac(mac_address):
    """Normalize MAC address to uppercase with colons."""
    if not mac_address:
        return None
    return mac_address.upper().replace("-", ":")

# Device type detection
KNOWN_DEVICE_UUIDS = {
    "0000180f-0000-1000-8000-00805f9b34fb": "Battery Service",
    "0000180a-0000-1000-8000-00805f9b34fb": "Device Information",
    "0000fe9f-0000-1000-8000-00805f9b34fb": "Google Fast Pair",
    "0000fd6f-0000-1000-8000-00805f9b34fb": "Windows Device",
    "9fa480e0-4967-4542-9390-d343dc5d04ae": "Apple Device"
}

def get_device_type(uuids):
    """Determines device type based on UUIDs"""
    device_types = []
    for uuid in uuids:
        if uuid.lower() in KNOWN_DEVICE_UUIDS:
            device_types.append(KNOWN_DEVICE_UUIDS[uuid.lower()])
    return device_types if device_types else ["Unknown Device"]

def get_manufacturer_info(manufacturer_data):
    """Identifies manufacturer and device type from manufacturer_data"""
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
    """Formats device data into structure for MQTT"""
    uuids = device.metadata.get("uuids", [])
    return {
        "name": device.name or "Unknown",
        "mac": device.address,
        "rssi": device.rssi,
        "uuids": uuids,
        "device_types": get_device_type(uuids),
        "manufacturer_data": {
            str(k): v.hex() for k, v in device.metadata.get("manufacturer_data", {}).items()
        },
        "manufacturer_info": get_manufacturer_info(device.metadata.get("manufacturer_data", {}))
    }

async def scan_and_send():
    # Get or set Raspberry UUID
    raspberry_uuid = get_raspberry_uuid()
    print(f"🆔 Using Raspberry UUID: {raspberry_uuid}")
    print(f"👤 Using Fake User UUID: {FAKE_USER_UUID}")
    print(f"✓ Verified device MAC: {FAKE_VERIFIED_MAC}")
    
    while True:
        # Uncomment this block if you want to respect working hours
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

            for device in devices:
                device_data = format_device_data(device)
                payload = {
                    "data": device_data,
                    "timestamp": datetime.now().isoformat()
                }
                
                device_types = device_data["device_types"]
                print(f"📱 Device {device.address} (RSSI: {device.rssi}) type: {', '.join(device_types)}")

                # Normalize MAC for topic
                normalized_device_mac = normalize_mac(device.address)
                
                # Always add our fake verified user to the device list
                if device.address == FAKE_VERIFIED_MAC or device.address.replace("-", ":") == FAKE_VERIFIED_MAC:
                    topic = f"ble_devices/{raspberry_uuid}/{normalized_device_mac}/overenaadresa_uzivatele/{FAKE_USER_UUID}"
                    print(f"✅ Device {device.address} is our fake verified user. Sending to MQTT: {topic}")
                else:
                    topic = f"ble_devices/{raspberry_uuid}/{normalized_device_mac}"
                    print(f"✅ Sending device {device.address} to MQTT: {topic}")

                try:
                    send_payload(topic, payload)
                except Exception as e:
                    print(f"❌ Error sending data to MQTT for {device.address}: {e}")

            # Add the fake verified device if not already in the list
            if not any(normalize_mac(d.address) == normalize_mac(FAKE_VERIFIED_MAC) for d in devices):
                print(f"➕ Adding fake verified device {FAKE_VERIFIED_MAC}")
                fake_topic = f"ble_devices/{raspberry_uuid}/{normalize_mac(FAKE_VERIFIED_MAC)}/overenaadresa_uzivatele/{FAKE_USER_UUID}"
                fake_payload = {
                    "data": {
                        "name": "Fake Verified Device",
                        "mac": FAKE_VERIFIED_MAC,
                        "rssi": -65,
                        "uuids": [],
                        "device_types": ["Simulated Device"],
                        "manufacturer_data": {},
                        "manufacturer_info": ["Simulated Manufacturer"]
                    },
                    "timestamp": datetime.now().isoformat()
                }
                try:
                    send_payload(fake_topic, fake_payload)
                    print(f"✅ Sent fake verified device to MQTT: {fake_topic}")
                except Exception as e:
                    print(f"❌ Error sending fake verified device: {e}")

            await asyncio.sleep(30)

        except Exception as e:
            print(f"❌ Error during scanning or processing: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    print("🚀 Starting BLE monitoring with fake verified user...")
    print("🔑 Working with hardcoded user UUID")
    asyncio.run(scan_and_send())