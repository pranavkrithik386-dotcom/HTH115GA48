import os
import re
import json
import sqlite3
from pathlib import Path

from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import fitz
from groq import Groq

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DB_DIR = BASE_DIR / "database"

UPLOAD_DIR.mkdir(exist_ok=True)
DB_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

ALLOWED = {"pdf"}

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


SKILL_ALIASES = {
    "python": ["python"],
    "sql": ["sql", "mysql", "postgresql"],
    "machine learning": ["machine learning", "ml", "scikit-learn", "sklearn"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "scikit-learn": ["scikit-learn", "sklearn"],
    "git": ["git", "github"],
    "docker": ["docker"],
    "fastapi": ["fastapi"],
    "flask": ["flask"],
    "rest apis": ["rest api", "rest apis", "restful"],
    "postgresql": ["postgresql", "postgres"],
    "aws": ["aws", "amazon web services"],
    "power bi": ["power bi", "powerbi"],
    "statistics": ["statistics", "statistical"],
    "data analysis": ["data analysis", "data analyst", "analyzed", "analytics"],
    "excel": ["excel", "microsoft excel"],
    "tensorflow": ["tensorflow"],
    "javascript": ["javascript"],
    "react": ["react"],
    "node.js": ["node.js", "nodejs"],
    "mongodb": ["mongodb"],
    "java": ["java"],
    "c++": ["c++"],
    "linux": ["linux"],
    "ci/cd": ["ci/cd"],
}


def extract_pdf_text(path):
    doc = fitz.open(path)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text.strip()


def clean_line(line):
    return re.sub(r"\s+", " ", line).strip(" -•\t")


def extract_requirements(jd_text):
    lines = [clean_line(x) for x in jd_text.splitlines() if clean_line(x)]

    found = []
    lower_all = jd_text.lower()

    for skill, aliases in SKILL_ALIASES.items():
        if any(
            re.search(
                r"(?<!\w)" + re.escape(a) + r"(?!\w)",
                lower_all
            )
            for a in aliases
        ):
            found.append(skill)

    if re.search(
        r"bachelor|b\.e\.|b\.tech|b\.sc|bca|master|m\.sc",
        lower_all
    ):
        found.append("bachelor's degree")

    if re.search(r"\b\d+\s*(?:year|years)\b", lower_all):
        found.append("experience")

    out = []

    for x in found:
        if x not in out:
            out.append(x)

    return out


def find_evidence(requirement, resume_text):
    aliases = SKILL_ALIASES.get(requirement, [requirement])

    for line in resume_text.splitlines():
        clean = clean_line(line)

        if clean and any(
            a.lower() in clean.lower()
            for a in aliases
        ):
            return clean

    return None


def deterministic_match(requirement, resume_text):
    evidence = find_evidence(requirement, resume_text)

    if evidence:
        return "MATCH", evidence

    related = {
        "machine learning": [
            "data science",
            "analytics",
            "statistics"
        ],
        "data analysis": [
            "data analyst",
            "analytics",
            "power bi"
        ],
        "docker": [
            "cloud",
            "devops"
        ],
        "aws": [
            "cloud"
        ],
        "fastapi": [
            "flask",
            "rest api"
        ],
        "postgresql": [
            "sql",
            "mysql"
        ],
        "scikit-learn": [
            "machine learning",
            "python"
        ],
    }

    lower = resume_text.lower()

    if requirement in related and any(
        term in lower
        for term in related[requirement]
    ):
        return (
            "PARTIAL",
            "Related evidence found, but the exact requirement "
            "is not explicitly stated."
        )

    return (
        "MISSING",
        "No explicit evidence found in the uploaded resume."
    )


def calculate_score(results):
    if not results:
        return 0

    points = {
        "MATCH": 1.0,
        "PARTIAL": 0.5,
        "MISSING": 0.0
    }

    return round(
        sum(points[r["status"]] for r in results)
        / len(results)
        * 100
    )


def extract_json_from_response(content):
    """
    Safely extract JSON even if the model returns:
    ```json
    {...}
    ```
    or additional text around the JSON.
    """

    content = content.strip()

    # Remove Markdown code fences
    content = re.sub(
        r"^```json\s*",
        "",
        content,
        flags=re.IGNORECASE
    )

    content = re.sub(
        r"^```\s*",
        "",
        content
    )

    content = re.sub(
        r"\s*```$",
        "",
        content
    )

    # First attempt: direct JSON
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Second attempt: find the JSON object
    start = content.find("{")
    end = content.rfind("}")

    if start != -1 and end != -1 and end > start:
        json_text = content[start:end + 1]

        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            pass

    raise ValueError(
        "Groq returned a response that was not valid JSON."
    )


def llm_explanation(results, resume_text, jd_text):

    if not client:
        return {
            "summary": (
                "LLM explanation is unavailable because "
                "GROQ_API_KEY is not configured. "
                "The evidence-based matching still works."
            ),
            "gaps": [
                r["requirement"]
                for r in results
                if r["status"] == "MISSING"
            ],
            "questions": [
                f"Explain your experience with {r['requirement']}."
                for r in results
                if r["status"] != "MATCH"
            ][:5]
        }

    compact = json.dumps(
        results,
        ensure_ascii=False
    )

    prompt = f"""
You are an explainable resume-to-job analysis assistant.

Use ONLY the supplied requirement results and evidence.

Do not invent experience, skills, qualifications,
employers, dates, or projects.

Return ONLY valid JSON.

The JSON must have exactly these keys:

{{
  "summary": "short explanation",
  "gaps": ["gap 1", "gap 2"],
  "questions": ["question 1", "question 2"]
}}

Requirement results:
{compact}

Resume text:
{resume_text[:12000]}

Job description:
{jd_text[:12000]}
"""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            temperature=0.2,
            max_completion_tokens=1200,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You produce concise, "
                        "evidence-grounded hiring "
                        "decision support."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
        )

        content = response.choices[0].message.content

        if not content:
            raise ValueError(
                "Groq returned an empty response."
            )

        result = extract_json_from_response(content)

        # Make sure the expected keys exist
        return {
            "summary": str(
                result.get(
                    "summary",
                    "No AI summary was returned."
                )
            ),
            "gaps": result.get("gaps", []),
            "questions": result.get("questions", [])
        }

    except Exception as e:
        return {
            "summary": (
                "AI explanation could not be generated. "
                f"Reason: {str(e)}"
            ),
            "gaps": [
                r["requirement"]
                for r in results
                if r["status"] == "MISSING"
            ],
            "questions": [
                f"Explain your experience with {r['requirement']}."
                for r in results
                if r["status"] != "MATCH"
            ][:5]
        }


def save_evaluation(
    resume_name,
    job_name,
    score,
    results
):
    db = sqlite3.connect(DB_DIR / "app.db")

    db.execute("""
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resume_name TEXT,
            job_name TEXT,
            score INTEGER,
            results_json TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute(
        """
        INSERT INTO evaluations
        (resume_name, job_name, score, results_json)
        VALUES (?, ?, ?, ?)
        """,
        (
            resume_name,
            job_name,
            score,
            json.dumps(results)
        )
    )

    db.commit()
    db.close()


@app.route("/")
def home():
    return render_template("index.html")


@app.post("/analyze")
def analyze():

    if (
        "resume" not in request.files
        or "job" not in request.files
    ):
        return jsonify({
            "error": (
                "Please upload both a resume PDF "
                "and a job description PDF."
            )
        }), 400

    resume = request.files["resume"]
    job = request.files["job"]

    if (
        not resume.filename.lower().endswith(".pdf")
        or not job.filename.lower().endswith(".pdf")
    ):
        return jsonify({
            "error": "Only PDF files are supported."
        }), 400

    resume_path = (
        UPLOAD_DIR
        / secure_filename(resume.filename)
    )

    job_path = (
        UPLOAD_DIR
        / secure_filename(job.filename)
    )

    resume.save(resume_path)
    job.save(job_path)

    try:

        resume_text = extract_pdf_text(
            resume_path
        )

        jd_text = extract_pdf_text(
            job_path
        )

        requirements = extract_requirements(
            jd_text
        )

        results = []

        for req in requirements:

            status, evidence = deterministic_match(
                req,
                resume_text
            )

            results.append({
                "requirement": req,
                "status": status,
                "evidence": evidence
            })

        score = calculate_score(results)

        explanation = llm_explanation(
            results,
            resume_text,
            jd_text
        )

        save_evaluation(
            resume.filename,
            job.filename,
            score,
            results
        )

        return jsonify({
            "resume": resume.filename,
            "job": job.filename,
            "score": score,
            "results": results,
            "explanation": explanation,
            "bias_note": (
                "Matching uses job-related evidence "
                "such as skills, education and experience. "
                "Name, gender, age, photo, religion, "
                "marital status and address are not used."
            )
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(debug=True)