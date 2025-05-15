#!/usr/bin/python3

import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib
import array
import uuid
import prijimac

# Define UUIDs for service and characteristic
SERVICE_UUID = "A07498CA-AD5B-474E-940D-16F7609C2A69"
CHAR_UUID = "12345678-1234-5678-1234-56789abcdef1"

# Define Base UUID and common path
BLUEZ_SERVICE_NAME = 'org.bluez'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'

LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
LE_ADVERTISEMENT_IFACE = 'org.bluez.LEAdvertisement1'

class Service(dbus.service.Object):
    PATH_BASE = '/org/bluez/example/service'

    def __init__(self, bus, index, uuid, primary):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.uuid = uuid
        self.primary = primary
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_SERVICE_IFACE: {
                'UUID': self.uuid,
                'Primary': self.primary,
                'Characteristics': dbus.Array(
                    self.get_characteristic_paths(),
                    signature='o')
            }
        }

    def get_characteristic_paths(self):
        result = []
        for chrc in self.characteristics:
            result.append(chrc.path)
        return result
    
    def get_characteristics(self):
        return self.characteristics

    def add_characteristic(self, characteristic):
        self.characteristics.append(characteristic)

    @dbus.service.method(dbus.PROPERTIES_IFACE,
                         in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_SERVICE_IFACE:
            raise dbus.exceptions.DBusException(
                'org.bluez.Error.InvalidArguments',
                'GetAll called with invalid interface')
        return self.get_properties()[GATT_SERVICE_IFACE]
    
class Advertisement(dbus.service.Object):
    PATH_BASE = '/org/bluez/example/advertisement'

    def __init__(self, bus, index, advertising_type):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.ad_type = advertising_type
        self.service_uuids = [SERVICE_UUID]  # Add your service UUID here
        self.manufacturer_data = {}
        self.solicit_uuids = []
        self.service_data = {}
        self.local_name = "AttentID Server"  # Set your device name here
        self.include_tx_power = False
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        properties = dict()
        properties['Type'] = self.ad_type
        
        if self.service_uuids:
            properties['ServiceUUIDs'] = dbus.Array(self.service_uuids, signature='s')
        if self.manufacturer_data:
            properties['ManufacturerData'] = dbus.Dictionary(
                self.manufacturer_data, signature='qv')
        if self.solicit_uuids:
            properties['SolicitUUIDs'] = dbus.Array(self.solicit_uuids, signature='s')
        if self.service_data:
            properties['ServiceData'] = dbus.Dictionary(
                self.service_data, signature='sv')
        if self.local_name:
            properties['LocalName'] = dbus.String(self.local_name)
        if self.include_tx_power:
            properties['IncludeTxPower'] = dbus.Boolean(True)

        return {LE_ADVERTISEMENT_IFACE: properties}

    @dbus.service.method(dbus.PROPERTIES_IFACE,
                         in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != LE_ADVERTISEMENT_IFACE:
            raise dbus.exceptions.DBusException(
                'org.bluez.Error.InvalidArguments',
                'GetAll called with invalid interface')
        return self.get_properties()[LE_ADVERTISEMENT_IFACE]

    @dbus.service.method(LE_ADVERTISEMENT_IFACE, in_signature='', out_signature='')
    def Release(self):
        print(f"Advertisement {self.path} released")


class Characteristic(dbus.service.Object):
    def __init__(self, bus, index, uuid, flags, service):
        self.path = service.path + '/char' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.service = service
        self.flags = flags
        self.descriptors = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                'Service': self.service.path,
                'UUID': self.uuid,
                'Flags': self.flags,
                'Descriptors': dbus.Array(
                    self.get_descriptor_paths(),
                    signature='o')
            }
        }

    def get_descriptor_paths(self):
        result = []
        for desc in self.descriptors:
            result.append(desc.path)
        return result
        
    def add_descriptor(self, descriptor):
        self.descriptors.append(descriptor)

    @dbus.service.method(dbus.PROPERTIES_IFACE,
                         in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise dbus.exceptions.DBusException(
                'org.bluez.Error.InvalidArguments',
                'GetAll called with invalid interface')
        return self.get_properties()[GATT_CHRC_IFACE]

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='a{sv}',
                        out_signature='ay')
    def ReadValue(self, options):
        print(f"Reading characteristic... Current value: {self.value}")
        # Make sure to return a proper dbus array of bytes
        return [dbus.Byte(b) for b in self.value]


    @dbus.service.method(GATT_CHRC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        # Convert from dbus array to Python bytearray
        received_bytes = bytearray(value)
        print(f"Value received (bytes): {received_bytes}")
        
        try:
            data_str = ''.join([chr(b) for b in received_bytes])
            print(f"Value as string: {data_str}")
            device_address = options.get('device', 'unknown-device')
            print(f"Device address: {device_address}")
            
            # Pass to prijimac for handling
            prijimac.handle_message(device_address, data_str)
            
            # Store the value for future reads
            self.value = received_bytes
        except Exception as e:
            print(f"Error processing write value: {e}")

class Descriptor(dbus.service.Object):
    def __init__(self, bus, index, uuid, flags, characteristic):
        self.path = characteristic.path + '/desc' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.characteristic = characteristic
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            'org.bluez.GattDescriptor1': {
                'Characteristic': self.characteristic.path,
                'UUID': self.uuid,
                'Flags': self.flags,
            }
        }

    @dbus.service.method('org.bluez.GattDescriptor1',
                        in_signature='a{sv}', out_signature='ay')
    def ReadValue(self, options):
        return [dbus.Byte(0)]

    @dbus.service.method(dbus.PROPERTIES_IFACE,
                         in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != 'org.bluez.GattDescriptor1':
            raise dbus.exceptions.DBusException(
                'org.bluez.Error.InvalidArguments',
                'GetAll called with invalid interface')
        return self.get_properties()['org.bluez.GattDescriptor1']

class CustomService(Service):
    def __init__(self, bus, index):
        Service.__init__(self, bus, index, SERVICE_UUID, True)
        self.add_characteristic(CustomCharacteristic(bus, 0, self))

class CustomCharacteristic(Characteristic):
    def __init__(self, bus, index, service):
        # Add notify flag to make it more visible to scanning apps
        Characteristic.__init__(
            self, bus, index,
            CHAR_UUID,
            ['read', 'write', 'notify'],  # Add notify flag
            service)
        self.value = bytearray(b"AttentID Ready")
        
        # Add a user description descriptor to help discovery
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 1, self, "AttentID Communication Channel"))

class CharacteristicUserDescriptionDescriptor(Descriptor):
    """
    Characteristic User Description descriptor.
    """
    DESCRIPTOR_UUID = '2901'
    DESCRIPTOR_IFACE = 'org.bluez.GattDescriptor1'

    def __init__(self, bus, index, characteristic, description):
        self.path = characteristic.path + '/desc' + str(index)
        self.bus = bus
        self.index = index
        self.characteristic = characteristic
        self.description = description
        Descriptor.__init__(self, bus, index, self.DESCRIPTOR_UUID,
                            ['read'], characteristic)

    def ReadValue(self, options):
        return [dbus.Byte(ord(c)) for c in self.description]

class Application(dbus.service.Object):
    """
    org.bluez.GattApplication1 interface implementation
    """
    def __init__(self, bus):
        self.path = "/org/bluez/example/app0"  # Ensure unique path with proper format
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method("org.bluez.GattApplication1",
                     in_signature='', out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        for service in self.services:
            response[dbus.ObjectPath(service.path)] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[dbus.ObjectPath(chrc.path)] = chrc.get_properties()
        return response

def register_service():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    
    # Check if GATT service exists
    try:
        service_manager = dbus.Interface(
            bus.get_object(BLUEZ_SERVICE_NAME, '/org/bluez/hci0'),
            GATT_MANAGER_IFACE)
        print("Found GATT Manager at /org/bluez/hci0")
        
        # Also get advertising manager
        ad_manager = dbus.Interface(
            bus.get_object(BLUEZ_SERVICE_NAME, '/org/bluez/hci0'),
            LE_ADVERTISING_MANAGER_IFACE)
        print("Found Advertising Manager at /org/bluez/hci0")
        
        # Make the adapter discoverable
        adapter = dbus.Interface(
            bus.get_object(BLUEZ_SERVICE_NAME, '/org/bluez/hci0'),
            'org.bluez.Adapter1')
        adapter_props = dbus.Interface(
            bus.get_object(BLUEZ_SERVICE_NAME, '/org/bluez/hci0'),
            'org.freedesktop.DBus.Properties')
        adapter_props.Set('org.bluez.Adapter1', 'Powered', dbus.Boolean(1))
        adapter_props.Set('org.bluez.Adapter1', 'Discoverable', dbus.Boolean(1))
        print("Adapter is now discoverable")
        
        # Create service and application
        service = CustomService(bus, 0)
        app = Application(bus)
        app.add_service(service)
        
        # Create and register advertisement
        advertisement = Advertisement(bus, 0, 'peripheral')
        
        ad_manager.RegisterAdvertisement(
            advertisement.path, {},
            reply_handler=lambda: print("Advertisement registered"),
            error_handler=lambda error: print(f"Failed to register advertisement: {error}")
        )
        
        # Register application
        service_manager.RegisterApplication(
            app.get_path(), {},
            reply_handler=lambda: print("Service registered"),
            error_handler=lambda error: print(f"Failed to register service: {error} (type: {type(error).__name__})")
        )
        
        print("Service and advertisement registered. Running main loop...")
        mainloop = GLib.MainLoop()
        mainloop.run()
        
    except dbus.exceptions.DBusException as e:
        print(f"Error: {e}")
        print("WARNING: GATT manager or advertising manager not found.")
        print("Make sure experimental features are enabled in /etc/bluetooth/main.conf")
        return

if __name__ == '__main__':
    print("Starting GATT server...")
    register_service()