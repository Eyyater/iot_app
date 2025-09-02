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

@app.route("/api/data") # 提取数据
def api_data(): 
    """
    返回最新的传感器数据，结构为：
    {
        "temperature": float,
        "humidity": float,
        "vis": List[float],
        "nir": List[float],
        "DW": float,
        "SC": float,
        "L": float,
        "a": float,
        "b": float,
        "LB": float,
        "BI": float
    }
    """
    try:
        raw_data = get_shadow()
        shadow_list = raw_data.get("shadow", [])

        temperature = None
        humidity = None
        DW = None
        SC = None
        L = None
        a = None
        b = None
        LB = None
        BI = None
        vis_values = []
        nir_values = []

        for s in shadow_list:
            service_id = s.get("service_id")
            reported = s.get("reported", {})
            props = reported.get("properties", {})

            if service_id == "TRH":
                temperature = float(props.get("temperature", 0.0))
                humidity = float(props.get("humidity", 0.0))
            
            elif service_id == "DW&SC":
                DW = float(props.get("DW", 0.0))
                SC = float(props.get("SC", 0.0))

            elif service_id == "Lab":
                L = float(props.get("L", 0.0))
                a = float(props.get("a", 0.0))
                b = float(props.get("b", 0.0))

            elif service_id == "LB&BI":
                LB = float(props.get("LB", 0.0))
                BI = float(props.get("BI", 0.0))

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
            "nir": nir_values,
            "DW": DW,
            "SC": SC,
            "L": L,
            "a": a,
            "b": b,
            "LB": LB,
            "BI": BI
        }

        return jsonify(result)

    except Exception as e:
        print("解析最新数据失败：", e)
        return jsonify({"error": "数据解析失败"}), 500

from datetime import datetime, timedelta

@app.route("/api/history")
def api_history():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 先多取一些（例如取最近 50 条），以便筛选出间隔大的
        cursor.execute("""
            SELECT timestamp, "L/B", BI, id
            FROM sensor_data
            ORDER BY timestamp DESC
            LIMIT 50
        """)
        rows = cursor.fetchall()

        filtered = []
        last_time = None

        for row in rows:
            ts_str = row["timestamp"]
            
            # 兼容时间格式："20250705T011804Z"
            ts = datetime.strptime(ts_str, "%Y%m%dT%H%M%SZ")

            if last_time is None or (last_time - ts) >= timedelta(minutes=1):
                filtered.append({
                    "timestamp": ts_str,
                    "LB": row["L/B"],
                    "BI": row["BI"],
                    "id": row["id"]
                })
                last_time = ts

            if len(filtered) >= 10:
                break

        # 反转结果：从早到晚返回（前端好画图）
        filtered.reverse()

        conn.close()
        return jsonify(filtered)

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
