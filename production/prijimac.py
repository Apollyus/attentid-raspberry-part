import asyncio
from bleak import BleakScanner, BleakClient
import porovnani

def handle_message(device_address, data_string):
    """
    Tato funkce je zavolána, když server přijme data přes GATT Write.
    """
    print(f"--- PRIJIMAC MODUL ---")
    print(f"Přijata zpráva od zařízení: {device_address}")
    print(f"Obsah zprávy (jako string): {data_string}")
    print(f"-----------------------")
    #porovnani.verify_device(device_address, uuid)

async def main():
    """
    Main function to scan for BLE devices and handle incoming messages.
    """
    print("Starting BLE scanner...")
    scanner = BleakScanner()

    def detection_callback(device, advertisement_data):
        """
        Callback function triggered when a BLE device is detected.
        """
        # Assuming the message is in the manufacturer data
        manufacturer_data = advertisement_data.manufacturer_data
        for key, value in manufacturer_data.items():
            try:
                # Decode the 32-bit message
                message = int.from_bytes(value, byteorder='little')
                device_address = device.address
                uuid = message & 0xFFFFFFFF  # Extract UUID from the message
                asyncio.create_task(handle_message(device_address, uuid))
            except Exception as e:
                print(f"Error processing message: {e}")

    scanner.register_detection_callback(detection_callback)

    try:
        await scanner.start()
        print("Scanner started. Listening for messages...")
        await asyncio.sleep(30)  # Run the scanner for 30 seconds
    finally:
        await scanner.stop()
        print("Scanner stopped.")

if __name__ == "__main__":
    asyncio.run(main())