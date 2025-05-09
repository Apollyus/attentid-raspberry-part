#mqtt spojeni a odesilani
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
import ssl
import numpy as np

auth = {
  'username':"rv-catcher",
  'password':"D6U5ERM7VAIdh7vaCa4fg6Leh"
}

tls = {
  'tls_version':ssl.PROTOCOL_TLSv1_2
}

##Pridame z tridy videoprocesor z cyklostezka
def send_payload(topic, payload):
    print("Send to MQTT.portabo.cz")
    topic="/rv-catcher/"+topic  #mame pravo posilat jen do topicu zacinajiciho /rv-catcher/
    print(topic)
    print(payload)
    data_do_DCUK_all = publish.single(topic, 
            payload = str(payload),
            hostname = "mqtt.portabo.cz",
            client_id = "RomanVaibarHailoCounter",
            auth = auth,
            tls = tls,
            port = 8883,
            protocol = mqtt.MQTTv311)
    print(data_do_DCUK_all)


# Funkce pro konverzi klíčů na int
def convert_keys_to_int(d):
    if isinstance(d, dict):
        return {int(k) if isinstance(k, np.integer) else k: convert_keys_to_int(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [convert_keys_to_int(i) for i in d]
    else:
        return d
