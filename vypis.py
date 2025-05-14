import asyncio
from bleak import BleakScanner
from mqttportabo import send_payload
import time
import os
from datetime import datetime

# Slovník známých UUID a jejich typů zařízení
KNOWN_DEVICE_UUIDS = {
    "0000180f-0000-1000-8000-00805f9b34fb": "Battery Service",
    "0000180a-0000-1000-8000-00805f9b34fb": "Device Information",
    "0000fe9f-0000-1000-8000-00805f9b34fb": "Google Fast Pair",
    "0000fd6f-0000-1000-8000-00805f9b34fb": "Windows Device",
    "9fa480e0-4967-4542-9390-d343dc5d04ae": "Apple Device"
}

def is_working_hours():
    """Kontroluje, zda je čas v pracovní době (7:00 - 19:00)"""
    current_hour = datetime.now().hour
    return 7 <= current_hour < 19

# Removed get_device_type function as it relied on UUIDs

def get_manufacturer_info(manufacturer_data):
    """Zjistí výrobce a typ zařízení z manufacturer_data"""
    manufacturer_info = []
    manufacturer_mapping = {
        76: "Apple",  # Company Identifier Code 0x004C
        6: "Microsoft",  # Company Identifier Code 0x0006
        117: "Samsung",  # Company Identifier Code 0x0075
        224: "Google",  # Company Identifier Code 0x00E0
        89: "Sony",  # Company Identifier Code 0x0059
        15: "Intel",  # Company Identifier Code 0x000F
        2: "IBM",  # Company Identifier Code 0x0002
        48: "Nokia",  # Company Identifier Code 0x0030
        85: "Qualcomm",  # Company Identifier Code 0x0055
        72: "Broadcom",  # Company Identifier Code 0x0048
        112: "Huawei",  # Company Identifier Code 0x0070
        208: "Xiaomi",  # Company Identifier Code 0x00D0
        240: "Oppo",  # Company Identifier Code 0x00F0
        200: "Vivo",  # Company Identifier Code 0x00C8
    }
    for key, value in manufacturer_data.items():
        manufacturer_info.append(manufacturer_mapping.get(key, f"Unknown Manufacturer (ID: {key})"))
    return manufacturer_info

def get_device_type(uuids):
    """Zjistí typ zařízení podle UUID"""
    device_types = []
    for uuid in uuids:
        if uuid.lower() in KNOWN_DEVICE_UUIDS:
            device_types.append(KNOWN_DEVICE_UUIDS[uuid.lower()])
    return device_types if device_types else ["Unknown Device"]

def format_device_data(device):
    """Formátuje data ze zařízení do struktury pro MQTT"""
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
    while True:  # Nekonečná smyčka pro kontinuální skenování
        if not is_working_hours():
            print("⏰ Mimo pracovní dobu (7:00-19:00), čekám...")
            await asyncio.sleep(60)  # Zvýšení intervalu kontroly na 60 sekund
            continue

        try:
            print("🔍 Spouštím BLE skenování...")
            devices = await BleakScanner.discover(timeout=5.0)  # Zkrácení doby skenování na 5 sekund

            if not devices:
                print("❌ Nenalezena žádná BLE zařízení.")
                await asyncio.sleep(60)  # Zvýšení intervalu čekání na 60 sekund
                continue

            print(f"✅ Nalezeno {len(devices)} zařízení")

            for device in devices:
                device_data = format_device_data(device)
                payload = {
                    "data": device_data
                }
                
                # Print device type information
                device_types = device_data["device_types"]
                print(f"📱 Zařízení {device.address} typu: {', '.join(device_types)}")

                try:
                    # Read and display the raspberry UUID
                    folder_path = os.path.join(os.getcwd(), "raspberry_uuid")
                    file_path = os.path.join(folder_path, "uuid.txt")
                    if os.path.exists(file_path):
                        with open(file_path, "r") as file:
                            raspberry_uuid = file.read().strip()
                        print(f"Raspberry UUID: {raspberry_uuid}")
                    else:
                        print("UUID file not found.")

                    send_payload("ble_devices", payload)
                    print(f"📤 Odesláno: {device.address}")
                except Exception as e:
                    print(f"❌ Chyba při odesílání dat: {e}")

            await asyncio.sleep(60)  # Zvýšení intervalu čekání na 60 sekund

        except Exception as e:
            print(f"❌ Chyba při skenování: {e}")
            await asyncio.sleep(5)  # Počkáme před dalším pokusem

if __name__ == "__main__":
    print("🚀 Spouštím BLE monitoring...")
    print("⏰ Pracovní doba: 7:00 - 19:00")
    asyncio.run(scan_and_send())
