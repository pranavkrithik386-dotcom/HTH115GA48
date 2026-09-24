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


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

UPLOAD_DIR = BASE_DIR / "uploads"
DB_DIR = BASE_DIR / "database"

UPLOAD_DIR.mkdir(exist_ok=True)
DB_DIR.mkdir(exist_ok=True)


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


# ============================================================
# GROQ
# ============================================================

GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY",
    ""
)

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-20b"
)

client = (
    Groq(api_key=GROQ_API_KEY)
    if GROQ_API_KEY
    else None
)


# ============================================================
# SKILL ALIASES
# EXACT MATCH ONLY
# ============================================================

SKILL_ALIASES = {

    "python": [
        "python"
    ],

    "sql": [
        "sql",
        "mysql"
    ],

    "machine learning": [
        "machine learning",
        "ml",
        "scikit-learn",
        "sklearn"
    ],

    "pandas": [
        "pandas"
    ],

    "numpy": [
        "numpy"
    ],

    "scikit-learn": [
        "scikit-learn",
        "sklearn"
    ],

    "git": [
        "git"
    ],

    "docker": [
        "docker"
    ],

    "fastapi": [
        "fastapi"
    ],

    "flask": [
        "flask"
    ],

    "rest apis": [
        "rest api",
        "rest apis",
        "restful"
    ],

    "postgresql": [
        "postgresql",
        "postgres"
    ],

    "aws": [
        "aws",
        "amazon web services"
    ],

    "power bi": [
        "power bi",
        "powerbi"
    ],

    "statistics": [
        "statistics",
        "statistical"
    ],

    "data analysis": [
        "data analysis",
        "data analyst",
        "analytics"
    ],

    "excel": [
        "excel",
        "microsoft excel"
    ],

    "tensorflow": [
        "tensorflow"
    ],

    "javascript": [
        "javascript"
    ],

    "react": [
        "react"
    ],

    "node.js": [
        "node.js",
        "nodejs"
    ],

    "mongodb": [
        "mongodb"
    ],

    "java": [
        "java"
    ],

    "c++": [
        "c++"
    ],

    "linux": [
        "linux"
    ],

    "ci/cd": [
        "ci/cd"
    ],

    "pyspark": [
        "pyspark",
        "apache spark"
    ],

    "airflow": [
        "airflow",
        "apache airflow"
    ],

    "etl": [
        "etl",
        "extract transform load"
    ],

    "aws s3": [
        "aws s3",
        "amazon s3",
        "s3"
    ]
}


# ============================================================
# RELATED SKILLS
# RELATED = PARTIAL, NEVER MATCH
# ============================================================

RELATED_SKILLS = {

    "machine learning": [
        "data science",
        "statistics",
        "tensorflow",
        "pytorch"
    ],

    "data analysis": [
        "data analyst",
        "analytics",
        "power bi",
        "pandas",
        "excel"
    ],

    "docker": [
        "container",
        "containers",
        "devops"
    ],

    "aws": [
        "azure",
        "gcp",
        "google cloud",
        "cloud computing",
        "cloud"
    ],

    "fastapi": [
        "flask",
        "rest api",
        "restful api"
    ],

    "postgresql": [
        "mysql"
    ],

    "pyspark": [
        "spark",
        "apache spark"
    ],

    "airflow": [
        "workflow scheduling",
        "workflow orchestration",
        "pipeline scheduling"
    ],

    "etl": [
        "data pipeline",
        "data pipelines",
        "data transformation",
        "data ingestion"
    ],

    "aws s3": [
        "cloud storage",
        "object storage",
        "aws storage"
    ],

    "sql": [
        "database querying",
        "relational database"
    ],

    "git": [
        "version control"
    ]
}


# ============================================================
# CATEGORY PRIORITY
# ============================================================

CATEGORY_PRIORITY = {

    "Required Skills": 5,
    "Preferred Skills": 4,
    "Responsibilities": 3,
    "Certification": 2,
    "Education": 2,
    "Experience": 2,
    "General": 1,
    "Technical Skill": 1
}


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_line(line):

    line = re.sub(
        r"\s+",
        " ",
        line
    ).strip()

    line = line.strip(
        " -•\t"
    )

    return line


# ============================================================
# PDF EXTRACTION
# ============================================================

def extract_pdf_pages(path):

    doc = fitz.open(path)

    pages = []

    for page_number, page in enumerate(
        doc,
        start=1
    ):

        pages.append({

            "page": page_number,

            "text": page.get_text().strip()
        })

    doc.close()

    return pages


def pages_to_text(pages):

    return "\n".join(

        page["text"]

        for page in pages

    ).strip()


# ============================================================
# SECTION DETECTION
# ============================================================

def detect_section(line):

    lower = line.lower().strip()

    if re.search(
        r"\b(required skills?|technical skills?|requirements?)\b",
        lower
    ):

        return "Required Skills"

    if re.search(
        r"\b(preferred skills?|preferred qualifications?|nice to have)\b",
        lower
    ):

        return "Preferred Skills"

    if re.search(
        r"\b(responsibilities|roles and responsibilities|key responsibilities)\b",
        lower
    ):

        return "Responsibilities"

    if re.search(
        r"\b(experience|work experience|professional experience)\b",
        lower
    ):

        return "Experience"

    if re.search(
        r"\b(education|educational qualification)\b",
        lower
    ):

        return "Education"

    if re.search(
        r"\b(certifications?|certification)\b",
        lower
    ):

        return "Certification"

    return None


# ============================================================
# SKILL DETECTION
# ============================================================

def find_skill_matches(text):

    found = []

    ordered_skills = [

        "aws s3",
        "pyspark",
        "airflow",
        "postgresql",
        "rest apis",

        "python",
        "sql",
        "etl",
        "git",
        "docker",
        "fastapi",
        "flask",

        "machine learning",
        "scikit-learn",
        "pandas",
        "numpy",
        "power bi",
        "statistics",
        "data analysis",
        "excel",
        "tensorflow",
        "javascript",
        "react",
        "node.js",
        "mongodb",
        "java",
        "c++",
        "linux",
        "ci/cd",

        "aws"
    ]

    lower_text = text.lower()

    for skill in ordered_skills:

        aliases = SKILL_ALIASES.get(
            skill,
            [skill]
        )

        for alias in aliases:

            pattern = (
                r"(?<!\w)"
                + re.escape(alias.lower())
                + r"(?!\w)"
            )

            if re.search(
                pattern,
                lower_text
            ):

                found.append(skill)

                break

    return found


# ============================================================
# ADD REQUIREMENT
# ============================================================

def add_requirement(
    requirements,
    requirement,
    category,
    source_text
):

    requirement = requirement.lower().strip()

    # AWS S3 should not create a second standalone AWS
    # requirement when both appear in the same source line.

    if requirement == "aws":

        source_lower = (
            source_text or ""
        ).lower()

        if "s3" in source_lower:

            return

    for item in requirements:

        if item["requirement"] == requirement:

            old_priority = CATEGORY_PRIORITY.get(
                item["category"],
                0
            )

            new_priority = CATEGORY_PRIORITY.get(
                category,
                0
            )

            if new_priority > old_priority:

                item["category"] = category

                item["source_text"] = source_text

            elif (
                not item.get("source_text")
                and source_text
            ):

                item["source_text"] = source_text

            return

    requirements.append({

        "requirement": requirement,

        "category": category,

        "source_text": source_text
    })


# ============================================================
# REQUIREMENT EXTRACTION
# ============================================================

def extract_requirements(jd_text):

    lines = [

        clean_line(x)

        for x in jd_text.splitlines()

        if clean_line(x)
    ]

    requirements = []

    current_section = "General"

    for line in lines:

        detected = detect_section(line)

        if detected:

            current_section = detected

            continue

        if len(line) < 2:

            continue

        if line.lower() in {

            "job description",
            "job summary",
            "about the role",
            "about the company"

        }:

            continue

        skills = find_skill_matches(line)

        for skill in skills:

            add_requirement(

                requirements,

                skill,

                current_section,

                line
            )

    # Global skill detection

    for skill in find_skill_matches(jd_text):

        add_requirement(

            requirements,

            skill,

            "Technical Skill",

            None
        )

    # ========================================================
    # EDUCATION
    # ========================================================

    education_patterns = [

        r"\bbachelor(?:'s)?\s+degree\b",
        r"\bbachelor\b",
        r"\bb\.?\s*tech\b",
        r"\bb\.?\s*e\.?\b",
        r"\bb\.?\s*sc\b",
        r"\bbca\b",
        r"\bmaster(?:'s)?\s+degree\b",
        r"\bm\.?\s*sc\b",
        r"\bmca\b"
    ]

    education_source = None

    for line in lines:

        for pattern in education_patterns:

            if re.search(
                pattern,
                line,
                re.IGNORECASE
            ):

                education_source = line

                break

        if education_source:

            break

    if education_source:

        add_requirement(

            requirements,

            "bachelor's degree",

            "Education",

            education_source
        )

    # ========================================================
    # EXPERIENCE
    # ========================================================

    experience_patterns = [

        r"\b\d+\s*(?:-|–|—|to)\s*\d+\s*years?\b",

        r"\b\d+\s*\+?\s*years?\s+of\s+experience\b",

        r"\b\d+\s*\+?\s*years?\s+experience\b",

        r"\bexperience\s+in\b"
    ]

    experience_source = None

    for line in lines:

        for pattern in experience_patterns:

            if re.search(
                pattern,
                line,
                re.IGNORECASE
            ):

                experience_source = line

                break

        if experience_source:

            break

    if experience_source:

        add_requirement(

            requirements,

            "experience",

            "Experience",

            experience_source
        )

    # ========================================================
    # CERTIFICATION
    # ========================================================

    certification_patterns = [

        r"\baws\s+cloud\s+practitioner\b",

        r"\bcloud\s+practitioner\b",

        r"\bcertified\b",

        r"\bcertification\b",

        r"\bcertificate\b"
    ]

    certification_source = None

    for line in lines:

        for pattern in certification_patterns:

            if re.search(
                pattern,
                line,
                re.IGNORECASE
            ):

                certification_source = line

                break

        if certification_source:

            break

    if certification_source:

        add_requirement(

            requirements,

            "certification",

            "Certification",

            certification_source
        )

    return requirements


# ============================================================
# EXACT EVIDENCE
# ============================================================

def find_exact_evidence(
    requirement,
    resume_pages
):

    aliases = SKILL_ALIASES.get(

        requirement,

        [requirement]
    )

    aliases = sorted(
        aliases,
        key=len,
        reverse=True
    )

    for page_data in resume_pages:

        page_number = page_data["page"]

        for raw_line in page_data["text"].splitlines():

            line = clean_line(raw_line)

            if not line:

                continue

            for alias in aliases:

                pattern = (

                    r"(?<!\w)"

                    + re.escape(
                        alias.lower()
                    )

                    + r"(?!\w)"
                )

                match = re.search(

                    pattern,

                    line.lower()
                )

                if match:

                    return {

                        "text": line[
                            match.start():
                            match.end()
                        ].strip(),

                        "page": page_number,

                        "type": "EXACT"
                    }

    return None


# ============================================================
# RELATED EVIDENCE
# ============================================================

def find_related_evidence(
    requirement,
    resume_pages
):

    related_terms = RELATED_SKILLS.get(

        requirement,

        []
    )

    related_terms = sorted(

        related_terms,

        key=len,

        reverse=True
    )

    for page_data in resume_pages:

        page_number = page_data["page"]

        for raw_line in page_data["text"].splitlines():

            line = clean_line(raw_line)

            if not line:

                continue

            for term in related_terms:

                pattern = (

                    r"(?<!\w)"

                    + re.escape(
                        term.lower()
                    )

                    + r"(?!\w)"
                )

                match = re.search(

                    pattern,

                    line.lower()
                )

                if match:

                    return {

                        "text": line[
                            match.start():
                            match.end()
                        ].strip(),

                        "page": page_number,

                        "type": "RELATED"
                    }

    return None


# ============================================================
# EDUCATION EVIDENCE
# ============================================================

def find_education_evidence(
    resume_pages
):

    patterns = [

        r"\bb\.?\s*tech\b",

        r"\bb\.?\s*e\.?\b",

        r"\bb\.?\s*sc\b",

        r"\bbca\b",

        r"\bbachelor(?:'s)?\b",

        r"\bm\.?\s*sc\b",

        r"\bmca\b",

        r"\bmaster(?:'s)?\b"
    ]

    for page_data in resume_pages:

        page_number = page_data["page"]

        for raw_line in page_data["text"].splitlines():

            line = clean_line(raw_line)

            if not line:

                continue

            for pattern in patterns:

                match = re.search(

                    pattern,

                    line,

                    re.IGNORECASE
                )

                if match:

                    return {

                        "text": match.group(0).strip(),

                        "page": page_number,

                        "type": "EXACT"
                    }

    return None


# ============================================================
# CERTIFICATION EVIDENCE
# ============================================================

def find_certification_evidence(
    resume_pages
):

    patterns = [

        r"\baws\s+cloud\s+practitioner\b",

        r"\bcloud\s+practitioner\b",

        r"\baws\s+certified\b",

        r"\bcertified\b",

        r"\bcertification\b"
    ]

    for page_data in resume_pages:

        page_number = page_data["page"]

        for raw_line in page_data["text"].splitlines():

            line = clean_line(raw_line)

            if not line:

                continue

            for pattern in patterns:

                match = re.search(

                    pattern,

                    line,

                    re.IGNORECASE
                )

                if match:

                    return {

                        "text": match.group(0).strip(),

                        "page": page_number,

                        "type": "EXACT"
                    }

    return None


# ============================================================
# EXPERIENCE RANGE
# ============================================================

def extract_experience_range(text):

    if not text:

        return None

    range_match = re.search(

        r"\b(\d+)\s*(?:-|–|—|to)\s*(\d+)\s*years?\b",

        text,

        re.IGNORECASE
    )

    if range_match:

        return (

            int(range_match.group(1)),

            int(range_match.group(2))
        )

    plus_match = re.search(

        r"\b(\d+)\s*\+\s*years?\b",

        text,

        re.IGNORECASE
    )

    if plus_match:

        return (

            int(plus_match.group(1)),

            None
        )

    single_match = re.search(

        r"\b(\d+)\s*years?\s*(?:of\s+)?experience\b",

        text,

        re.IGNORECASE
    )

    if single_match:

        years = int(
            single_match.group(1)
        )

        return (
            years,
            years
        )

    return None


# ============================================================
# RESUME EXPERIENCE DURATION
# ============================================================

def find_explicit_experience_duration(
    resume_pages
):

    patterns = [

        r"\b(\d+)\s*(?:-|–|—|to)\s*(\d+)\s*years?\b",

        r"\b(\d+)\s*\+\s*years?\b",

        r"\b(\d+)\s*years?\s+of\s+experience\b",

        r"\b(\d+)\s*years?\s+experience\b"
    ]

    for page_data in resume_pages:

        page_number = page_data["page"]

        for raw_line in page_data["text"].splitlines():

            line = clean_line(raw_line)

            if not line:

                continue

            for pattern in patterns:

                match = re.search(

                    pattern,

                    line,

                    re.IGNORECASE
                )

                if not match:

                    continue

                if match.lastindex == 2:

                    minimum = int(
                        match.group(1)
                    )

                    maximum = int(
                        match.group(2)
                    )

                else:

                    minimum = int(
                        match.group(1)
                    )

                    maximum = minimum

                    if "+" in match.group(0):

                        maximum = None

                return {

                    "text": match.group(0).strip(),

                    "page": page_number,

                    "type": "EXACT",

                    "min_years": minimum,

                    "max_years": maximum
                }

    return None


# ============================================================
# GENERIC EXPERIENCE EVIDENCE
# ============================================================

def find_generic_experience_evidence(
    resume_pages
):

    role_patterns = [

        r"\b(?:software|data|backend|frontend|full[- ]stack|machine learning|ml|cloud)\s+engineer\b",

        r"\b(?:software|data|business|system)\s+analyst\b",

        r"\b(?:web|software|python|java|data)\s+developer\b",

        r"\b(?:intern|internship)\b"
    ]

    for page_data in resume_pages:

        page_number = page_data["page"]

        for raw_line in page_data["text"].splitlines():

            line = clean_line(raw_line)

            if not line:

                continue

            for pattern in role_patterns:

                match = re.search(

                    pattern,

                    line,

                    re.IGNORECASE
                )

                if match:

                    return {

                        "text": match.group(0).strip(),

                        "page": page_number,

                        "type": "RELATED"
                    }

    return None


# ============================================================
# EXPERIENCE MATCHING
# ============================================================

def match_experience_requirement(
    jd_source_text,
    resume_pages
):

    jd_range = extract_experience_range(

        jd_source_text
    )

    explicit = find_explicit_experience_duration(

        resume_pages
    )

    if explicit:

        candidate_min = explicit[
            "min_years"
        ]

        candidate_max = explicit[
            "max_years"
        ]

        if jd_range:

            jd_min, jd_max = jd_range

            if candidate_min >= jd_min:

                if jd_max is None:

                    return (
                        "MATCH",
                        explicit
                    )

                if candidate_max is None:

                    return (
                        "MATCH",
                        explicit
                    )

                if candidate_max <= jd_max:

                    return (
                        "MATCH",
                        explicit
                    )

            return (
                "PARTIAL",
                explicit
            )

        return (
            "MATCH",
            explicit
        )

    generic = find_generic_experience_evidence(

        resume_pages
    )

    if generic:

        return (
            "PARTIAL",
            generic
        )

    return (

        "MISSING",

        {
            "text": None,
            "page": None,
            "type": "NONE"
        }
    )


# ============================================================
# GENERAL EVIDENCE ENGINE
# ============================================================

def find_evidence(
    requirement,
    resume_pages
):

    exact = find_exact_evidence(

        requirement,

        resume_pages
    )

    if exact:

        return exact

    related = find_related_evidence(

        requirement,

        resume_pages
    )

    if related:

        return related

    return {

        "text": None,

        "page": None,

        "type": "NONE"
    }


# ============================================================
# AUDIT REASON
# ============================================================

def build_audit_reason(
    requirement,
    category,
    status,
    evidence_type,
    resume_evidence,
    jd_evidence
):

    if status == "MATCH":

        if evidence_type == "EXACT":

            if requirement == "experience":

                return (
                    "Direct experience-duration evidence "
                    "supports the job requirement."
                )

            if requirement == "bachelor's degree":

                return (
                    "Direct education evidence matching "
                    "the required degree level was found."
                )

            if requirement == "certification":

                return (
                    "Direct certification evidence was found "
                    "in the resume."
                )

            return (
                "Direct evidence for the requirement "
                "was found in the resume."
            )

    if status == "PARTIAL":

        if requirement == "experience":

            return (
                "Relevant professional experience is indicated, "
                "but the required data-engineering experience "
                "and/or duration is not explicitly confirmed."
            )

        return (
            "Related evidence was found, but the resume does "
            "not explicitly confirm the requested requirement."
        )

    if status == "MISSING":

        return (
            "No direct or sufficiently related evidence "
            "for this requirement was found in the resume."
        )

    return (
        "The requirement could not be classified."
    )


# ============================================================
# DETERMINISTIC MATCHING
# ============================================================

def deterministic_match(
    requirement,
    resume_pages,
    jd_source_text=None
):

    # --------------------------------------------------------
    # EXPERIENCE
    # --------------------------------------------------------

    if requirement == "experience":

        return match_experience_requirement(

            jd_source_text,

            resume_pages
        )

    # --------------------------------------------------------
    # EDUCATION
    # --------------------------------------------------------

    if requirement == "bachelor's degree":

        evidence = find_education_evidence(

            resume_pages
        )

        if evidence:

            return (
                "MATCH",
                evidence
            )

    # --------------------------------------------------------
    # CERTIFICATION
    # --------------------------------------------------------

    if requirement == "certification":

        evidence = find_certification_evidence(

            resume_pages
        )

        if evidence:

            return (
                "MATCH",
                evidence
            )

    # --------------------------------------------------------
    # EXACT / RELATED / NONE
    # --------------------------------------------------------

    evidence = find_evidence(

        requirement,

        resume_pages
    )

    if evidence["type"] == "EXACT":

        return (
            "MATCH",
            evidence
        )

    if evidence["type"] == "RELATED":

        return (
            "PARTIAL",
            evidence
        )

    return (
        "MISSING",
        evidence
    )


# ============================================================
# SCORE
# ============================================================

def calculate_score(results):

    if not results:

        return 0

    points = {

        "MATCH": 1.0,

        "PARTIAL": 0.5,

        "MISSING": 0.0
    }

    total = sum(

        points.get(
            result["status"],
            0
        )

        for result in results
    )

    return round(

        total /

        len(results)

        * 100
    )


# ============================================================
# JSON EXTRACTION
# ============================================================

def extract_json_from_response(content):

    content = content.strip()

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

    try:

        return json.loads(content)

    except json.JSONDecodeError:

        pass

    start = content.find("{")

    end = content.rfind("}")

    if (

        start != -1

        and end != -1

        and end > start

    ):

        try:

            return json.loads(

                content[
                    start:end + 1
                ]
            )

        except json.JSONDecodeError:

            pass

    raise ValueError(
        "Groq returned invalid JSON."
    )


# ============================================================
# GROQ EXPLANATION
# ============================================================

def llm_explanation(
    results,
    resume_text,
    jd_text
):

    if not client:

        return {

            "summary": (

                "LLM explanation is unavailable because "
                "GROQ_API_KEY is not configured. "
                "Evidence-based matching still works."
            ),

            "gaps": [

                r["requirement"]

                for r in results

                if r["status"] != "MATCH"
            ],

            "questions": [

                (
                    f"Explain your experience with "
                    f"{r['requirement']}."
                )

                for r in results

                if r["status"] != "MATCH"
            ][:7]
        }

    compact_results = json.dumps(

        results,

        ensure_ascii=False
    )

    prompt = f"""
You are an explainable resume-to-job analysis assistant.

The deterministic matching engine has already calculated
MATCH, PARTIAL, or MISSING.

You MUST NOT change those statuses.

Rules:

MATCH:
Direct evidence exists.

PARTIAL:
Related or incomplete evidence exists, but the requirement
is not fully confirmed.

MISSING:
No meaningful evidence exists.

Never invent resume information.

Never invent:

- skills
- years
- projects
- employers
- certifications
- dates
- achievements

Never infer years of experience from graduation year.

Never infer SQL merely from PostgreSQL.

Never infer AWS merely from another cloud provider.

Never infer PySpark merely from Spark.

Never infer Git merely from GitHub.

For the summary:
Explain what is directly supported.

For gaps:
Include MISSING and PARTIAL requirements.

For interview questions:
Create questions specifically related to MISSING or PARTIAL
requirements.

Return ONLY valid JSON:

{{
  "summary": "short evidence-grounded explanation",
  "gaps": [
    "gap 1",
    "gap 2"
  ],
  "questions": [
    "question 1",
    "question 2"
  ]
}}

Requirement results:

{compact_results}

Resume:

{resume_text[:12000]}

Job Description:

{jd_text[:12000]}
"""

    try:

        response = client.chat.completions.create(

            model=GROQ_MODEL,

            temperature=0.2,

            max_completion_tokens=1400,

            messages=[

                {

                    "role": "system",

                    "content": (
                        "You provide concise,"
                        "evidence-grounded"
                        "candidate-role analysis."
                        "Never invent resume facts."
                    )
                },

                {

                    "role": "user",

                    "content": prompt
                }
            ]
        )

        content = (

            response
            .choices[0]
            .message
            .content
        )

        result = extract_json_from_response(
            content
        )

        return {

            "summary": str(

                result.get(
                    "summary",
                    "No AI summary was returned."
                )
            ),

            "gaps": result.get(
                "gaps",
                []
            ),

            "questions": result.get(
                "questions",
                []
            )
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

                if r["status"] != "MATCH"
            ],

            "questions": [

                (
                    f"Explain your experience with "
                    f"{r['requirement']}."
                )

                for r in results

                if r["status"] != "MATCH"
            ][:7]
        }


# ============================================================
# DATABASE
# ============================================================

def initialize_database():

    db = sqlite3.connect(
        DB_DIR / "app.db"
    )

    db.execute("""

        CREATE TABLE IF NOT EXISTS evaluations (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            resume_name TEXT,

            job_name TEXT,

            score INTEGER,

            results_json TEXT,

            created_at DATETIME
                DEFAULT CURRENT_TIMESTAMP
        )

    """)

    db.commit()

    db.close()


def save_evaluation(
    resume_name,
    job_name,
    score,
    results
):

    db = sqlite3.connect(
        DB_DIR / "app.db"
    )

    db.execute("""

        INSERT INTO evaluations
        (
            resume_name,
            job_name,
            score,
            results_json
        )

        VALUES (?, ?, ?, ?)

    """, (

        resume_name,

        job_name,

        score,

        json.dumps(
            results,
            ensure_ascii=False
        )
    ))

    db.commit()

    db.close()


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    return jsonify({

        "status": "ok",

        "application": (
            "GA-04 Explainable "
            "Candidate-Role Fit Engine"
        ),

        "matching": "deterministic",

        "genai": (
            "enabled"
            if client
            else "not configured"
        )
    })


# ============================================================
# ANALYZE
# ============================================================

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

    resume_filename = secure_filename(
        resume.filename
    )

    job_filename = secure_filename(
        job.filename
    )

    resume_path = (
        UPLOAD_DIR /
        resume_filename
    )

    job_path = (
        UPLOAD_DIR /
        job_filename
    )

    resume.save(
        resume_path
    )

    job.save(
        job_path
    )

    try:

        # ====================================================
        # PDF EXTRACTION
        # ====================================================

        resume_pages = extract_pdf_pages(
            resume_path
        )

        job_pages = extract_pdf_pages(
            job_path
        )

        resume_text = pages_to_text(
            resume_pages
        )

        jd_text = pages_to_text(
            job_pages
        )

        if not resume_text:

            return jsonify({

                "error": (
                    "No readable text found "
                    "in the resume PDF."
                )

            }), 400

        if not jd_text:

            return jsonify({

                "error": (
                    "No readable text found "
                    "in the job description PDF."
                )

            }), 400

        # ====================================================
        # REQUIREMENTS
        # ====================================================

        requirements = extract_requirements(
            jd_text
        )

        # ====================================================
        # MATCH EACH REQUIREMENT
        # ====================================================

        results = []

        for requirement_data in requirements:

            requirement = (
                requirement_data[
                    "requirement"
                ]
            )

            category = (
                requirement_data[
                    "category"
                ]
            )

            jd_source_text = (
                requirement_data[
                    "source_text"
                ]
            )

            status, evidence = (
                deterministic_match(

                    requirement,

                    resume_pages,

                    jd_source_text
                )
            )

            resume_evidence = (
                evidence["text"]
            )

            page = evidence["page"]

            evidence_type = (
                evidence["type"]
            )

            audit_reason = build_audit_reason(

                requirement,

                category,

                status,

                evidence_type,

                resume_evidence,

                jd_source_text
            )

            # =================================================
            # AUDIT OBJECT
            # =================================================

            audit = {

                "decision": status,

                "evidence_type": evidence_type,

                "reason": audit_reason,

                "jd_evidence": (
                    jd_source_text
                ),

                "resume_evidence": (
                    resume_evidence
                ),

                "resume_page": page
            }

            results.append({

                "requirement": requirement,

                "category": category,

                "status": status,

                "jd_evidence": (
                    jd_source_text
                ),

                "resume_evidence": (
                    resume_evidence
                ),

                "resume_page": page,

                "evidence_type": (
                    evidence_type
                ),

                "audit_reason": audit_reason,

                "audit": audit
            })

        # ====================================================
        # SCORE
        # ====================================================

        score = calculate_score(
            results
        )

        # ====================================================
        # AI
        # ====================================================

        explanation = llm_explanation(

            results,

            resume_text,

            jd_text
        )

        # ====================================================
        # DATABASE
        # ====================================================

        save_evaluation(

            resume.filename,

            job.filename,

            score,

            results
        )

        # ====================================================
        # RESPONSE
        # ====================================================

        return jsonify({

            "resume": resume.filename,

            "job": job.filename,

            "score": score,

            "requirements_count": len(
                results
            ),

            "results": results,

            "explanation": explanation,

            "bias_note": (

                "Matching uses job-related evidence "
                "such as skills, education and experience. "
                "Name, gender, age, photo, religion, "
                "marital status and address are not used."
            ),

            "engine": {

                "matching": (
                    "deterministic"
                ),

                "scoring": (
                    "MATCH=1, PARTIAL=0.5, MISSING=0"
                ),

                "llm_role": (
                    "explanation, gap analysis "
                    "and interview preparation"
                )
            }
        })

    except Exception as e:

        return jsonify({

            "error": str(e)

        }), 500


# ============================================================
# FILE SIZE ERROR
# ============================================================

@app.errorhandler(413)
def file_too_large(error):

    return jsonify({

        "error": (
            "File too large. "
            "Maximum size is 10 MB."
        )

    }), 413


# ============================================================
# INITIALIZE DATABASE
# ============================================================

initialize_database()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )