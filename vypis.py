import asyncio
from bleak import BleakScanner
# Předpokládáme, že mqttportabo.py je buď ve stejném adresáři, nebo v PYTHONPATH
from mqttportabo import send_payload # Zkontrolujte umístění mqttportabo.py
import time
import os
from datetime import datetime
import re # Přidán chybějící import re

# Importy z adresáře 'production'
# Aby to fungovalo, adresář 'production' by měl být buď v sys.path,
# nebo by 'production' měl být balíček (obsahovat __init__.py)
# a spouštět vypis.py z kořenového adresáře projektu.
from production.prijimac import uuid_uzivatele # Používá se pro MQTT téma
from production.porovnani import normalize_mac_address, check_if_device_is_nearby

# Slovník známých UUID a jejich typů zařízení
KNOWN_DEVICE_UUIDS = {
    "0000180f-0000-1000-8000-00805f9b34fb": "Battery Service",
    "0000180a-0000-1000-8000-00805f9b34fb": "Device Information",
    "0000fe9f-0000-1000-8000-00805f9b34fb": "Google Fast Pair",
    "0000fd6f-0000-1000-8000-00805f9b34fb": "Windows Device",
    "9fa480e0-4967-4542-9390-d343dc5d04ae": "Apple Device"
}
def is_working_hours():
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

# Načtení UUID Raspberry Pi
folder_path = os.path.join(os.getcwd(), "production", "raspberry_uuid") # Upravená cesta
file_path = os.path.join(folder_path, "uuid.txt")
raspberry_uuid = "unknown_raspberry_uuid" # Defaultní hodnota
if os.path.exists(file_path):
    with open(file_path, "r") as file:
        raspberry_uuid = file.read().strip()
else:
    print(f"Soubor s UUID Raspberry Pi nebyl nalezen: {file_path}")


def get_device_type(uuids):
    device_types = []
    for uuid_str in uuids: # Přejmenováno pro srozumitelnost
        if uuid_str.lower() in KNOWN_DEVICE_UUIDS:
            device_types.append(KNOWN_DEVICE_UUIDS[uuid_str.lower()])
    return device_types if device_types else ["Unknown Device"]

def format_device_data(device):
    uuids = device.metadata.get("uuids", [])
    # Ujistěte se, že manufacturer_data klíče jsou stringy, pokud tak přicházejí z bleak
    raw_manufacturer_data = device.metadata.get("manufacturer_data", {})
    processed_manufacturer_data = {str(k): v.hex() for k, v in raw_manufacturer_data.items()}

    return {
        "name": device.name or "Unknown",
        "mac": device.address,
        "rssi": device.rssi,
        "uuids": uuids,
        "device_types": get_device_type(uuids),
        "manufacturer_data": processed_manufacturer_data,
        "manufacturer_info": get_manufacturer_info(processed_manufacturer_data) # Použijte zpracovaná data
    }

async def scan_and_send():
    while True:
        if not is_working_hours():
            print("⏰ Mimo pracovní dobu (7:00-19:00), čekám...")
            await asyncio.sleep(60)
            continue

        try:
            print("🔍 Spouštím BLE skenování...")
            # Zvýšení timeoutu může pomoci najít více zařízení, ale prodlouží skenování
            devices = await BleakScanner.discover(timeout=10.0) 

            if not devices:
                print("❌ Nenalezena žádná BLE zařízení.")
                await asyncio.sleep(30)
                continue

            print(f"✅ Nalezeno {len(devices)} zařízení")
            
            all_discovered_macs = [d.address for d in devices]

            for device in devices:
                device_data = format_device_data(device)
                payload = {
                    "data": device_data,
                    "timestamp": datetime.now().isoformat() # Přidání časového razítka
                }
                
                device_types = device_data["device_types"]
                print(f"📱 Zařízení {device.address} (RSSI: {device.rssi}) typu: {', '.join(device_types)}")

                # Použití funkce z porovnani.py pro kontrolu, zda je zařízení "ověřené" (tj. v blízkosti)
                # Tato logika je oddělená od GATT ověření.
                # Zde "overenaadresa" znamená, že MAC adresa zařízení byla nalezena v seznamu aktuálně skenovaných zařízení.
                # To není úplně "ověření" ve smyslu identity, spíše potvrzení přítomnosti.
                # Funkce check_if_device_is_nearby nyní vrací boolean.
                
                # Normalizujeme MAC adresu zařízení pro konzistentní formát v MQTT tématu
                normalized_device_mac_for_topic = normalize_mac_address(device.address)

                # Logika pro určení, zda je adresa "ověřená" (tj. nalezena mezi ostatními skenovanými)
                # Tato část byla ve vašem kódu trochu nejasná, `handle_incoming_message` se zdálo být pro toto.
                # Nyní používáme `check_if_device_is_nearby`.
                # `uuid_uzivatele` je zde použito pro identifikaci "uživatele" v MQTT tématu.
                
                # Původní logika byla: if normalized_mac in normalized_nearby_macs:
                # což je přesně to, co dělá check_if_device_is_nearby(device.address, all_discovered_macs)
                
                # Pro jednoduchost, pokud chcete označit zařízení, jehož MAC odpovídá uuid_uzivatele:
                if normalize_mac_address(device.address) == normalize_mac_address(uuid_uzivatele):
                    topic = f"ble_devices/{raspberry_uuid}/{normalized_device_mac_for_topic}/overenaadresa_uzivatele/{uuid_uzivatele}"
                    print(f"✅ Zařízení {device.address} odpovídá uuid_uzivatele. Odesílám na MQTT (uživatel): {topic}")
                # Obecné odeslání pro všechna zařízení
                else:
                    topic = f"ble_devices/{raspberry_uuid}/{normalized_device_mac_for_topic}"
                    print(f"✅ Odesílám zařízení {device.address} na MQTT: {topic}")

                try:
                    send_payload(topic, payload)
                except Exception as e:
                    print(f"❌ Chyba při odesílání dat na MQTT pro {device.address}: {e}")

            await asyncio.sleep(30)

        except Exception as e:
            print(f"❌ Chyba při skenování nebo zpracování: {e}", exc_info=True)
            await asyncio.sleep(10)

if __name__ == "__main__":
    print("🚀 Spouštím BLE monitoring...")
    print(f"🆔 UUID Raspberry Pi: {raspberry_uuid}")
    print(f"👤 UUID Uživatele (pro MQTT a GATT): {uuid_uzivatele}")
    print("⏰ Pracovní doba: 7:00 - 19:00")
    asyncio.run(scan_and_send())