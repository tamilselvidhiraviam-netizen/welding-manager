import streamlit as st
import pandas as pd
import sqlite3
import io
from datetime import datetime

1. DATABASE SETUP
def init_db():
conn = sqlite3.connect('welding_qms_pro.db', check_same_thread=False)
c = conn.cursor()
c.executescript('''
CREATE TABLE IF NOT EXISTS areas (
area_id INTEGER PRIMARY KEY AUTOINCREMENT,
area_name TEXT UNIQUE,
client_name TEXT,
contractor_name TEXT,
location TEXT
);
CREATE TABLE IF NOT EXISTS wps_master (wps_no TEXT PRIMARY KEY, process TEXT);
CREATE TABLE IF NOT EXISTS welders (
welder_id TEXT PRIMARY KEY,
name TEXT,
qualified_wps TEXT,
last_weld_date DATE
);
CREATE TABLE IF NOT EXISTS joints (
id INTEGER PRIMARY KEY AUTOINCREMENT,
area_name TEXT, line_no TEXT, tag_no TEXT, drawing_no TEXT,
joint_dia REAL, joint_type TEXT, sch_thickness REAL,
wps_no TEXT, welder_id TEXT, fitup_date DATE, weld_date DATE,
visual_status TEXT DEFAULT 'Pending', nde_type TEXT,
nde_report_no TEXT, nde_result TEXT, status TEXT DEFAULT 'Open'
);
''')
conn.commit()
return conn

conn = init_db()
c = conn.cursor()

2. INTERFACE
st.set_page_config(layout="wide", page_title="WeldQMS Pro")
st.title("👨‍🏭 WeldQMS Professional")
st.write("---")

tabs = st.tabs(["📂 Areas", "📏 Joints", "👷 Welders", "📊 Reports"])

with tabs[0]:
st.header("Project Area Registration")
with st.form("area_f"):
name = st.text_input("Area Name")
if st.form_submit_button("Create"):
c.execute("INSERT OR IGNORE INTO areas (area_name) VALUES (?)", (name,))
conn.commit()
st.rerun()
st.dataframe(pd.read_sql_query("SELECT * FROM areas", conn))

with tabs[1]:
st.header("Joint Management")
areas = [r[0] for r in c.execute("SELECT area_name FROM areas").fetchall()]
if areas:
sel_area = st.selectbox("Select Area", areas)
with st.expander("Upload Excel"):
f = st.file_uploader("Excel File", type=['xlsx'])
if f and st.button("Import"):
df = pd.read_excel(f)
for _, row in df.iterrows():
c.execute("INSERT INTO joints (area_name, line_no, tag_no, drawing_no, joint_dia, wps_no) VALUES (?,?,?,?,?,?)",
(sel_area, row['line_no'], row['tag_no'], row['drawing_no'], row['joint_dia'], row['wps_no']))
conn.commit()
st.rerun()
df_j = pd.read_sql_query("SELECT * FROM joints WHERE area_name=?", conn, params=(sel_area,))
st.dataframe(df_j)

with tabs[2]:
st.header("Welder Registry")
with st.form("w_reg"):
wid = st.text_input("Welder ID")
wn = st.text_input("Name")
if st.form_submit_button("Register"):
c.execute("INSERT OR IGNORE INTO welders (welder_id, name) VALUES (?,?)", (wid, wn))
conn.commit()
st.rerun()
st.dataframe(pd.read_sql_query("SELECT * FROM welders", conn))

with tabs[3]:
st.header("NDE & Performance Reports")
df_all = pd.read_sql_query("SELECT * FROM joints", conn)
st.dataframe(df_all)
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
df_all.to_excel(writer, index=False)
st.download_button("Download Excel Report", buffer, "WeldReport.xlsx")COUNT(*)) * 100 as Repair_Rate
        FROM joints WHERE nde_result IS NOT NULL GROUP BY welder_id
        """
        st.table(get_data(query))
