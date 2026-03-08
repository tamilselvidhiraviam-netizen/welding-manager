import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# -------------------------
# DATABASE
# -------------------------

conn = sqlite3.connect("weld_control.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS areas(
id INTEGER PRIMARY KEY AUTOINCREMENT,
area_name TEXT,
client TEXT,
contractor TEXT,
location TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS lines(
id INTEGER PRIMARY KEY AUTOINCREMENT,
area_id INTEGER,
line_number TEXT,
tag_number TEXT,
drawing_number TEXT,
diameter TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS welders(
id INTEGER PRIMARY KEY AUTOINCREMENT,
welder_id TEXT,
name TEXT,
process TEXT,
qualification_date TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS welds(
id INTEGER PRIMARY KEY AUTOINCREMENT,
line_id INTEGER,
joint_number TEXT,
weld_type TEXT,
welder_id TEXT,
weld_date TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS nde(
id INTEGER PRIMARY KEY AUTOINCREMENT,
weld_id INTEGER,
nde_type TEXT,
result TEXT,
report_number TEXT,
inspection_date TEXT
)
""")

conn.commit()

# -------------------------
# APP HEADER
# -------------------------

st.title("Weld Management & Welder Control System")

menu = st.sidebar.selectbox(
"Navigation",
["Areas","Line Numbers","Welders","Weld Joints","Excel Import","Reports","Welder Continuity"]
)

# -------------------------
# AREAS
# -------------------------

if menu == "Areas":

    st.header("Area Management")

    area = st.text_input("Area Name")
    client = st.text_input("Client Name")
    contractor = st.text_input("Contractor Name")
    location = st.text_input("Location")

    if st.button("Add Area"):
        cursor.execute(
        "INSERT INTO areas(area_name,client,contractor,location) VALUES(?,?,?,?)",
        (area,client,contractor,location))
        conn.commit()
        st.success("Area Added")

    df = pd.read_sql("SELECT * FROM areas",conn)
    st.dataframe(df)


# -------------------------
# LINE NUMBERS
# -------------------------

if menu == "Line Numbers":

    st.header("Line Numbers")

    areas = pd.read_sql("SELECT * FROM areas",conn)

    area = st.selectbox("Select Area",areas["area_name"])

    line = st.text_input("Line Number")
    tag = st.text_input("Tag Number")
    drawing = st.text_input("Drawing Number")
    dia = st.text_input("Diameter")

    if st.button("Add Line"):

        area_id = areas[areas["area_name"]==area]["id"].values[0]

        cursor.execute("""
        INSERT INTO lines(area_id,line_number,tag_number,drawing_number,diameter)
        VALUES(?,?,?,?,?)
        """,(area_id,line,tag,drawing,dia))

        conn.commit()

        st.success("Line Added")

    df = pd.read_sql("""
    SELECT lines.*,areas.area_name
    FROM lines
    LEFT JOIN areas ON lines.area_id = areas.id
    """,conn)

    st.dataframe(df)

# -------------------------
# WELDERS
# -------------------------

if menu == "Welders":

    st.header("Welder Management")

    wid = st.text_input("Welder ID")
    name = st.text_input("Welder Name")
    process = st.selectbox("Process",["SMAW","GTAW","FCAW","GMAW"])
    qdate = st.date_input("Qualification Date")

    if st.button("Add Welder"):

        cursor.execute("""
        INSERT INTO welders(welder_id,name,process,qualification_date)
        VALUES(?,?,?,?)
        """,(wid,name,process,str(qdate)))

        conn.commit()

        st.success("Welder Added")

    df = pd.read_sql("SELECT * FROM welders",conn)
    st.dataframe(df)

# -------------------------
# WELD JOINTS
# -------------------------

if menu == "Weld Joints":

    st.header("Weld Joint Entry")

    lines = pd.read_sql("SELECT * FROM lines",conn)
    welders = pd.read_sql("SELECT * FROM welders",conn)

    line = st.selectbox("Line Number",lines["line_number"])

    joint = st.text_input("Joint Number")

    weld_type = st.selectbox(
    "Weld Type",
    ["BW","SW","BRANCH"]
    )

    welder = st.selectbox("Welder ID",welders["welder_id"])

    date = st.date_input("Weld Date")

    if st.button("Add Weld"):

        line_id = lines[lines["line_number"]==line]["id"].values[0]

        cursor.execute("""
        INSERT INTO welds(line_id,joint_number,weld_type,welder_id,weld_date)
        VALUES(?,?,?,?,?)
        """,(line_id,joint,weld_type,welder,str(date)))

        conn.commit()

        st.success("Weld Added")

    df = pd.read_sql("""
    SELECT welds.*,lines.line_number
    FROM welds
    LEFT JOIN lines ON welds.line_id = lines.id
    """,conn)

    st.dataframe(df)

# -------------------------
# EXCEL IMPORT
# -------------------------

if menu == "Excel Import":

    st.header("Upload Weld Excel")

    file = st.file_uploader("Upload Excel File")

    if file:

        df = pd.read_excel(file)

        st.write(df)

        if st.button("Import Data"):

            for i,row in df.iterrows():

                cursor.execute("""
                INSERT INTO welds(line_id,joint_number,weld_type,welder_id,weld_date)
                VALUES(?,?,?,?,?)
                """,(row["line_id"],row["joint"],row["type"],row["welder"],row["date"]))

            conn.commit()

            st.success("Data Imported")

# -------------------------
# REPORTS
# -------------------------

if menu == "Reports":

    st.header("Weld Reports")

    weld_summary = pd.read_sql("""
    SELECT weld_type,COUNT(*) as total
    FROM welds
    GROUP BY weld_type
    """,conn)

    st.subheader("Weld Type Summary")
    st.dataframe(weld_summary)

    welder_summary = pd.read_sql("""
    SELECT welder_id,COUNT(*) as welds
    FROM welds
    GROUP BY welder_id
    """,conn)

    st.subheader("Welder Performance")
    st.dataframe(welder_summary)

# -------------------------
# WELDER CONTINUITY
# -------------------------

if menu == "Welder Continuity":

    st.header("Welder Continuity Check")

    df = pd.read_sql("""
    SELECT welder_id,MAX(weld_date) as last_weld
    FROM welds
    GROUP BY welder_id
    """,conn)

    expired = []

    for i,row in df.iterrows():

        if row["last_weld"]:

            date = datetime.strptime(row["last_weld"],"%Y-%m-%d")

            if date < datetime.now() - timedelta(days=180):

                expired.append(row)

    if expired:

        st.warning("Welders With Expired Continuity")

        st.dataframe(pd.DataFrame(expired))

    else:

        st.success("All Welders Active")
