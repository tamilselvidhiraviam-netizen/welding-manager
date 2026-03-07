import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- DATABASE SETUP ---
conn = sqlite3.connect('welding_data.db', check_same_thread=False)
c = conn.cursor()

# Create tables if they don't exist
c.executescript('''
CREATE TABLE IF NOT EXISTS wps_master (wps_no TEXT PRIMARY KEY, process TEXT);
CREATE TABLE IF NOT EXISTS welders (welder_id TEXT PRIMARY KEY, name TEXT, qualified_wps TEXT);
CREATE TABLE IF NOT EXISTS projects (project_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT);
CREATE TABLE IF NOT EXISTS joints (
    id INTEGER PRIMARY KEY AUTOINCREMENT, project_name TEXT, drawing_no TEXT, 
    joint_dia REAL, sch_thickness REAL, wps_no TEXT, welder_id TEXT, 
    fitup_date DATE, weld_date DATE, visual_report TEXT, 
    nde_type TEXT, nde_result TEXT, status TEXT
);
''')
conn.commit()

st.set_page_config(layout="wide", page_title="WeldQMS Pro")
st.title("👨‍🏭 Welding Project & Quality Management")

# --- SIDEBAR: CONFIGURATION ---
st.sidebar.header("Setup Master Data")
menu = st.sidebar.radio("Navigation", ["Project Dashboard", "Add Project/Joints", "WPS & Welder Registry", "Welder Performance"])

# --- 1. WPS & WELDER REGISTRY ---
if menu == "WPS & Welder Registry":
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Register WPS")
        wps_input = st.text_input("WPS Number (e.g., WPS-001)")
        proc_input = st.selectbox("Process", ["TIG", "MIG", "SMAW", "FCAW"])
        if st.button("Save WPS"):
            c.execute("INSERT OR IGNORE INTO wps_master VALUES (?,?)", (wps_input, proc_input))
            conn.commit()
    
    with col2:
        st.subheader("Register Welder")
        w_id = st.text_input("Welder ID")
        w_name = st.text_input("Welder Name")
        # Multi-select for WPS qualifications
        wps_list = [row[0] for row in c.execute("SELECT wps_no FROM wps_master").fetchall()]
        w_quals = st.multiselect("Qualified for WPS:", wps_list)
        if st.button("Save Welder"):
            c.execute("INSERT OR IGNORE INTO welders VALUES (?,?,?)", (w_id, w_name, ",".join(w_quals)))
            conn.commit()

# --- 2. ADD PROJECT & JOINTS (THE UPLOAD AREA) ---
elif menu == "Add Project/Joints":
    st.subheader("Create New Project Entry")
    p_name = st.text_input("Project Name")
    
    col1, col2, col3 = st.columns(3)
    drw = col1.text_input("Drawing Number")
    dia = col2.number_input("Joint Dia (Inch)", min_value=0.5)
    sch = col3.number_input("Sch/Thickness (mm)", min_value=1.0)
    
    wps_list = [row[0] for row in c.execute("SELECT wps_no FROM wps_master").fetchall()]
    selected_wps = st.selectbox("Select WPS", wps_list)
    
    if st.button("Add Joint to Project"):
        c.execute("""INSERT INTO joints (project_name, drawing_no, joint_dia, sch_thickness, wps_no, status) 
                     VALUES (?,?,?,?,?,?)""", (p_name, drw, dia, sch, selected_wps, "Pending Fitup"))
        conn.commit()
        st.success(f"Joint for {drw} added.")

# --- 3. PROJECT DASHBOARD (UPDATING WELDS) ---
elif menu == "Project Dashboard":
    st.subheader("Active Joints Matrix")
    df = pd.read_sql_query("SELECT * FROM joints WHERE status != 'Closed'", conn)
    st.dataframe(df)
    
    st.divider()
    st.subheader("Update Joint Progress")
    joint_to_update = st.selectbox("Select Joint ID to Update", df['id'].tolist() if not df.empty else [None])
    
    if joint_to_update:
        # Get WPS for this joint to filter welders
        current_wps = df[df['id'] == joint_to_update]['wps_no'].values[0]
        
        # Logic: Filter welders qualified for THIS WPS
        all_welders = c.execute("SELECT welder_id, qualified_wps FROM welders").fetchall()
        qualified_welders = [w[0] for w in all_welders if current_wps in w[1].split(',')]
        
        c1, c2, c3 = st.columns(3)
        f_date = c1.date_input("Fitup Date")
        w_date = c2.date_input("Weld Date")
        w_id = c3.selectbox("Qualified Welder", qualified_welders)
        
        c4, c5, c6 = st.columns(3)
        v_rep = c4.selectbox("Visual Inspection", ["Pending", "Accepted", "Rejected"])
        nde_req = c5.selectbox("NDE Required", ["None", "RT", "PT", "MPI", "UT"])
        nde_res = c6.selectbox("NDE Result", ["Pending", "Pass", "Fail"])
        
        if st.button("Update and Progress Joint"):
            # Logic: If Visual is Accepted and NDE is None OR NDE is Pass -> Close
            new_status = "Open"
            if v_rep == "Accepted":
                if nde_req == "None" or nde_res == "Pass":
                    new_status = "Closed"
                else:
                    new_status = "Awaiting NDE"
            
            c.execute("""UPDATE joints SET fitup_date=?, weld_date=?, welder_id=?, 
                         visual_report=?, nde_type=?, nde_result=?, status=? WHERE id=?""",
                      (f_date, w_date, w_id, v_rep, nde_req, nde_res, new_status, joint_to_update))
            conn.commit()
            st.rerun()

# --- 4. WELDER PERFORMANCE (REPAIR RATES) ---
elif menu == "Welder Performance":
    st.subheader("Welder Performance Analytics")
    
    performance_query = """
    SELECT 
        welder_id,
        COUNT(id) as Total_Joints,
        SUM(joint_dia) as Total_Inch_Dia,
        SUM(CASE WHEN nde_result = 'Fail' THEN 1 ELSE 0 END) as Total_Repairs,
        ROUND((CAST(SUM(CASE WHEN nde_result = 'Fail' THEN 1 ELSE 0 END) AS FLOAT) / 
        NULLIF(SUM(CASE WHEN nde_result IN ('Pass', 'Fail') THEN 1 ELSE 0 END), 0)) * 100, 2) as Repair_Rate_Percent
    FROM joints
    WHERE welder_id IS NOT NULL
    GROUP BY welder_id
    """
    perf_df = pd.read_sql_query(performance_query, conn)
    st.table(perf_df)
   # --- 4. WELDER PERFORMANCE (REPAIR RATES) ---
elif menu == "Welder Performance":
    st.subheader("Welder Performance Analytics")
    
    # Query to get performance data
    performance_query = """
    SELECT 
        welder_id,
        COUNT(id) as Total_Joints,
        SUM(joint_dia) as Total_Inch_Dia,
        SUM(CASE WHEN nde_result = 'Fail' THEN 1 ELSE 0 END) as Total_Repairs,
        ROUND((CAST(SUM(CASE WHEN nde_result = 'Fail' THEN 1 ELSE 0 END) AS FLOAT) / 
        NULLIF(SUM(CASE WHEN nde_result IN ('Pass', 'Fail') THEN 1 ELSE 0 END), 0)) * 100, 2) as Repair_Rate_Percent
    FROM joints
    WHERE welder_id IS NOT NULL
    GROUP BY welder_id
    """
    
    perf_df = pd.read_sql_query(performance_query, conn)
    
    if not perf_df.empty:
        # 1. Display the table
        st.table(perf_df)
        
        # 2. Add Export Logic INSIDE this block
        import io
        buffer = io.BytesIO()
        # Use ExcelWriter with XlsxWriter engine
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            perf_df.to_excel(writer, index=False, sheet_name='Performance_Report')
        
        st.download_button(
            label="📥 Download Performance Report (Excel)",
            data=buffer.getvalue(),
            file_name=f"Welder_Performance_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.ms-excel"
        )
        
        # 3. Visual Charts
        st.subheader("Productivity (Inch-Dia)")
        st.bar_chart(perf_df.set_index('welder_id')['Total_Inch_Dia'])
        
    else:
        st.warning("No welder data found. Complete some welds in the Dashboard first!")
