import re

def normalize_mac_address(mac_address):
    """Normalizuje MAC adresu do formátu XXXXXXXXXXXX (velká písmena)."""
    if mac_address is None:
        return ""
    return re.sub(r'[^a-fA-F0-9]', '', str(mac_address)).upper()

def verify_device(received_mac_from_gatt_client, user_mac_to_compare):
    """
    Ověří, zda MAC adresa přijatá od GATT klienta odpovídá
    známé MAC adrese uživatele.
    """
    normalized_received_mac = normalize_mac_address(received_mac_from_gatt_client)
    normalized_user_mac = normalize_mac_address(user_mac_to_compare)

    if normalized_received_mac and normalized_user_mac and normalized_received_mac == normalized_user_mac:
        print(f"GATT OVĚŘENÍ ÚSPĚŠNÉ: Zařízení {received_mac_from_gatt_client} (normalizováno: {normalized_received_mac}) odpovídá {user_mac_to_compare} (normalizováno: {normalized_user_mac}).")
        return True
    else:
        print(f"GATT OVĚŘENÍ NEÚSPĚŠNÉ: Zařízení {received_mac_from_gatt_client} (normalizováno: {normalized_received_mac}) neodpovídá {user_mac_to_compare} (normalizováno: {normalized_user_mac}).")
        return False

def check_if_device_is_nearby(mac_address_to_check, list_of_nearby_macs):
    """
    Zkontroluje, zda je daná MAC adresa přítomna v seznamu MAC adres okolních zařízení.
    Používá se ve vypis.py.
    """
    normalized_mac = normalize_mac_address(mac_address_to_check)
    normalized_nearby_macs = [normalize_mac_address(mac) for mac in list_of_nearby_macs]
    
    is_nearby = normalized_mac in normalized_nearby_macs
    if is_nearby:
        print(f"KONTROLA OKOLÍ (pro vypis.py): Zařízení {mac_address_to_check} je v seznamu okolních zařízení.")
    else:
        print(f"KONTROLA OKOLÍ (pro vypis.py): Zařízení {mac_address_to_check} není v seznamu okolních zařízení.")
    return is_nearby