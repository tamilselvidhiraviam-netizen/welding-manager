import sqlite3
import pandas as pd
import os
from datetime import datetime, timedelta

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# -----------------------------
# DATABASE CONNECTION
# -----------------------------

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# -----------------------------
# DATABASE INITIALIZATION
# -----------------------------

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS areas(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        area_name TEXT,
        client TEXT,
        contractor TEXT,
        location TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS lines(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        area_id INTEGER,
        line_number TEXT,
        tag_number TEXT,
        drawing_number TEXT,
        diameter TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS welders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        welder_id TEXT,
        name TEXT,
        process TEXT,
        qualification_date TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS welds(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        line_id INTEGER,
        joint_number TEXT,
        weld_type TEXT,
        welder_id TEXT,
        weld_date TEXT
    )
    """)

    cur.execute("""
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
    conn.close()

init_db()


# -----------------------------
# HOME PAGE
# -----------------------------

@app.route("/")
def index():
    return render_template("index.html")


# -----------------------------
# AREAS
# -----------------------------

@app.route("/areas", methods=["GET","POST"])
def areas():

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        area = request.form["area"]
        client = request.form["client"]
        contractor = request.form["contractor"]
        location = request.form["location"]

        cur.execute("""
        INSERT INTO areas(area_name,client,contractor,location)
        VALUES(?,?,?,?)
        """,(area,client,contractor,location))

        conn.commit()

    areas = cur.execute("SELECT * FROM areas").fetchall()
    conn.close()

    return render_template("areas.html",areas=areas)


# -----------------------------
# LINE NUMBERS
# -----------------------------

@app.route("/lines", methods=["GET","POST"])
def lines():

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":

        area_id = request.form["area_id"]
        line = request.form["line"]
        tag = request.form["tag"]
        drawing = request.form["drawing"]
        dia = request.form["dia"]

        cur.execute("""
        INSERT INTO lines(area_id,line_number,tag_number,drawing_number,diameter)
        VALUES(?,?,?,?,?)
        """,(area_id,line,tag,drawing,dia))

        conn.commit()

    lines = cur.execute("""
    SELECT lines.*,areas.area_name
    FROM lines
    LEFT JOIN areas ON lines.area_id=areas.id
    """).fetchall()

    areas = cur.execute("SELECT * FROM areas").fetchall()

    conn.close()

    return render_template("lines.html",lines=lines,areas=areas)


# -----------------------------
# WELDERS
# -----------------------------

@app.route("/welders",methods=["GET","POST"])
def welders():

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":

        wid = request.form["wid"]
        name = request.form["name"]
        process = request.form["process"]
        qdate = request.form["qdate"]

        cur.execute("""
        INSERT INTO welders(welder_id,name,process,qualification_date)
        VALUES(?,?,?,?)
        """,(wid,name,process,qdate))

        conn.commit()

    welders = cur.execute("SELECT * FROM welders").fetchall()

    conn.close()

    return render_template("welders.html",welders=welders)


# -----------------------------
# WELDS
# -----------------------------

@app.route("/welds",methods=["GET","POST"])
def welds():

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":

        line_id = request.form["line_id"]
        joint = request.form["joint"]
        weld_type = request.form["type"]
        welder = request.form["welder"]
        date = request.form["date"]

        cur.execute("""
        INSERT INTO welds(line_id,joint_number,weld_type,welder_id,weld_date)
        VALUES(?,?,?,?,?)
        """,(line_id,joint,weld_type,welder,date))

        conn.commit()

    welds = cur.execute("""
    SELECT welds.*,lines.line_number
    FROM welds
    LEFT JOIN lines ON welds.line_id=lines.id
    """).fetchall()

    lines = cur.execute("SELECT * FROM lines").fetchall()

    welders = cur.execute("SELECT * FROM welders").fetchall()

    conn.close()

    return render_template("welds.html",welds=welds,lines=lines,welders=welders)


# -----------------------------
# REPORTS
# -----------------------------

@app.route("/reports")
def reports():

    conn = get_db()
    cur = conn.cursor()

    weld_summary = cur.execute("""
    SELECT weld_type,COUNT(*) as total
    FROM welds
    GROUP BY weld_type
    """).fetchall()

    welder_summary = cur.execute("""
    SELECT welder_id,COUNT(*) as total
    FROM welds
    GROUP BY welder_id
    """).fetchall()

    conn.close()

    return render_template("reports.html",
                           weld_summary=weld_summary,
                           welder_summary=welder_summary)


# -----------------------------
# EXCEL IMPORT
# -----------------------------

@app.route("/import",methods=["POST"])
def import_excel():

    file = request.files["file"]

    path = os.path.join(app.config["UPLOAD_FOLDER"],file.filename)
    file.save(path)

    df = pd.read_excel(path)

    conn = get_db()
    cur = conn.cursor()

    for index,row in df.iterrows():

        cur.execute("""
        INSERT INTO welds(line_id,joint_number,weld_type,welder_id,weld_date)
        VALUES(?,?,?,?,?)
        """,(row["line_id"],row["joint"],row["type"],row["welder"],row["date"]))

    conn.commit()
    conn.close()

    return redirect("/welds")


# -----------------------------
# WELDER CONTINUITY CHECK
# -----------------------------

@app.route("/continuity")
def continuity():

    conn = get_db()
    cur = conn.cursor()

    six_months = datetime.now() - timedelta(days=180)

    inactive = cur.execute("""
    SELECT welder_id,MAX(weld_date) as last_weld
    FROM welds
    GROUP BY welder_id
    """).fetchall()

    expired = []

    for w in inactive:
        if w["last_weld"]:
            date = datetime.strptime(w["last_weld"],"%Y-%m-%d")
            if date < six_months:
                expired.append(w)

    conn.close()

    return {"expired_welders":expired}


# -----------------------------
# RUN APPLICATION
# -----------------------------

if __name__ == "__main__":
    app.run(debug=True)
