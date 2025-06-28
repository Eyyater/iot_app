import os
import sqlite3
from datetime import datetime
from huaweicloudsdkcore.auth.credentials import BasicCredentials, DerivedCredentials
from huaweicloudsdkcore.region.region import Region as coreRegion
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkiotda.v5 import *

Project_ID = "91013bc50fd941e68ffb86f478b50c18"
Instance_ID = "368805c9-c87f-4a14-80c2-57398b92cdb0"
Device_ID = "67e53e652902516e866b8487_potato-sensor-test"
App_ID = "c4ac0b5acc504d668506981d54c3f435"
EndPoint = "https://9b0766b4b1.st1.iotda-app.cn-north-4.myhuaweicloud.com"

ak = os.environ["HUAWEICLOUD_SDK_AK"]
sk = os.environ["HUAWEICLOUD_SDK_SK"]

credentials = BasicCredentials(ak, sk, Project_ID).with_derived_predicate(DerivedCredentials.get_default_derived_predicate())
client = IoTDAClient.new_builder() \
    .with_credentials(credentials) \
    .with_region(coreRegion(id="cn-north-4", endpoint=EndPoint)) \
    .build()

def get_shadow(): # 获取最新数据
    try:
        request = ShowDeviceShadowRequest()
        request.device_id = Device_ID
        response = client.show_device_shadow(request)
        return response.to_dict()
    except exceptions.ClientRequestException as e:
        print(f"Error getting shadow: {e}")
        return None

def save_shadow_to_db(data): # 将数据存入数据库
    # 初始化空字典存数据
    record = {
        "timestamp": None,
        "temperature": None,
        "humidity": None,
        "vis_b": None, "vis_g": None, "vis_o": None, "vis_r": None, "vis_v": None, "vis_y": None,
        "nir_r": None, "nir_s": None, "nir_t": None, "nir_u": None, "nir_v": None, "nir_w": None,
        "DW": None, "SC": None,
        "L": None,  "a": None, "b": None,
        "LB": None, "BI": None,
    }

    # 遍历 shadow 数据
    for service in data.get("shadow", []):
        service_id = service.get("service_id")
        props = service.get("reported", {}).get("properties", {})
        ts = service.get("reported", {}).get("event_time")

        if service_id == "TRH":
            record["temperature"] = float(props.get("temperature", 0))
            record["humidity"] = float(props.get("humidity", 0))
            record["timestamp"] = ts or datetime.utcnow().isoformat()

        elif service_id == "VIS":
            record["vis_b"] = float(props.get("B", 0))
            record["vis_g"] = float(props.get("G", 0))
            record["vis_o"] = float(props.get("O", 0))
            record["vis_r"] = float(props.get("R", 0))
            record["vis_v"] = float(props.get("V", 0))
            record["vis_y"] = float(props.get("Y", 0))

        elif service_id == "NIR":
            record["nir_r"] = float(props.get("R", 0))
            record["nir_s"] = float(props.get("S", 0))
            record["nir_t"] = float(props.get("T", 0))
            record["nir_u"] = float(props.get("U", 0))
            record["nir_v"] = float(props.get("V", 0))
            record["nir_w"] = float(props.get("W", 0))

        elif service_id == "DW&SC":
            record["DW"] = float(props.get("DW", 0))
            record["SC"] = float(props.get("SC", 0))

        elif service_id == "Lab":
            record["L"] = float(props.get("L", 0))
            record["a"] = float(props.get("a", 0))
            record["b"] = float(props.get("b", 0))

        elif service_id == "LB&BI":
            record["LB"] = float(props.get("LB", 0))
            record["BI"] = float(props.get("BI", 0))

    # 存入数据库
    conn = sqlite3.connect('sensor_data.db')
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO sensor_data (
            timestamp, temperature, humidity,
            vis_b, vis_g, vis_o, vis_r, vis_v, vis_y,
            nir_r, nir_s, nir_t, nir_u, nir_v, nir_w,
            DW, SC, "L*", "a*", "b*", "L/B", BI
        ) VALUES (?, ?, ?,
                  ?, ?, ?, ?, ?, ?,
                  ?, ?, ?, ?, ?, ?,
                  ?, ?, ?, ?, ?, ?, ?)
    ''', tuple(record.values()))

    conn.commit()
    conn.close()
    print("数据已保存至数据库。")

def get_db_connection(): # 读取数据库
    conn = sqlite3.connect("sensor_data.db")
    conn.row_factory = sqlite3.Row
    return conn

if __name__ == "__main__":
    print(get_shadow())
    data = get_shadow()
    save_shadow_to_db(data)
