from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import sqlite3
from pydantic import BaseModel
from llm import generate_sql
import re

app = FastAPI()

# -----------------------------
# Enable CORS (Frontend Support)
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Load CSV Data into SQLite
# -----------------------------
def load_data():
    conn = sqlite3.connect("database.db")

    pd.read_csv("Employee.csv").to_sql(
        "employee", conn, if_exists="replace", index=False
    )
    pd.read_csv("PerformanceRating.csv").to_sql(
        "performance", conn, if_exists="replace", index=False
    )
    pd.read_csv("EducationLevel.csv").to_sql(
        "education_level", conn, if_exists="replace", index=False
    )
    pd.read_csv("RatingLevel.csv").to_sql(
        "rating_level", conn, if_exists="replace", index=False
    )
    pd.read_csv("SatisfiedLevel.csv").to_sql(
        "satisfaction_level", conn, if_exists="replace", index=False
    )

    conn.close()

load_data()

# -----------------------------
# Request Model
# -----------------------------
class Query(BaseModel):
    question: str


# -----------------------------
# Health Check
# -----------------------------
@app.get("/")
def home():
    return {"message": "HR BI Chatbot backend running"}


# -----------------------------
# SQL Safety Validator
# -----------------------------
def sanitize_sql(sql: str) -> str:

    sql = sql.strip().rstrip(";")

    # Prevent multiple statements
    if ";" in sql:
        raise Exception("Only one SQL statement allowed.")

    # Only allow SELECT queries
    if not sql.lower().startswith("select"):
        raise Exception("Only SELECT queries are allowed.")

    # Prevent dangerous keywords
    forbidden = ["drop", "delete", "update", "insert", "alter", "truncate"]
    for word in forbidden:
        if re.search(rf"\b{word}\b", sql.lower()):
            raise Exception("Unsafe SQL detected.")

    return sql


# -----------------------------
# Ask Endpoint
# -----------------------------
@app.post("/ask")
def ask(query: Query):

    try:
        # Generate SQL from LLM
        sql = generate_sql(query.question)

        # Safety cleanup
        sql = sanitize_sql(sql)

        print("Generated SQL:", sql)

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        data = []
        for row in rows:
            record = dict(zip(columns, row))

            # Remove null categories
            if record.get("category") is None:
                continue

            data.append(record)

        conn.close()

        if not data:
            return {"error": "No data returned."}

        # -----------------------------
        # KPI Calculation
        # -----------------------------
        metrics = [d["metric"] for d in data if isinstance(d.get("metric"), (int, float))]
        kpi = round(sum(metrics) / len(metrics), 2) if metrics else None

        # -----------------------------
        # Total Employees KPI
        # -----------------------------
        conn = sqlite3.connect("database.db")
        total_employees = conn.execute(
            "SELECT COUNT(*) FROM employee"
        ).fetchone()[0]
        conn.close()

        # -----------------------------
        # Detect Time Series
        # -----------------------------
        is_time_series = "strftime" in sql.lower()

        return {
            "sql": sql,
            "data": data,
            "kpi": kpi,
            "total_employees": total_employees,
            "is_time_series": is_time_series
        }

    except Exception as e:
        return {"error": str(e)}