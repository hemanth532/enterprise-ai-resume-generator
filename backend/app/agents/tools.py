import re
from typing import Any, Dict


COMMON_SKILLS = [
    "Python",
    "SQL",
    "Power BI",
    "Tableau",
    "Pandas",
    "NumPy",
    "Machine Learning",
    "Data Analysis",
    "AWS",
    "Docker",
]


DEFAULT_KEYWORDS = [
    "Python",
    "SQL",
    "Power BI",
    "Tableau",
    "AWS",
    "Docker",
]


def infer_years(paragraphs):
    text = "\n".join(paragraphs)
    m = re.search(r"(\d{1,2})\+?\s+years", text, flags=re.I)
    if m:
        return int(m.group(1))
    m2 = re.search(r"(\d{1,2})\s+years?\s+of\s+experience", text, flags=re.I)
    if m2:
        return int(m2.group(1))
    return 0


def infer_domain(paragraphs):
    text = " ".join(paragraphs).lower()
    if "data" in text or "analytics" in text:
        return "Data Analytics"
    if "software" in text or "developer" in text:
        return "Software Engineering"
    if "machine learning" in text or "ml" in text:
        return "Machine Learning"
    return "General"


def infer_level(years: int):
    if years >= 10:
        return "Senior"
    if years >= 4:
        return "Mid-Level"
    if years > 0:
        return "Junior"
    return "Entry"


def profile_analysis_tool(parsed: Dict[str, Any]) -> Dict[str, Any]:
    paragraphs = parsed.get("paragraphs", [])
    skills_found = []
    text = "\n".join(paragraphs)
    for s in COMMON_SKILLS:
        if re.search(r"\b" + re.escape(s) + r"\b", text, flags=re.I):
            skills_found.append(s)
    years = infer_years(paragraphs)
    domain = infer_domain(paragraphs)
    level = infer_level(years)
    return {
        "candidate_level": level,
        "primary_domain": domain,
        "years_experience": years,
        "skills": skills_found,
    }


def ats_optimization_tool(parsed: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
    text = "\n".join(parsed.get("paragraphs", [])).lower()
    keywords = set(k.lower() for k in DEFAULT_KEYWORDS)
    for s in profile.get("skills", []):
        keywords.add(s.lower())
    present = [k for k in keywords if k in text]
    missing = [k for k in keywords if k not in text]
    ats_score = int((len(present) / max(1, len(keywords))) * 100)
    return {"missing_keywords": missing, "present_keywords": present, "ats_score": ats_score}


def resume_generation_tool(parsed: Dict[str, Any], profile: Dict[str, Any], ats: Dict[str, Any]) -> Dict[str, Any]:
    level = profile.get("candidate_level", "Professional")
    domain = profile.get("primary_domain", "")
    years = profile.get("years_experience", 0)
    skills = profile.get("skills", [])
    skills_str = ", ".join(skills[:5])
    summary = f"{level} {domain} professional with {years} years of experience. Skilled in {skills_str}. Proven ability to deliver results in cross-functional teams."
    paras = parsed.get("paragraphs", [])
    bullets = []
    for p in paras:
        if len(bullets) >= 6:
            break
        if len(p.split()) > 4:
            bullets.append(p.strip())
    if not bullets:
        bullets = ["Delivered measurable improvements to process and outcomes."]
    return {"summary": summary, "experience_bullets": bullets, "skills": skills}


def _safe_string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(item) for item in value if item is not None)
    return str(value)


def resume_review_tool(resume: Dict[str, Any]) -> Dict[str, Any]:
    issues = []
    summary = _safe_string(resume.get("summary", ""))
    if len(summary.split()) < 10:
        issues.append("Summary is short; consider expanding with concrete achievements.")
    if "  " in summary:
        issues.append("Double spaces found in summary.")
    experience_bullets = resume.get("experience_bullets", [])
    if experience_bullets is None:
        experience_bullets = []
    elif not isinstance(experience_bullets, list):
        experience_bullets = [experience_bullets]
    if len(experience_bullets) < 3:
        issues.append("Fewer than 3 experience bullets; add more quantifiable achievements.")
    return {"issues": issues, "passed": len(issues) == 0}


TOOL_DESCRIPTIONS = {
    "profile_analysis": {
        "name": "profile_analysis",
        "description": "Extract candidate seniority, domain, experience years, and core skills from parsed resume paragraphs.",
    },
    "ats_optimization": {
        "name": "ats_optimization",
        "description": "Identify missing ATS keywords and compute an ATS score based on resume text and candidate profile.",
    },
    "resume_generation": {
        "name": "resume_generation",
        "description": "Generate an enterprise-grade resume summary, experience bullets, and skills section from analysis inputs.",
    },
    "resume_review": {
        "name": "resume_review",
        "description": "Review generated resume content for grammar, consistency, and enterprise quality.",
    },
}
