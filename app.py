import streamlit as st
from google import genai
import json
import tempfile
import pandas as pd

# ----------------------------------------
# STREAMLIT SETUP
# ----------------------------------------
st.set_page_config(page_title="ATS Resume Ranker", layout="wide")

# HERO TITLE
st.markdown("""
<div style="text-align: center; padding: 10px;">
    <h1 style="color:#4CAF50; font-size: 42px;"> ATS Resume Ranking System</h1>
    <p style="font-size: 18px; color: #666;">AI-powered ranking using Gemini 2.5 Flash</p>
</div>
""", unsafe_allow_html=True)

# ----------------------------------------
# SIDEBAR: API KEY INPUT
# ----------------------------------------
st.sidebar.header("🔑 Configuration")
API_KEY = st.sidebar.text_input("Enter Gemini API Key:", type="password")

if API_KEY:
    client = genai.Client(api_key=API_KEY)
else:
    st.sidebar.warning("Please enter your API key.", icon="⚠️")
    st.stop()

# ----------------------------------------
# JOB DESCRIPTION
# ----------------------------------------
st.markdown("##  Job Description")
job_description = st.text_area("Paste the Job Description here...", height=250)

if not job_description:
    st.info("Enter a job description to continue.")
    st.stop()

# ----------------------------------------
# FILE UPLOAD
# ----------------------------------------
st.markdown("## 📂 Upload Resumes (PDF)")

uploaded_files = st.file_uploader(
    "Upload 1 or more PDF resumes",
    type=["pdf"],
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("Please upload resumes to proceed.")
    st.stop()

# ----------------------------------------
# ATS PROMPT
# ----------------------------------------
ats_prompt = """
You are an ATS (Applicant Tracking System). 
Evaluate the candidate's resume strictly in relation to the given job description.

Return ONLY this JSON:

{
  "ats_score": 0-100,
  "match_percentage": 0-100,
  "skills_missing": [],
  "strengths": [],
  "weaknesses": [],
  "summary": ""
}

Evaluation Rules:
1. Score ONLY based on skills, tools, and responsibilities clearly written in the resume.
2. The score MUST be relative to the job description provided.
3. Different job descriptions MUST produce different scores.
4. If the resume matches many core requirements, give high scores.
5. If partially matched, give medium scores.
6. If barely matched, give low scores.
7. This system MUST work for ALL types of resumes — HR, BDA, Data Analyst, ML, Cloud, etc.
8. Output STRICT JSON ONLY.
"""

# ----------------------------------------
# EVALUATION FUNCTION
# ----------------------------------------
def evaluate_resume(file_uri, job_description):
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            {"text": ats_prompt},
            {"file_data": {"file_uri": file_uri, "mime_type": "application/pdf"}},
            {"text": "Job Description:\n" + job_description}
        ]
    )

    raw = response.text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except:
        return {
            "ats_score": 0,
            "match_percentage": 0,
            "skills_missing": [],
            "strengths": [],
            "weaknesses": [],
            "summary": "Parsing error: Could not decode response."
        }

# ----------------------------------------
# PROCESSING RESUMES
# ----------------------------------------
st.markdown("##  Processing Resumes...")
results = []

progress = st.progress(0)
# progress bar only when files uploaded
if uploaded_files:
    progress = st.progress(0)
    step = 1 / len(uploaded_files)
else:
    st.error("No resumes were uploaded.")
    st.stop()

for idx, uploaded in enumerate(uploaded_files):
    # Save temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded.read())
        temp_path = tmp.name

    uploaded_gemini = client.files.upload(file=temp_path)

    score = evaluate_resume(uploaded_gemini.uri, job_description)

    results.append({
        "file": uploaded.name,
        "ats": score["ats_score"],
        "match": score["match_percentage"],
        "details": score
    })

    progress.progress((idx + 1) * step / 100)

# ----------------------------------------
# SORTING RESULTS
# ----------------------------------------
ranked = sorted(results, key=lambda x: x["match"], reverse=True)

st.success("Resumes ranked successfully!")

# ----------------------------------------
# DISPLAY RESULTS
# ----------------------------------------
st.markdown("## 🏆 Ranked Resumes")

# Build DataFrame
df = pd.DataFrame([{
    "Resume": r["file"],
    "Match %": r["match"],
    "ATS Score": r["ats"]
} for r in ranked])

st.dataframe(df, use_container_width=True)

# Detailed cards
st.markdown("## Detailed Resume Insights")

for r in ranked:
    st.markdown(f"""
    <div style="padding: 15px; border-radius: 10px; background: #F7F7F7; margin-bottom: 15px;">
        <h3 style="color:#333;"> {r['file']}</h3>
        <p><b>Match Score:</b> <span style="color:#4CAF50; font-weight:bold;">{r['match']}%</span></p>
        <p><b>ATS Score:</b> <span style="color:#2196F3; font-weight:bold;">{r['ats']}</span></p>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("View Full Evaluation"):
        st.json(r["details"])
