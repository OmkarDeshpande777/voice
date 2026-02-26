"""Resume analysis service — PDF extraction, skill detection, Groq-powered classification & question generation."""
import json
import os
import re
from pathlib import Path
from typing import List, Optional, Tuple

import httpx
import pdfplumber
from dotenv import load_dotenv

# Load .env
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "gpt-oss")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# ---------------------------------------------------------------------------
# Comprehensive skills dictionary (used for fast token-based extraction)
# ---------------------------------------------------------------------------
SKILLS_SET = {
    # Programming Languages
    "python", "java", "javascript", "typescript", "c", "c++", "c#", "ruby",
    "php", "swift", "kotlin", "go", "golang", "rust", "scala", "perl",
    "r", "matlab", "dart", "lua", "haskell", "elixir", "clojure",
    # Web / Frontend
    "html", "css", "sass", "less", "react", "reactjs", "react.js", "angular",
    "angularjs", "vue", "vue.js", "vuejs", "svelte", "next.js", "nextjs",
    "nuxt.js", "gatsby", "tailwind", "bootstrap", "jquery", "webpack",
    "vite", "redux", "graphql",
    # Backend / Frameworks
    "node.js", "nodejs", "express", "express.js", "django", "flask",
    "fastapi", "spring", "spring boot", "springboot", ".net", "asp.net",
    "laravel", "rails", "ruby on rails", "gin", "fiber", "nestjs",
    # Databases
    "sql", "mysql", "postgresql", "postgres", "mongodb", "sqlite",
    "oracle", "redis", "cassandra", "dynamodb", "firebase", "supabase",
    "elasticsearch", "neo4j", "mariadb", "couchdb",
    # Cloud & DevOps
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "k8s",
    "terraform", "ansible", "jenkins", "ci/cd", "github actions",
    "gitlab ci", "circleci", "cloudformation", "helm", "prometheus",
    "grafana", "nginx", "apache", "linux", "bash", "shell scripting",
    # Data & ML
    "machine learning", "deep learning", "tensorflow", "pytorch", "keras",
    "scikit-learn", "sklearn", "pandas", "numpy", "scipy", "matplotlib",
    "seaborn", "nlp", "natural language processing", "computer vision",
    "opencv", "data science", "data analysis", "data engineering",
    "spark", "hadoop", "airflow", "databricks", "tableau", "power bi",
    "etl", "big data",
    # Tools & Misc
    "git", "github", "gitlab", "bitbucket", "jira", "confluence",
    "agile", "scrum", "rest", "restful", "api", "microservices",
    "rabbitmq", "kafka", "celery", "websockets", "oauth", "jwt",
    "figma", "photoshop", "illustrator",
    # Mobile
    "android", "ios", "flutter", "react native", "xamarin", "swiftui",
    # Testing
    "unit testing", "pytest", "jest", "mocha", "selenium", "cypress",
    "playwright", "testng", "junit",
    # Security
    "cybersecurity", "penetration testing", "owasp", "encryption",
    "ssl", "tls", "firewalls",
}

# Job role mappings based on skills
JOB_MAPPINGS = {
    "python": ["Python Developer", "Data Scientist", "Backend Developer"],
    "java": ["Java Developer", "Software Engineer", "Full Stack Developer"],
    "javascript": ["Frontend Developer", "Full Stack Developer", "Web Developer"],
    "typescript": ["Frontend Developer", "Full Stack Developer", "Web Developer"],
    "react": ["React Developer", "Frontend Developer", "UI Developer"],
    "reactjs": ["React Developer", "Frontend Developer", "UI Developer"],
    "angular": ["Angular Developer", "Frontend Developer", "UI Developer"],
    "vue": ["Vue.js Developer", "Frontend Developer", "UI Developer"],
    "node.js": ["Backend Developer", "Full Stack Developer", "Node.js Developer"],
    "nodejs": ["Backend Developer", "Full Stack Developer", "Node.js Developer"],
    "django": ["Python Developer", "Backend Developer", "Full Stack Developer"],
    "flask": ["Python Developer", "Backend Developer", "API Developer"],
    "fastapi": ["Python Developer", "Backend Developer", "API Developer"],
    "spring": ["Java Developer", "Backend Developer", "Enterprise Developer"],
    "sql": ["Database Administrator", "Data Analyst", "Backend Developer"],
    "mongodb": ["Backend Developer", "Database Engineer", "Full Stack Developer"],
    "aws": ["Cloud Engineer", "DevOps Engineer", "Solutions Architect"],
    "azure": ["Cloud Engineer", "DevOps Engineer", "Azure Architect"],
    "gcp": ["Cloud Engineer", "DevOps Engineer", "Solutions Architect"],
    "docker": ["DevOps Engineer", "Cloud Engineer", "Systems Engineer"],
    "kubernetes": ["DevOps Engineer", "Cloud Architect", "Platform Engineer"],
    "machine learning": ["ML Engineer", "Data Scientist", "AI Engineer"],
    "deep learning": ["ML Engineer", "Data Scientist", "AI Research Engineer"],
    "tensorflow": ["ML Engineer", "Data Scientist", "AI Engineer"],
    "pytorch": ["ML Engineer", "Data Scientist", "AI Research Engineer"],
    "data science": ["Data Scientist", "Data Analyst", "ML Engineer"],
    "flutter": ["Flutter Developer", "Mobile Developer", "Cross-Platform Developer"],
    "react native": ["Mobile Developer", "React Native Developer", "Cross-Platform Developer"],
    "android": ["Android Developer", "Mobile Developer", "Software Engineer"],
    "ios": ["iOS Developer", "Mobile Developer", "Software Engineer"],
    "cybersecurity": ["Security Engineer", "Penetration Tester", "Security Analyst"],
    "git": ["Software Engineer", "Developer", "DevOps Engineer"],
    "linux": ["System Administrator", "DevOps Engineer", "Backend Developer"],
}

# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _clean_text(text: str) -> str:
    """Remove URLs, hashtags, mentions, special chars from resume text."""
    text = re.sub(r"http\S+\s?", " ", text)
    text = re.sub(r"RT|cc", " ", text)
    text = re.sub(r"#\S+\s?", " ", text)
    text = re.sub(r"@\S+", " ", text)
    text = re.sub(r"[%s]" % re.escape("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"), " ", text)
    text = re.sub(r"[^\x00-\x7f]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_text_from_pdf(pdf_path: str) -> Optional[str]:
    """Extract raw text from a PDF file using pdfplumber."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
            return "\n".join(pages).strip() or None
    except Exception as e:
        print(f"[RESUME] PDF extraction error: {e}")
        return None


def extract_skills(text: str) -> List[str]:
    """Token / bigram match against known skills list."""
    if not text:
        return []

    lower = text.lower()
    found: set = set()

    # Check each skill (handles multi-word skills too)
    for skill in SKILLS_SET:
        # Use word-boundary regex so "c" doesn't match inside "react"
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, lower):
            found.add(skill)

    return sorted(found)


def recommend_jobs(skills: List[str], top_n: int = 5) -> List[str]:
    """Map extracted skills → job recommendations."""
    jobs: set = set()
    for skill in skills:
        key = skill.lower()
        if key in JOB_MAPPINGS:
            jobs.update(JOB_MAPPINGS[key])
    return sorted(jobs)[:top_n]


# ---------------------------------------------------------------------------
# Groq LLM helpers
# ---------------------------------------------------------------------------

def _groq_chat(system: str, user: str, temperature: float = 0.7, max_tokens: int = 2048) -> Optional[str]:
    """Send a chat completion request to Groq and return the assistant message."""
    if not GROQ_API_KEY:
        return None
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    try:
        resp = httpx.post(GROQ_API_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[RESUME] Groq call failed: {e}")
        return None


def predict_category_llm(resume_text: str) -> str:
    """Use Groq LLM to predict the resume's job-role category."""
    system = "You are an expert recruiter. Given resume text, predict the single best job-role category. Reply with ONLY the category name (e.g. 'Data Science', 'Web Development', 'DevOps', 'Mobile Development', 'Cybersecurity', 'Software Engineering', 'Frontend Development', 'Backend Development', 'Full Stack Development', 'Machine Learning', 'Cloud Engineering')."
    cleaned = _clean_text(resume_text)[:3000]  # keep prompt reasonable
    result = _groq_chat(system, f"Resume:\n{cleaned}")
    return result.strip('" \n') if result else "General Software Engineering"


def generate_resume_questions(skills: List[str], category: str, count: int = 5) -> List[dict]:
    """Generate targeted interview questions based on extracted skills and predicted role."""
    if not skills:
        return []

    skills_str = ", ".join(skills[:20])  # cap to 20 for prompt length

    system = "You are an expert technical interviewer. Generate interview questions that specifically test a candidate's depth of knowledge on the skills found in their resume."

    user_prompt = f"""The candidate's resume was classified as: **{category}**
Skills found: {skills_str}

Generate exactly {count} targeted technical interview questions based on these specific skills.
Questions should range from intermediate to advanced difficulty.
Each question should directly relate to one or more of the listed skills.

Respond ONLY with a JSON array. Each item must have:
- "text": the question text
- "difficulty": "easy", "medium", or "hard"
- "tips": one brief tip for answering well (max 20 words)
- "related_skills": list of skills this question tests

JSON array only, no other text:"""

    raw = _groq_chat(system, user_prompt, temperature=0.8)
    if not raw:
        return _fallback_questions(skills, count)

    # Strip markdown fences if present
    text = raw
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])

    try:
        questions = json.loads(text)
        if isinstance(questions, list):
            return [
                {
                    "text": q.get("text", ""),
                    "difficulty": q.get("difficulty", "medium"),
                    "tips": q.get("tips", ""),
                    "related_skills": q.get("related_skills", []),
                }
                for q in questions
                if q.get("text")
            ][:count]
    except json.JSONDecodeError:
        print("[RESUME] Failed to parse Groq response as JSON, using fallback questions.")

    return _fallback_questions(skills, count)


def _fallback_questions(skills: List[str], count: int) -> List[dict]:
    """Provide basic questions when LLM is unavailable."""
    templates = [
        "Explain the key features of {skill} and how you have used it in your projects.",
        "What are the advantages and disadvantages of using {skill}?",
        "Describe a challenging problem you solved using {skill}.",
        "How does {skill} compare to its alternatives?",
        "What best practices do you follow when working with {skill}?",
        "Can you walk me through a project where {skill} was critical?",
        "What are common pitfalls when using {skill} and how do you avoid them?",
    ]
    questions = []
    for i, skill in enumerate(skills[:count]):
        tmpl = templates[i % len(templates)]
        questions.append({
            "text": tmpl.format(skill=skill),
            "difficulty": "medium",
            "tips": f"Focus on practical experience with {skill}.",
            "related_skills": [skill],
        })
    return questions[:count]


# ---------------------------------------------------------------------------
# High-level orchestrator used by the router
# ---------------------------------------------------------------------------

def analyse_resume(pdf_path: str) -> Tuple[Optional[str], List[str], str, List[str]]:
    """
    Full pipeline: extract text → skills → category → jobs.
    Returns (extracted_text, skills, category, recommended_jobs).
    """
    text = extract_text_from_pdf(pdf_path)
    if not text:
        return None, [], "Unknown", []

    skills = extract_skills(text)
    category = predict_category_llm(text)
    jobs = recommend_jobs(skills)
    return text, skills, category, jobs
