from flask import Flask, jsonify, render_template
from huawei import get_shadow, save_shadow_to_db, get_db_connection
from flask_cors import CORS
import threading
import time
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)  # 跨域支持

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/data") 
def api_data(): 
    """
    返回最新的传感器数据，结构为：
    {
        "temperature": float,
        "humidity": float,
        "vis": List[float],
        "nir": List[float]
    }
    """
    try:
        raw_data = get_shadow()
        shadow_list = raw_data.get("shadow", [])

        temperature = None
        humidity = None
        vis_values = []
        nir_values = []

        for s in shadow_list:
            service_id = s.get("service_id")
            reported = s.get("reported", {})
            props = reported.get("properties", {})

            if service_id == "TRH":
                temperature = float(props.get("temperature", 0.0))
                humidity = float(props.get("humidity", 0.0))

            elif service_id.startswith("VIS"):
                vis_keys = ["V", "B", "G", "Y", "O", "R"]
                for k in vis_keys:
                    if k in props:
                        vis_values.append(float(props[k]))

            elif service_id.startswith("NIR"):
                # 获取 NIR 数据（R, S, T, U, V, W）
                nir_keys = ["R", "S", "T", "U", "V", "W"]
                for k in nir_keys:
                    if k in props:
                        nir_values.append(float(props[k]))

        result = {
            "temperature": temperature,
            "humidity": humidity,
            "vis": vis_values,
            "nir": nir_values
        }

        return jsonify(result)

    except Exception as e:
        print("解析最新数据失败：", e)
        return jsonify({"error": "数据解析失败"}), 500

@app.route("/api/history")
def api_history(): # 打印数据库历史数据（只含温湿度和时间戳）
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 获取当前时间前 1 小时的数据
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        cursor.execute("""
            SELECT timestamp, temperature, humidity
            FROM sensor_data
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        """, (one_hour_ago.isoformat(),))
        rows = cursor.fetchall()

        history = []
        for row in rows:
            history.append({
                "timestamp": row["timestamp"],
                "temperature": row["temperature"],
                "humidity": row["humidity"]
            })

        conn.close()
        return jsonify(history)

    except Exception as e:
        print("获取历史数据失败：", e)
        return jsonify({"error": "无法获取历史数据"}), 500

last_timestamp = None

def poll_data(): # 获取新数据并存入数据库
    global last_timestamp
    while True:
        try:
            data = get_shadow()
            shadow_list = data.get("shadow", [])

            # 获取 TRH 时间戳
            trh = next((s for s in shadow_list if s.get("service_id") == "TRH"), None)
            current_ts = trh.get("reported", {}).get("event_time") if trh else None

            # print(f"当前时间戳: {current_ts} | 上次时间戳: {last_timestamp}")

            if  last_timestamp == None:
                last_timestamp = current_ts
            elif current_ts and current_ts != last_timestamp:
                save_shadow_to_db(data)
                last_timestamp = current_ts
                # print("新数据已保存。")
            # else:
                # print("数据未更新。")

        except Exception as e:
            print("拉取或保存数据时出错：", e)

        time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=poll_data, daemon=True).start()
    app.run(debug=False)
