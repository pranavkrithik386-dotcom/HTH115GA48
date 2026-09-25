# Resume Fit Analyzer

A simple Flask MVP for the GA-04 Explainable Candidate-Role Fit Engine.

## Features
- Upload resume PDF and job description PDF
- Extract PDF text
- Detect job-related requirements
- Requirement-level MATCH / PARTIAL / MISSING
- Evidence from the resume
- Deterministic fit percentage
- Optional Groq LLM explanation
- Skill gaps and interview questions
- Basic bias safeguard
- SQLite evaluation history

## Run

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python app.py
```

Open http://127.0.0.1:5000

## API
POST /analyze with multipart fields:
- resume
- job

## Demo data
- data/resumes/ contains 10 synthetic resumes
- data/jobs/ contains 3 synthetic job descriptions

# HTH115GA48 — Explainable Candidate-Role Fit Engine

## 🌐 Live Demo

👉 **[Open the Live Web Application](https://hth115ga48-1.onrender.com)**

## 📌 Project

An explainable AI-powered Candidate-Role Fit Engine that analyzes resumes against job descriptions and provides evidence-backed matching, skill gaps, interview questions, career development, certifications, future scope, and job-search pathways.

