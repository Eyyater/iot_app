# db_init.py
import sqlite3

conn = sqlite3.connect('sensor_data.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    temperature REAL,
    humidity REAL,
    vis_b REAL, vis_g REAL, vis_o REAL, vis_r REAL, vis_v REAL, vis_y REAL,
    nir_r REAL, nir_s REAL, nir_t REAL, nir_u REAL, nir_v REAL, nir_w REAL,
    DW REAL, SC REAL,
    "L*" REAL, "a*" REAL, "b*" REAL,
    "L/B" REAL, BI REAL
)
''')

conn.commit()
conn.close()
print("数据库初始化完成。")
