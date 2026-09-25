import os
import re
import json
import sqlite3
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from pathlib import Path

from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

try:
    import pymupdf as fitz
except ImportError:
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

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

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
# TEXT CLEANING
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
# DOCUMENT VALIDATION
# ============================================================

RESUME_SECTION_PATTERNS = {
    "education": r"\beducation(?:al)?\b|\bdegree\b|\buniversity\b|\bcollege\b",
    "experience": r"\b(?:work|professional|employment)?\s*experience\b|\bwork history\b",
    "skills": r"\bskills?\b|\btechnologies\b|\btechnical proficienc",
    "projects": r"\bprojects?\b|\bportfolio\b",
    "certifications": r"\bcertifications?\b|\blicenses?\b",
    "summary": r"\bsummary\b|\bobjective\b|\bprofile\b"
}

JOB_SIGNAL_PATTERNS = {
    "responsibilities": r"\bresponsibilit(?:y|ies)\b|\bduties\b|\bresponsible for\b|\byou will\b",
    "requirements": r"\brequirements?\b|\bmust have\b|\bmust be\b|\brequired\b",
    "qualifications": r"\bqualifications?\b|\bpreferred\b|\bnice to have\b",
    "skills": r"\bskills?\b|\btechnical skills?\b|\bproficienc",
    "experience": r"\b\d+\+?\s+years?\b|\bexperience required\b|\bexperience in\b",
    "role_context": r"\b(?:job|open)\s+title\b|\bposition\b|\brole\b|\bcareer opportunity\b",
    "work_context": r"\blocation\b|\bremote\b|\bhybrid\b|\bon[- ]site\b|\bemployment type\b|\bsalary\b|\bcompensation\b|\babout (?:the )?(?:role|company)\b"
}


def _normalized_text(text):

    return re.sub(
        r"\s+",
        " ",
        (text or "").lower()
    ).strip()


def _matched_patterns(text, patterns):

    normalized = _normalized_text(text)

    return {
        name
        for name, pattern in patterns.items()
        if re.search(pattern, normalized)
    }


def _resume_profile(text):

    normalized = _normalized_text(text)
    sections = _matched_patterns(
        normalized,
        RESUME_SECTION_PATTERNS
    )
    contact = bool(
        re.search(r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b", normalized)
        or re.search(r"(?:\+?\d[\d\s().-]{7,}\d)", normalized)
        or re.search(r"\b(?:linkedin|github)\.com\b", normalized)
    )
    identity = bool(
        re.search(r"\b(?:resume|curriculum vitae|cv)\b", normalized)
        or contact
    )
    score = len(sections) + int(contact) + int(identity)

    return {
        "score": score,
        "sections": sections,
        "contact": contact,
        "identity": identity
    }


def _job_profile(text):

    normalized = _normalized_text(text)
    signals = _matched_patterns(
        normalized,
        JOB_SIGNAL_PATTERNS
    )
    title = bool(
        re.search(
            r"\b(?:engineer|developer|analyst|manager|designer|specialist|"
            r"consultant|scientist|administrator|coordinator|architect|"
            r"technician|intern|director|lead|officer)\b",
            normalized
        )
    )
    score = len(signals) + int(title)

    return {
        "score": score,
        "signals": signals,
        "title": title
    }


def validate_resume_document(text):

    resume = _resume_profile(text)
    job = _job_profile(text)
    resume_core = len(
        resume["sections"].intersection({
            "experience",
            "skills",
            "projects",
            "education"
        })
    )
    job_core = len(
        job["signals"].intersection({
            "responsibilities",
            "requirements",
            "qualifications",
            "experience"
        })
    )

    if job["score"] >= resume["score"] + 3 and job_core >= 2:
        return (
            "INVALID RESUME — This document appears to be a Job Description. "
            "Please upload a candidate resume."
        )

    if (
        len(_normalized_text(text)) < 60
        or resume["score"] < 3
        or (resume_core == 0 and not resume["contact"])
    ):
        return (
            "INVALID RESUME — This document does not contain enough resume "
            "content. Please upload a candidate resume."
        )

    return None


def validate_job_document(text):

    job = _job_profile(text)
    resume = _resume_profile(text)
    job_core = len(
        job["signals"].intersection({
            "responsibilities",
            "requirements",
            "qualifications",
            "experience"
        })
    )

    if resume["score"] >= job["score"] + 3 and len(
        resume["sections"].intersection({
            "experience",
            "skills",
            "projects",
            "education"
        })
    ) >= 2:
        return (
            "INVALID JOB DESCRIPTION — This document appears to be a Resume. "
            "Please upload a job description."
        )

    if (
        len(_normalized_text(text)) < 60
        or job["score"] < 3
        or job_core == 0
    ):
        return (
            "INVALID JOB DESCRIPTION — This document does not contain enough "
            "job description content. Please upload a job description."
        )

    return None


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

    source_lower = (
        source_text or ""
    ).lower()

    if (
        requirement == "aws"
        and "s3" in source_lower
    ):
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

    for skill in find_skill_matches(jd_text):

        add_requirement(

            requirements,

            skill,

            "Technical Skill",

            None

        )

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

                        "text":
                            line[
                                match.start():
                                match.end()
                            ].strip(),

                        "page":
                            page_number,

                        "type":
                            "EXACT"

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

                        "text":
                            line[
                                match.start():
                                match.end()
                            ].strip(),

                        "page":
                            page_number,

                        "type":
                            "RELATED"

                    }

    return None


# ============================================================
# EDUCATION EVIDENCE
# ============================================================

def find_education_evidence(resume_pages):

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

                        "text":
                            match.group(0).strip(),

                        "page":
                            page_number,

                        "type":
                            "EXACT"

                    }

    return None


# ============================================================
# CERTIFICATION EVIDENCE
# ============================================================

def find_certification_evidence(resume_pages):

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

                        "text":
                            match.group(0).strip(),

                        "page":
                            page_number,

                        "type":
                            "EXACT"

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
# EXPERIENCE EVIDENCE
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

                    "text":
                        match.group(0).strip(),

                    "page":
                        page_number,

                    "type":
                        "EXACT",

                    "min_years":
                        minimum,

                    "max_years":
                        maximum

                }

    return None


# ============================================================
# GENERIC EXPERIENCE
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

                        "text":
                            match.group(0).strip(),

                        "page":
                            page_number,

                        "type":
                            "RELATED"

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

        candidate_min = explicit["min_years"]
        candidate_max = explicit["max_years"]

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
# GENERAL EVIDENCE
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
                "but the required experience duration is not "
                "explicitly confirmed."
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

    if requirement == "experience":

        return match_experience_requirement(

            jd_source_text,

            resume_pages

        )

    if requirement == "bachelor's degree":

        evidence = find_education_evidence(

            resume_pages

        )

        if evidence:

            return (

                "MATCH",

                evidence

            )

    if requirement == "certification":

        evidence = find_certification_evidence(

            resume_pages

        )

        if evidence:

            return (

                "MATCH",

                evidence

            )

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

def status_points(status):

    return {

        "MATCH": 1.0,
        "PARTIAL": 0.5,
        "MISSING": 0.0

    }.get(

        status,

        0.0

    )


def calculate_score(results):

    if not results:
        return 0

    total = sum(

        status_points(
            result["status"]
        )

        for result in results

    )

    return round(

        total /
        len(results)
        * 100

    )


# ============================================================
# DEVELOPMENT GUIDANCE
# ============================================================

DEVELOPMENT_GUIDANCE = {

    "sql": {

        "title":
            "SQL",

        "develop":
            "Learn SQL querying, joins, aggregation, "
            "subqueries, filtering and database reporting.",

        "reason":
            "SQL is required by the job description "
            "but direct SQL evidence was not found "
            "in the resume.",

        "type":
            "SKILL"

    },

    "pyspark": {

        "title":
            "PySpark",

        "develop":
            "Learn PySpark DataFrames, transformations, "
            "Spark SQL, partitioning and distributed "
            "data processing.",

        "reason":
            "PySpark is required by the job description "
            "but direct PySpark evidence was not found.",

        "type":
            "SKILL"

    },

    "aws": {

        "title":
            "AWS",

        "develop":
            "Learn AWS fundamentals, IAM, EC2, S3 "
            "and cloud-based data workflows.",

        "reason":
            "AWS is required by the job description "
            "but direct AWS evidence was not found.",

        "type":
            "SKILL"

    },

    "airflow": {

        "title":
            "Apache Airflow",

        "develop":
            "Learn DAGs, scheduling, task dependencies, "
            "operators and workflow monitoring.",

        "reason":
            "Airflow is required for workflow orchestration "
            "but direct Airflow evidence was not found.",

        "type":
            "SKILL"

    },

    "etl": {

        "title":
            "ETL / Data Pipelines",

        "develop":
            "Learn extract-transform-load workflows, "
            "data cleaning, transformation and "
            "pipeline design.",

        "reason":
            "The job requires ETL/data pipeline knowledge "
            "but direct evidence was not found.",

        "type":
            "SKILL"

    },

    "aws s3": {

        "title":
            "AWS S3",

        "develop":
            "Learn S3 buckets, objects, permissions, "
            "storage classes and cloud data storage "
            "workflows.",

        "reason":
            "AWS S3 is specifically required for cloud "
            "data storage but direct evidence was not found.",

        "type":
            "SKILL"

    },

    "certification": {

        "title":
            "Cloud Certification",

        "develop":
            "Consider an entry-level cloud certification "
            "such as AWS Cloud Practitioner.",

        "reason":
            "The job description lists a preferred cloud "
            "certification that is not evidenced in the resume.",

        "type":
            "CERTIFICATION"

    }

}


# ============================================================
# CAREER PATHWAY CURATED DATA
# ============================================================

CAREER_CERTIFICATIONS = {

    "sql": [
        {
            "provider": "Microsoft",
            "name": "Microsoft Certified: Azure Data Fundamentals",
            "type": "Certification",
            "url": "https://learn.microsoft.com/en-us/credentials/certifications/azure-data-fundamentals/"
        }
    ],

    "python": [
        {
            "provider": "Python Institute",
            "name": "PCEP - Certified Entry-Level Python Programmer",
            "type": "Certification",
            "url": "https://pythoninstitute.org/pcep"
        }
    ],

    "machine learning": [
        {
            "provider": "Google",
            "name": "Google Advanced Data Analytics Professional Certificate",
            "type": "Professional Certificate",
            "url": "https://grow.google/certificates/advanced-data-analytics/"
        }
    ],

    "aws": [
        {
            "provider": "Amazon Web Services",
            "name": "AWS Certified Cloud Practitioner",
            "type": "Certification",
            "url": "https://aws.amazon.com/certification/certified-cloud-practitioner/"
        }
    ],

    "aws s3": [
        {
            "provider": "Amazon Web Services",
            "name": "AWS Certified Cloud Practitioner",
            "type": "Certification",
            "url": "https://aws.amazon.com/certification/certified-cloud-practitioner/"
        }
    ],

    "pyspark": [
        {
            "provider": "Databricks",
            "name": "Databricks Certified Associate Developer for Apache Spark",
            "type": "Certification",
            "url": "https://www.databricks.com/learn/certification/apache-spark-developer-associate"
        }
    ],

    "airflow": [
        {
            "provider": "Astronomer",
            "name": "Astronomer Certification for Apache Airflow Fundamentals",
            "type": "Certification",
            "url": "https://www.astronomer.io/certification/"
        }
    ],

    "etl": [
        {
            "provider": "Google Cloud",
            "name": "Professional Data Engineer Certification",
            "type": "Certification",
            "url": "https://cloud.google.com/learn/certification/data-engineer"
        }
    ],

    "data analysis": [
        {
            "provider": "Google",
            "name": "Google Data Analytics Professional Certificate",
            "type": "Professional Certificate",
            "url": "https://grow.google/certificates/data-analytics/"
        }
    ],

    "docker": [
        {
            "provider": "Docker",
            "name": "Docker Certified Associate",
            "type": "Certification",
            "url": "https://www.docker.com/certification/"
        }
    ],

    "power bi": [
        {
            "provider": "Microsoft",
            "name": "Microsoft Certified: Power BI Data Analyst Associate",
            "type": "Certification",
            "url": "https://learn.microsoft.com/en-us/credentials/certifications/data-analyst-associate/"
        }
    ],

    "git": [
        {
            "provider": "GitHub",
            "name": "GitHub Foundations",
            "type": "Certification",
            "url": "https://resources.github.com/learn/pathways/skills/github-foundations/"
        }
    ],

    "javascript": [
        {
            "provider": "Meta",
            "name": "Meta Front-End Developer Professional Certificate",
            "type": "Professional Certificate",
            "url": "https://www.coursera.org/professional-certificates/meta-front-end-developer"
        }
    ],

    "react": [
        {
            "provider": "Meta",
            "name": "Meta Front-End Developer Professional Certificate",
            "type": "Professional Certificate",
            "url": "https://www.coursera.org/professional-certificates/meta-front-end-developer"
        }
    ],

    "linux": [
        {
            "provider": "Linux Foundation",
            "name": "Introduction to Linux",
            "type": "Course",
            "url": "https://training.linuxfoundation.org/training/introduction-to-linux/"
        }
    ]
}


CAREER_ROLES = {
    "sql": ["Data Analyst", "Data Engineer", "SQL Developer", "Backend Developer"],
    "python": ["Python Developer", "Data Analyst", "Data Scientist", "ML Engineer"],
    "machine learning": ["Machine Learning Engineer", "Data Scientist", "Applied Scientist"],
    "pandas": ["Data Analyst", "Python Developer", "Data Scientist"],
    "numpy": ["Python Developer", "Data Scientist", "Machine Learning Engineer"],
    "scikit-learn": ["Machine Learning Engineer", "Data Scientist", "Applied Scientist"],
    "git": ["Software Developer", "DevOps Engineer", "Data Engineer"],
    "docker": ["DevOps Engineer", "Cloud Engineer", "Backend Developer"],
    "fastapi": ["Backend Developer", "Python Developer", "API Developer"],
    "flask": ["Backend Developer", "Python Developer", "API Developer"],
    "rest apis": ["Backend Developer", "API Developer", "Integration Engineer"],
    "postgresql": ["Database Developer", "Backend Developer", "Data Engineer"],
    "aws": ["Cloud Engineer", "Cloud Developer", "DevOps Engineer", "Data Engineer"],
    "aws s3": ["Cloud Engineer", "Data Engineer", "Cloud Data Engineer"],
    "power bi": ["Power BI Developer", "Data Analyst", "Business Intelligence Analyst"],
    "statistics": ["Data Analyst", "Data Scientist", "Quantitative Analyst"],
    "data analysis": ["Data Analyst", "Business Intelligence Analyst", "Product Analyst"],
    "excel": ["Data Analyst", "Business Analyst", "Reporting Analyst"],
    "tensorflow": ["Machine Learning Engineer", "Deep Learning Engineer", "Data Scientist"],
    "javascript": ["Frontend Developer", "Full-Stack Developer", "Web Developer"],
    "react": ["Frontend Developer", "React Developer", "Full-Stack Developer"],
    "node.js": ["Backend Developer", "Node.js Developer", "Full-Stack Developer"],
    "mongodb": ["Backend Developer", "Database Developer", "Full-Stack Developer"],
    "java": ["Java Developer", "Backend Developer", "Software Engineer"],
    "c++": ["C++ Developer", "Systems Programmer", "Embedded Software Engineer"],
    "linux": ["Linux Administrator", "DevOps Engineer", "Site Reliability Engineer"],
    "ci/cd": ["DevOps Engineer", "Release Engineer", "Site Reliability Engineer"],
    "pyspark": ["Data Engineer", "Big Data Developer", "Data Platform Engineer"],
    "airflow": ["Data Engineer", "Analytics Engineer", "Data Platform Engineer"],
    "etl": ["ETL Developer", "Data Engineer", "Analytics Engineer"]
}


CAREER_JOB_PLATFORMS = {
    "LinkedIn Jobs": "https://www.linkedin.com/jobs/search/?keywords={query}&location={location}",
    "Indeed": "https://www.indeed.com/jobs?q={query}&l={location}",
    "Naukri": "https://www.naukri.com/{query}-jobs-in-{location}"
}


def pathway_skills(results):
    """Return only deterministic, non-matching technical requirements."""
    skills = []
    seen = set()

    for item in results or []:
        requirement = str(item.get("requirement", "")).strip().lower()
        status = str(item.get("status", "MISSING")).upper()

        if (
            not requirement
            or status == "MATCH"
            or requirement not in SKILL_ALIASES
            or requirement in {"certification"}
            or requirement in seen
        ):
            continue

        seen.add(requirement)
        skills.append({
            "name": requirement,
            "status": status,
            "explanation": item.get(
                "audit_reason",
                "The job description mentions this skill, but the resume does not provide complete direct evidence."
            ),
            "certifications": CAREER_CERTIFICATIONS.get(requirement, []),
            "roles": CAREER_ROLES.get(requirement, [])
        })

    return skills


def live_job_search_links(query, location):
    encoded_query = quote_plus(query)
    encoded_location = quote_plus(location)
    return [
        {
            "platform": platform,
            "label": "LIVE JOB SEARCH",
            "url": template.format(
                query=encoded_query,
                location=encoded_location
            )
        }
        for platform, template in CAREER_JOB_PLATFORMS.items()
    ]


def fetch_adzuna_jobs(query, location):
    app_id = os.getenv("ADZUNA_APP_ID", "").strip()
    app_key = os.getenv("ADZUNA_APP_KEY", "").strip()
    country = os.getenv("ADZUNA_COUNTRY", "in").strip() or "in"

    if not app_id or not app_key:
        return None

    url = (
        f"https://api.adzuna.com/v1/api/jobs/{quote_plus(country)}/search/1"
        f"?app_id={quote_plus(app_id)}&app_key={quote_plus(app_key)}"
        f"&results_per_page=10&what={quote_plus(query)}"
        f"&where={quote_plus(location)}&content-type=application/json"
    )

    try:
        response = urlopen(
            Request(url, headers={"User-Agent": "GA04-Fit-Analyzer/1.0"}),
            timeout=8
        )
        payload = json.loads(response.read().decode("utf-8"))
        jobs = []

        for job in payload.get("results", []):
            jobs.append({
                "title": job.get("title", ""),
                "company": (job.get("company") or {}).get("display_name", ""),
                "location": (job.get("location") or {}).get("display_name", ""),
                "created": job.get("created", ""),
                "url": job.get("redirect_url", "")
            })

        return jobs
    except Exception:
        return None


def build_career_pathway(results, location):
    skills = pathway_skills(results)
    skill_query = " ".join(skill["name"] for skill in skills[:3])
    query = skill_query or "technology jobs"
    jobs = fetch_adzuna_jobs(query, location)

    if jobs is not None:
        live_jobs = {
            "mode": "api",
            "label": "LIVE JOBS",
            "provider": "Adzuna",
            "query": query,
            "location": location,
            "jobs": jobs,
            "search_links": []
        }
    else:
        live_jobs = {
            "mode": "search_links",
            "label": "LIVE JOB SEARCH",
            "provider": None,
            "query": query,
            "location": location,
            "jobs": [],
            "search_links": live_job_search_links(query, location)
        }

    return {
        "skills": skills,
        "live_jobs": live_jobs,
        "notice": (
            "Job listings are fetched from the configured jobs API."
            if live_jobs["mode"] == "api"
            else "No jobs API credentials are configured. These links open live searches on established job platforms; no listings are fabricated."
        )
    }


# ============================================================
# PROJECTED FIT
# ============================================================
def calculate_projected_fit(results):

    total = len(results)

    current_points = sum(
        status_points(item.get("status", "MISSING"))
        for item in results
    )
    current_score = round(current_points / total * 100, 1) if total else 0

    development_items = []

    for item in results:
        status = str(item.get("status", "MISSING")).upper()
        if status == "MATCH":
            continue

        requirement = str(item.get("requirement", "")).strip()
        if not requirement:
            continue

        category = item.get("category", "General")
        guidance = DEVELOPMENT_GUIDANCE.get(requirement)

        if guidance:
            title = guidance.get("title", requirement.title())
            develop = guidance.get(
                "develop",
                f"Build practical evidence for {requirement}."
            )
            reason = guidance.get(
                "reason",
                "This requirement is not fully evidenced in the resume."
            )
            item_type = guidance.get("type", "SKILL")
        else:
            title = requirement.title()
            develop = (
                f"Learn {title}, practice it through a practical project, "
                "and add clear evidence of the skill to your resume."
            )
            reason = (
                f"{title} is required by the job description but the resume "
                "does not provide complete direct evidence."
            )
            item_type = (
                "SKILL"
                if category in {"Required Skills", "Preferred Skills", "Technical Skill"}
                else str(category).upper()
            )

        current_points_for_item = status_points(status)
        development_items.append({
            "requirement": requirement,
            "title": title,
            "category": category,
            "current_status": status,
            "develop": develop,
            "reason": reason,
            "type": item_type,
            "point_gain": 1.0 - current_points_for_item,
            "projected_status": "MATCH"
        })

    projected_points = sum(
        1.0
        for _ in results
    )
    projected_score = round(projected_points / total * 100, 1) if total else 0
    improvement = round(projected_score - current_score, 1)

    return {
        "current_score": current_score,
        "projected_score": projected_score,
        "improvement": improvement,
        "development_count": len(development_items),
        "development_items": development_items,
        "remaining_gaps": [],
        "projection_method": (
            "Scenario calculation assuming every currently missing or partial "
            "requirement is completed and becomes MATCH."
        ),
        "projection_note": (
            "Projected Fit represents the maximum scenario if all identified "
            "requirements are satisfied. It is not a guarantee of employment "
            "or selection."
        )
    }
# ============================================================
# JSON EXTRACTION
# ============================================================

def extract_json_from_response(content):

    if not content:
        raise ValueError(
            "Groq returned an empty response."
        )

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
        and
        end != -1
        and
        end > start
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
# LLM EXPLANATION
# ============================================================

def llm_explanation(
    results,
    resume_text,
    jd_text
):

    if not client:

        return {

            "summary":
                "LLM explanation is unavailable because "
                "GROQ_API_KEY is not configured. "
                "Evidence-based matching still works.",

            "gaps": [

                r["requirement"]

                for r in results

                if r["status"] != "MATCH"

            ],

            "questions": [

                f"Explain your experience with "
                f"{r['requirement']}."

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

Never invent resume information.

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

                    "role":
                        "system",

                    "content":
                        "Provide concise evidence-grounded "
                        "resume analysis. Never invent facts."

                },

                {

                    "role":
                        "user",

                    "content":
                        prompt

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

            "summary":
                str(
                    result.get(
                        "summary",
                        "No AI summary was returned."
                    )
                ),

            "gaps":
                result.get(
                    "gaps",
                    []
                ),

            "questions":
                result.get(
                    "questions",
                    []
                )

        }

    except Exception as e:

        return {

            "summary":
                "AI explanation could not be generated. "
                f"Reason: {str(e)}",

            "gaps": [

                r["requirement"]

                for r in results

                if r["status"] != "MATCH"

            ],

            "questions": [

                f"Explain your experience with "
                f"{r['requirement']}."

                for r in results

                if r["status"] != "MATCH"

            ][:7]

        }


# ============================================================
# TARGET SCORE CALCULATION
# ============================================================

def calculate_target_plan(
    results,
    current_score,
    target_score
):

    total = len(results)

    target_score = max(
        0,
        min(
            100,
            float(target_score)
        )
    )

    if total == 0:

        return {

            "target":
                target_score,

            "current":
                current_score,

            "reachable_with_development":
                False,

            "required_improvement":
                0,

            "points_needed":
                0,

            "selected_requirements":
                [],

            "projected_score":
                0,

            "total_developable_requirements":
                0

        }

    current_points = sum(

        status_points(
            item["status"]
        )

        for item in results

    )

    target_points = (

        target_score /
        100
        * total

    )

    points_needed = max(

        0,

        target_points -
        current_points

    )

    candidates = []

    for item in results:

        requirement = item["requirement"]

        if (

            item["status"] != "MATCH"

            and

            requirement in DEVELOPMENT_GUIDANCE

        ):

            gain = (

                1.0 -

                status_points(
                    item["status"]
                )

            )

            candidates.append({

                "requirement":
                    requirement,

                "title":
                    DEVELOPMENT_GUIDANCE[
                        requirement
                    ]["title"],

                "status":
                    item["status"],

                "gain":
                    gain,

                "category":
                    item["category"]

            })

    candidates.sort(

        key=lambda x: (

            -x["gain"],

            -CATEGORY_PRIORITY.get(

                x["category"],

                0

            )

        )

    )

    selected = []

    gained = 0.0

    for candidate in candidates:

        if gained >= points_needed:
            break

        selected.append(candidate)
        gained += candidate["gain"]

    projected_points = (

        current_points +
        gained

    )

    projected_score = round(

        projected_points /
        total
        * 100,

        1

    )

    reachable = (

        projected_score >= target_score

    )

    return {

        "target":
            round(
                target_score,
                1
            ),

        "current":
            round(
                current_score,
                1
            ),

        "required_improvement":
            round(

                points_needed /
                total
                * 100,

                1

            ),

        "points_needed":
            round(
                points_needed,
                2
            ),

        "selected_requirements":
            selected,

        "projected_score":
            projected_score,

        "reachable_with_development":
            reachable,

        "total_developable_requirements":
            len(candidates)

    }


# ============================================================
# CAREER AI FALLBACK HELPERS
# ============================================================

def get_gap_items(results):

    return [

        item

        for item in results

        if item.get("status") != "MATCH"

    ]


def get_development_items(
    results,
    development_plan
):

    items = []

    existing = development_plan.get(
        "development_items",
        []
    )

    if existing:

        return existing

    for item in results:

        requirement = item.get(
            "requirement",
            ""
        )

        if (
            item.get("status") != "MATCH"
            and
            requirement in DEVELOPMENT_GUIDANCE
        ):

            guidance = DEVELOPMENT_GUIDANCE[
                requirement
            ]

            items.append({

                "requirement":
                    requirement,

                "title":
                    guidance["title"],

                "develop":
                    guidance["develop"],

                "reason":
                    guidance["reason"],

                "current_status":
                    item.get(
                        "status",
                        "MISSING"
                    )

            })

    return items


def build_career_fallback(
    question,
    results,
    current_score,
    development_plan,
    target_plan=None
):

    question_lower = question.lower().strip()

    gaps = get_gap_items(results)

    development_items = get_development_items(
        results,
        development_plan
    )

    # --------------------------------------------------------
    # TARGET QUESTION
    # --------------------------------------------------------

    if target_plan:

        target = target_plan["target"]
        projected = target_plan["projected_score"]
        reachable = target_plan[
            "reachable_with_development"
        ]

        selected = target_plan[
            "selected_requirements"
        ]

        lines = [

            "✦ CAREER AI",
            "",
            "CURRENT SUITABILITY",
            f"{current_score:.0f}% → {target:.0f}%",
            "",
            "TARGET"

        ]

        if reachable:

            lines.append(
                f"{target:.0f}% is reachable under the "
                f"current scoring model."
            )

            if selected:

                titles = [
                    item["title"]
                    for item in selected
                ]

                lines.append(
                    "Focus on: "
                    + ", ".join(titles[:6])
                )

            lines.append(
                f"Projected suitability after those "
                f"improvements: {projected:.1f}%."
            )

        else:

            lines.append(
                f"{target:.0f}% cannot currently be reached "
                f"using only the identified development "
                f"opportunities."
            )

            lines.append(
                f"Maximum projected suitability from those "
                f"opportunities: {projected:.1f}%."
            )

            if selected:

                titles = [
                    item["title"]
                    for item in selected
                ]

                lines.append(
                    "Current development areas: "
                    + ", ".join(titles[:6])
                )

        lines.append(
            "This is a scenario from the application's "
            "scoring model, not a hiring prediction."
        )

        return "\n".join(lines)

    # --------------------------------------------------------
    # PROJECT QUESTION
    # --------------------------------------------------------

    project_words = [
        "project",
        "portfolio",
        "build",
        "what should i make",
        "what can i build"
    ]

    if any(
        word in question_lower
        for word in project_words
    ):

        titles = [
            item.get(
                "title",
                item.get(
                    "requirement",
                    ""
                )
            )

            for item in development_items
        ]

        if titles:

            skill_text = ", ".join(
                titles[:5]
            )

            return "\n".join([

                "✦ CAREER AI",
                "",
                "WHAT TO DO",
                "Build one practical data pipeline project.",
                f"Use the identified gaps: {skill_text}.",
                "A useful project can combine SQL, PySpark, "
                "ETL, Airflow and AWS S3.",
                "Document exactly which technologies you used "
                "so they can become resume evidence."

            ])

        return "\n".join([

            "✦ CAREER AI",
            "",
            "WHAT TO DO",
            "Build a project that demonstrates the "
            "requirements already identified by the job.",
            "Add clear technical evidence, measurable work "
            "and project outcomes to the resume."

        ])

    # --------------------------------------------------------
    # INTERVIEW QUESTION
    # --------------------------------------------------------

    interview_words = [
        "interview",
        "interview questions",
        "prepare for interview",
        "prepare me"
    ]

    if any(
        word in question_lower
        for word in interview_words
    ):

        lines = [

            "✦ CAREER AI",
            "",
            "INTERVIEW PREPARATION"

        ]

        if gaps:

            for index, item in enumerate(
                gaps[:6],
                start=1
            ):

                requirement = item.get(
                    "requirement",
                    "requirement"
                )

                lines.append(
                    f"{index}. Be ready to explain your "
                    f"experience with {requirement}."
                )

        else:

            lines.append(
                "No major requirement gaps were identified."
            )

            lines.append(
                "Prepare examples from your resume for "
                "each matched requirement."
            )

        return "\n".join(lines)

    # --------------------------------------------------------
    # WHY SCORE QUESTION
    # --------------------------------------------------------

    score_words = [
        "why",
        "score",
        "percentage",
        "low",
        "suitability"
    ]

    if (
        "score" in question_lower
        or
        "percentage" in question_lower
        or
        "suitability" in question_lower
    ):

        lines = [

            "✦ CAREER AI",
            "",
            "CURRENT SUITABILITY",
            f"{current_score:.0f}%",
            "",
            "KEY GAPS"

        ]

        if gaps:

            for item in gaps[:7]:

                requirement = item.get(
                    "requirement",
                    "Requirement"
                )

                status = item.get(
                    "status",
                    "MISSING"
                )

                lines.append(
                    f"• {requirement} — {status.lower()}."
                )

        else:

            lines.append(
                "No unmatched requirements were identified."
            )

        return "\n".join(lines)

    # --------------------------------------------------------
    # LEARNING / SKILL QUESTION
    # --------------------------------------------------------

    learning_words = [
        "learn",
        "study",
        "skill",
        "skills",
        "improve",
        "improvement",
        "gap",
        "gaps",
        "course",
        "technology",
        "technologies"
    ]

    if any(
        word in question_lower
        for word in learning_words
    ):

        lines = [

            "✦ CAREER AI",
            "",
            "CURRENT SUITABILITY",
            f"{current_score:.0f}%",
            "",
            "KEY GAPS"

        ]

        if gaps:

            for item in gaps[:7]:

                requirement = item.get(
                    "requirement",
                    "Requirement"
                )

                status = item.get(
                    "status",
                    "MISSING"
                )

                lines.append(
                    f"• {requirement} — {status.lower()}."
                )

            lines.extend([

                "",
                "WHAT TO DO"

            ])

            for index, item in enumerate(
                development_items[:6],
                start=1
            ):

                title = item.get(
                    "title",
                    item.get(
                        "requirement",
                        "Skill"
                    )
                )

                develop = item.get(
                    "develop",
                    "Build practical evidence for this requirement."
                )

                lines.append(
                    f"{index}. {title} — {develop}"
                )

        else:

            lines.append(
                "No major development gaps were identified."
            )

        return "\n".join(lines)

    # --------------------------------------------------------
    # GENERAL FREE-FORM QUESTION
    # --------------------------------------------------------

    lines = [

        "✦ CAREER AI",
        "",
        "CURRENT SUITABILITY",
        f"{current_score:.0f}%",
        "",
        "ANSWER"

    ]

    if gaps:

        lines.append(
            "Your question is being answered using the "
            "requirements and evidence from this analysis."
        )

        first_gap = gaps[0]

        lines.append(
            f"Relevant current gap: "
            f"{first_gap.get('requirement', 'requirement')} "
            f"({first_gap.get('status', 'MISSING').lower()})."
        )

        if development_items:

            first_development = development_items[0]

            lines.append(
                f"Suggested development area: "
                f"{first_development.get('title', 'identified gap')}."
            )

    else:

        lines.append(
            "No major requirement gaps were identified "
            "in the current analysis."
        )

    return "\n".join(lines)


# ============================================================
# CAREER AI TEXT CLEANUP
# ============================================================

def clean_career_answer(answer):

    if not answer:
        return ""

    answer = str(answer)

    answer = answer.replace(
        "**",
        ""
    )

    answer = answer.replace(
        "###",
        ""
    )

    answer = answer.replace(
        "##",
        ""
    )

    answer = answer.replace(
        "#",
        ""
    )

    answer = answer.replace(
        "```",
        ""
    )

    answer = answer.replace(
        "\\#",
        ""
    )

    answer = answer.replace(
        "\\*",
        ""
    )

    answer = re.sub(
        r"\n{3,}",
        "\n\n",
        answer
    )

    return answer.strip()


# ============================================================
# CAREER AI
# ============================================================

@app.post("/career-chat")
def career_chat():

    data = request.get_json(
        silent=True
    ) or {}

    question = str(

        data.get(
            "question",
            ""
        )

    ).strip()

    context = data.get(
        "context",
        {}
    )

    history = data.get(
        "history",
        []
    )

    if not question:

        return jsonify({

            "error":
                "Please enter a career question."

        }), 400

    if len(question) > 1000:

        return jsonify({

            "error":
                "Question is too long. Maximum is 1000 characters."

        }), 400

    results = context.get(
        "results",
        []
    )

    development_plan = context.get(
        "development_plan",
        {}
    ) or {}

    current_score = float(

        context.get(
            "current_score",
            0
        )

        or 0

    )

    # --------------------------------------------------------
    # TARGET DETECTION
    # --------------------------------------------------------

    target_match = re.search(

        r"\b(\d{1,3})\s*%",

        question

    )

    target_plan = None

    if target_match:

        target_score = float(

            target_match.group(1)

        )

        target_score = max(

            0,

            min(
                100,
                target_score
            )

        )

        target_plan = calculate_target_plan(

            results,

            current_score,

            target_score

        )

    # --------------------------------------------------------
    # ALWAYS BUILD FALLBACK
    # --------------------------------------------------------

    fallback_answer = build_career_fallback(

        question,

        results,

        current_score,

        development_plan,

        target_plan

    )

    # --------------------------------------------------------
    # IF GROQ IS NOT CONFIGURED
    # RETURN FALLBACK INSTEAD OF ERROR
    # --------------------------------------------------------

    if not client:

        return jsonify({

            "answer":
                fallback_answer,

            "target_plan":
                target_plan,

            "source":
                "deterministic_fallback"

        })

    # --------------------------------------------------------
    # COMPACT RESULTS
    # --------------------------------------------------------

    compact_results = []

    for item in results:

        compact_results.append({

            "requirement":
                item.get(
                    "requirement",
                    ""
                ),

            "category":
                item.get(
                    "category",
                    ""
                ),

            "status":
                item.get(
                    "status",
                    ""
                ),

            "resume_evidence":
                item.get(
                    "resume_evidence",
                    ""
                ),

            "resume_page":
                item.get(
                    "resume_page",
                    None
                ),

            "evidence_type":
                item.get(
                    "evidence_type",
                    ""
                ),

            "jd_evidence":
                item.get(
                    "jd_evidence",
                    ""
                ),

            "audit_reason":
                item.get(
                    "audit_reason",
                    ""
                )

        })

    # --------------------------------------------------------
    # DEVELOPMENT DATA
    # --------------------------------------------------------

    development_items = (

        development_plan.get(

            "development_items",

            []

        )

    )

    development_context = []

    for item in development_items:

        development_context.append({

            "requirement":
                item.get(
                    "requirement",
                    ""
                ),

            "title":
                item.get(
                    "title",
                    ""
                ),

            "category":
                item.get(
                    "category",
                    ""
                ),

            "current_status":
                item.get(
                    "current_status",
                    ""
                ),

            "develop":
                item.get(
                    "develop",
                    ""
                ),

            "reason":
                item.get(
                    "reason",
                    ""
                ),

            "point_gain":
                item.get(
                    "point_gain",
                    0
                )

        })

    # --------------------------------------------------------
    # TARGET CONTEXT
    # --------------------------------------------------------

    target_instruction = ""

    if target_plan:

        selected = target_plan[
            "selected_requirements"
        ]

        selected_text = "\n".join(

            f"- {item['title']} "
            f"({item['status']}, "
            f"+{item['gain']} point)"

            for item in selected

        )

        if not selected_text:

            selected_text = (
                "No currently developable requirement "
                "was identified for this target."
            )

        target_instruction = f"""

TARGET CALCULATION

Current suitability:
{target_plan['current']}%

Requested target:
{target_plan['target']}%

Points needed:
{target_plan['points_needed']}

Requirements selected by the scoring engine:

{selected_text}

Projected suitability:
{target_plan['projected_score']}%

Reachable:
{target_plan['reachable_with_development']}

IMPORTANT:

Use these exact calculated values.

Do not invent percentage increases.

Do not say that every skill gives a fixed percentage.

Do not promise hiring or selection.
"""

    # --------------------------------------------------------
    # SAFE HISTORY
    # --------------------------------------------------------

    safe_history = []

    if isinstance(
        history,
        list
    ):

        for item in history[-6:]:

            if not isinstance(
                item,
                dict
            ):

                continue

            role = item.get(
                "role",
                ""
            )

            content = str(

                item.get(
                    "content",
                    ""
                )

            )[:2000]

            if (

                role in {
                    "user",
                    "assistant"
                }

                and

                content

            ):

                safe_history.append({

                    "role":
                        role,

                    "content":
                        content

                })

    # ========================================================
    # IMPROVED FREE-FORM CAREER AI PROMPT
    # ========================================================

    prompt = f"""
You are Career AI inside an explainable
Candidate-Role Fit Engine.

The user may ask ANY free-form career question.

Do NOT restrict yourself to suggested questions.

Answer the actual user question directly.

User question:

{question}

Current suitability:
{current_score}%

Resume/job analysis data:

{json.dumps(
    compact_results,
    ensure_ascii=False,
    indent=2
)}

Development opportunities:

{json.dumps(
    development_context,
    ensure_ascii=False,
    indent=2
)}

{target_instruction}

IMPORTANT RULES:

1. The user can ask any career-related question.

2. Answer questions about skills, gaps, score,
learning paths, projects, certifications, resume evidence,
interview preparation and career development.

3. MATCH, PARTIAL and MISSING values from the
deterministic engine are authoritative.

4. Never invent resume information.

5. Never claim a skill is present when the evidence
does not show it.

6. A related skill is not the same as an exact skill.

7. If the user asks about improving the score,
use the application's calculated values.

8. If the user asks for a target percentage,
use the exact target calculation supplied above.

9. Never invent percentage gains.

10. If the requested target is unreachable using the
currently identified development opportunities,
clearly say so.

11. You may answer questions that are NOT related
to the suggested question buttons, as long as they
can be answered using the provided career context.

12. If the question cannot be answered from the
available resume/job context, say what information
is missing instead of inventing an answer.

13. Do not promise hiring, selection or employment.

14. Keep the response concise but actually answer
the question.

15. Return plain text only.

16. Do not use Markdown.

17. Do not use:
##
###
**
backticks
Markdown tables

18. Put every section on a separate line.

19. Put every bullet on a separate line.

20. Do not return an empty response.

Example structure:

✦ CAREER AI

ANSWER
Direct answer to the user's question.

WHAT TO DO
1. First practical step.
2. Second practical step.

TARGET
Only include this section when relevant.
"""

    # --------------------------------------------------------
    # GROQ CALL
    # --------------------------------------------------------

    try:

        messages = [

            {

                "role":
                    "system",

                "content":
                    (
                        "You are a free-form Career AI assistant. "
                        "Answer the user's actual question. "
                        "Do not restrict answers to suggested questions. "
                        "Use only the supplied resume/job evidence. "
                        "Return plain text only. "
                        "Never use Markdown. "
                        "Never use ## or **. "
                        "Never return an empty response."
                    )

            }

        ]

        messages.extend(
            safe_history
        )

        messages.append({

            "role":
                "user",

            "content":
                prompt

        })

        response = client.chat.completions.create(

            model=GROQ_MODEL,

            temperature=0.2,

            max_completion_tokens=1200,

            messages=messages

        )

        answer = ""

        if response.choices:

            message = response.choices[0].message

            if message:

                answer = (
                    message.content
                    or ""
                )

        answer = clean_career_answer(
            answer
        )

        # ----------------------------------------------------
        # CRITICAL FIX
        # IF GROQ RETURNS EMPTY, USE FALLBACK
        # ----------------------------------------------------

        if not answer:

            answer = fallback_answer

            source = "deterministic_fallback"

        else:

            source = "groq"

        return jsonify({

            "answer":
                answer,

            "target_plan":
                target_plan,

            "source":
                source

        })

    # --------------------------------------------------------
    # GROQ ERROR FALLBACK
    # --------------------------------------------------------

    except Exception as e:

        print(
            "Career AI Groq error:",
            str(e)
        )

        return jsonify({

            "answer":
                fallback_answer,

            "target_plan":
                target_plan,

            "source":
                "deterministic_fallback",

            "ai_warning":
                "Groq was unavailable, so the application "
                "used its evidence-based fallback response."

        })


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
# HEALTH
# ============================================================

@app.route("/health")
def health():

    return jsonify({

        "status":
            "ok",

        "application":
            "GA-04 Explainable Candidate-Role Fit Engine",

        "matching":
            "deterministic",

        "genai":
            (
                "enabled"
                if client
                else "not configured"
            )

    })


# ============================================================
# CAREER PATHWAY
# ============================================================

@app.post("/career-pathway")
def career_pathway():

    data = request.get_json(silent=True) or {}
    context = data.get("context", data)
    results = context.get("results", []) if isinstance(context, dict) else []
    location = str(data.get("location", "India")).strip() or "India"

    if len(location) > 120:
        return jsonify({
            "error": "Location is too long. Maximum is 120 characters."
        }), 400

    return jsonify(build_career_pathway(results, location))


# ============================================================
# ANALYZE
# ============================================================

@app.post("/analyze")
def analyze():

    if (

        "resume" not in request.files

        or

        "job" not in request.files

    ):

        return jsonify({

            "error":
                "Please upload both a resume PDF "
                "and a job description PDF."

        }), 400

    resume = request.files["resume"]
    job = request.files["job"]

    if (
        Path(resume.filename or "").suffix.lower() != ".pdf"
        or
        Path(job.filename or "").suffix.lower() != ".pdf"
    ):

        return jsonify({

            "error":
                "INVALID FILE TYPE — Please upload a supported document."

        }), 400

    resume_header = resume.stream.read(5)
    resume.stream.seek(0)
    job_header = job.stream.read(5)
    job.stream.seek(0)

    if (
        resume_header != b"%PDF-"
        or
        job_header != b"%PDF-"
    ):

        return jsonify({

            "error":
                "INVALID FILE TYPE — Please upload a supported document."

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

        # ----------------------------------------------------
        # EXTRACT PDFs
        # ----------------------------------------------------

        try:

            resume_pages = extract_pdf_pages(
                resume_path
            )

            job_pages = extract_pdf_pages(
                job_path
            )

        except Exception:

            return jsonify({

                "error":
                    "INVALID FILE TYPE — Please upload a supported document."

            }), 400

        resume_text = pages_to_text(
            resume_pages
        )

        jd_text = pages_to_text(
            job_pages
        )

        print(
            "Resume text length:",
            len(resume_text)
        )

        print(
            "JD text length:",
            len(jd_text)
        )

        if not resume_text:

            return jsonify({

                "error":
                    "No readable text found "
                    "in the resume PDF."

            }), 400

        if not jd_text:

            return jsonify({

                "error":
                    "No readable text found "
                    "in the job description PDF."

            }), 400

        resume_validation_error = validate_resume_document(
            resume_text
        )

        print(
            "Resume validation:",
            resume_validation_error or "valid"
        )

        if resume_validation_error:

            return jsonify({

                "error":
                    resume_validation_error

            }), 400

        job_validation_error = validate_job_document(
            jd_text
        )

        print(
            "JD validation:",
            job_validation_error or "valid"
        )

        if job_validation_error:

            return jsonify({

                "error":
                    job_validation_error

            }), 400

        # ----------------------------------------------------
        # REQUIREMENTS
        # ----------------------------------------------------

        requirements = extract_requirements(
            jd_text
        )

        results = []

        # ----------------------------------------------------
        # MATCH REQUIREMENTS
        # ----------------------------------------------------

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

            audit = {

                "decision":
                    status,

                "evidence_type":
                    evidence_type,

                "reason":
                    audit_reason,

                "jd_evidence":
                    jd_source_text,

                "resume_evidence":
                    resume_evidence,

                "resume_page":
                    page

            }

            results.append({

                "requirement":
                    requirement,

                "category":
                    category,

                "status":
                    status,

                "jd_evidence":
                    jd_source_text,

                "resume_evidence":
                    resume_evidence,

                "resume_page":
                    page,

                "evidence_type":
                    evidence_type,

                "audit_reason":
                    audit_reason,

                "audit":
                    audit

            })

        # ----------------------------------------------------
        # SCORE
        # ----------------------------------------------------

        score = calculate_score(
            results
        )

        # ----------------------------------------------------
        # DEVELOPMENT
        # ----------------------------------------------------

        development_plan = calculate_projected_fit(
            results
        )

        # ----------------------------------------------------
        # AI EXPLANATION
        # ----------------------------------------------------

        explanation = llm_explanation(

            results,

            resume_text,

            jd_text

        )

        # ----------------------------------------------------
        # DATABASE
        # ----------------------------------------------------

        save_evaluation(

            resume.filename,

            job.filename,

            score,

            results

        )

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return jsonify({

            "resume":
                resume.filename,

            "job":
                job.filename,

            "score":
                score,

            "requirements_count":
                len(results),

            "results":
                results,

            "explanation":
                explanation,

            "development_plan":
                development_plan,

            "bias_note":
                (
                    "Matching uses job-related evidence "
                    "such as skills, education and experience. "
                    "Name, gender, age, photo, religion, "
                    "marital status and address are not used."
                ),

            "engine": {

                "matching":
                    "deterministic",

                "scoring":
                    "MATCH=1, PARTIAL=0.5, MISSING=0",

                "llm_role":
                    (
                        "explanation, gap analysis "
                        "and interview preparation"
                    ),

                "development_projection":
                    (
                        "Scenario-based calculation of "
                        "potential fit after completing "
                        "learnable missing requirements."
                    )

            }

        })

    except Exception as e:

        return jsonify({

            "error":
                str(e)

        }), 500


# ============================================================
# FILE SIZE ERROR
# ============================================================

@app.errorhandler(413)
def file_too_large(error):

    return jsonify({

        "error":
            "File too large. Maximum size is 10 MB."

    }), 413


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

initialize_database()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )