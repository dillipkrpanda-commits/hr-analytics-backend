import requests
import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not set. Please configure it in .env file.")


# =====================================================
# SQL GENERATION
# =====================================================

def generate_sql(question: str) -> str:

    schema = """
STRICT DATABASE SCHEMA (Use ONLY these exact columns):

Table: employee
Columns:
EmployeeID, FirstName, LastName, Gender, Age,
BusinessTravel, Department, DistanceFromHome_KM,
State, Ethnicity, Education, EducationField,
JobRole, MaritalStatus, Salary, StockOptionLevel,
OverTime, HireDate, Attrition,
YearsAtCompany, YearsInMostRecentRole,
YearsSinceLastPromotion, YearsWithCurrManager

Table: performance
Columns:
PerformanceID, EmployeeID, ReviewDate,
EnvironmentSatisfaction, JobSatisfaction,
RelationshipSatisfaction, TrainingOpportunitiesWithinYear,
TrainingOpportunitiesTaken, WorkLifeBalance,
SelfRating, ManagerRating

Table: education_level
Columns:
EducationLevelID, EducationLevel

Table: rating_level
Columns:
RatingID, RatingLevel

Table: satisfaction_level
Columns:
SatisfactionID, SatisfactionLevel

Relationships:
performance.EmployeeID = employee.EmployeeID
employee.Education = education_level.EducationLevelID
performance.SelfRating = rating_level.RatingID

Rules:
- Use ONLY exact column names listed above.
- Always alias grouped column as category.
- Always alias aggregated column as metric.
- For yearly trend use:
  strftime('%Y', performance.ReviewDate)
- For monthly trend use:
  strftime('%Y-%m', performance.ReviewDate)
- When using aggregation ALWAYS include GROUP BY if grouping requested.
- If grouping by date expression, GROUP BY the SAME expression.
- Return ONLY one valid SQLite SELECT statement.
- Do NOT include explanation.
- Do NOT use semicolon.
- Do NOT invent new column names.
"""

    prompt = f"""
You are a senior HR analytics SQL expert.
Generate a valid SQLite query.

{schema}

User Question:
{question}
"""

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "Generate ONLY SQL. No explanation."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0
        },
        timeout=30
    )

    result = response.json()

    if "error" in result:
        raise Exception(result["error"])

    if "choices" not in result:
        raise Exception(f"Unexpected API response: {result}")

    sql = result["choices"][0]["message"]["content"].strip()

    # Remove markdown wrapping if present
    if sql.startswith("```"):
        sql = sql.replace("```sql", "").replace("```", "").strip()

    # Safety cleanup
    sql = sql.rstrip(";")

    return sql


# =====================================================
# INSIGHT GENERATION
# =====================================================

def generate_insight(question: str, data: list) -> str:

    prompt = f"""
You are an HR analytics expert.

User Question:
{question}

Aggregated Data Result:
{data}

Write a concise 2-line executive-level business insight.
- Focus on trends, highs/lows, or key takeaways.
- Do NOT explain methodology.
- Do NOT repeat numbers excessively.
- Keep it professional and strategic.
"""

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "Generate professional HR insights."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        },
        timeout=30
    )

    result = response.json()

    if "error" in result:
        return ""

    if "choices" not in result:
        return ""

    insight = result["choices"][0]["message"]["content"].strip()

    return insight