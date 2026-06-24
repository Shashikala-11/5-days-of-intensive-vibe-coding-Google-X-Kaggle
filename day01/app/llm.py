import os
import json
import google.generativeai as genai
from typing import List, Dict, Any, Optional
from app.config import settings

def _get_genai_client(api_key: Optional[str] = None) -> Optional[Any]:
    """
    Initializes and returns a Gemini model instance if an API key is available.
    """
    key = api_key or settings.GEMINI_API_KEY
    if not key:
        return None
    try:
        genai.configure(api_key=key)
        # Using gemini-2.5-flash as the fast and cost-effective default
        return genai.GenerativeModel("gemini-2.5-flash")
    except Exception as e:
        print(f"Error configuring Google Generative AI client: {e}")
        return None

def analyze_portfolio_with_ai(
    profile_data: Dict[str, Any], 
    repositories: List[Dict[str, Any]], 
    api_key: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Calls Gemini API to audit the portfolio and suggest improvements/projects.
    """
    model = _get_genai_client(api_key)
    if not model:
        return None

    # Prepare repository and profile data for LLM
    cleaned_repos = []
    for r in repositories:
        cleaned_repos.append({
            "name": r.get("name"),
            "description": r.get("description"),
            "language": r.get("language"),
            "stars": r.get("stars", 0),
            "forks": r.get("forks", 0),
            "size_kb": r.get("size", 0),
            "files_present": {
                "README.md": r.get("has_readme", False),
                "LICENSE": r.get("has_license", False),
                "gitignore": r.get("has_gitignore", False),
                "CONTRIBUTING.md": r.get("has_contributing", False),
                "tests": r.get("has_tests", False),
                "ci_cd": r.get("has_ci", False),
                "dockerfile": r.get("has_docker", False),
            }
        })

    payload = {
        "username": profile_data.get("username"),
        "name": profile_data.get("name"),
        "bio": profile_data.get("bio"),
        "public_repos_count": profile_data.get("public_repos", 0),
        "followers": profile_data.get("followers", 0),
        "following": profile_data.get("following", 0),
        "repositories": cleaned_repos
    }

    system_instruction = (
        "You are an expert technical resume/portfolio auditor. Your goal is to review a developer's GitHub "
        "portfolio and provide feedback on project quality, missing files, documentation, and suggestions "
        "for improvements, along with tailored next-project recommendations. "
        "You must return your response strictly as a JSON object matching this schema:\n"
        "{\n"
        "  \"score\": 85, // integer 0-100 indicating portfolio quality/readiness\n"
        "  \"summary\": \"Detailed summary of their skills, primary languages, and strength/weakness profile...\",\n"
        "  \"improvements\": [\n"
        "    {\n"
        "      \"title\": \"Improvement title (e.g. Set up Testing in [Project Name])\",\n"
        "      \"description\": \"Detailed description of the issue, why it matters, and how to fix it.\",\n"
        "      \"category\": \"Category (e.g. Quality Assurance, Security, Documentation, DevOps, Architecture)\",\n"
        "      \"severity\": \"Severity level (High, Medium, or Low)\"\n"
        "    }\n"
        "  ],\n"
        "  \"recommended_projects\": [\n"
        "    {\n"
        "      \"title\": \"Next Project Title tailored to their skill gaps\",\n"
        "      \"description\": \"Brief description of the project idea, its complexity, and how it expands their portfolio.\",\n"
        "      \"tech_stack\": \"Comma separated tech stack list (e.g. Python, FastAPI, React, Redis)\",\n"
        "      \"difficulty\": \"Difficulty rating (Beginner, Medium, or Advanced)\",\n"
        "      \"tasks\": [\n"
        "         \"Task 1: Core setup steps...\",\n"
        "         \"Task 2: Architectural step...\",\n"
        "         \"Task 3: Testing/deployment step...\"\n"
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}"
    )

    prompt = f"Analyze this GitHub profile payload:\n{json.dumps(payload, indent=2)}"

    try:
        response = model.generate_content(
            contents=prompt,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.2
            },
            # Optional in some SDK versions, but we can pass instructions in the prompt if not supported.
            # google-generativeai >= 0.3.0 supports system_instruction on GenerativeModel instantiation, 
            # so we'll configure it dynamically or append it to prompt.
        )
        
        # In case the model was initialized without system instruction support, we can use a fallback format
        # but modern google-generativeai supports system instructions. Let's build the model with it:
        # Actually, let's create the model with instructions to ensure they are strictly followed:
        model_with_instruction = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=system_instruction
        )
        response = model_with_instruction.generate_content(
            contents=prompt,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.2
            }
        )
        
        data = json.loads(response.text)
        data["is_ai_generated"] = True
        return data
    except Exception as e:
        print(f"Gemini API Error in analyze_portfolio_with_ai: {e}")
        return None

def generate_readme_with_ai(
    repo_name: str,
    language: Optional[str],
    description: Optional[str],
    custom_instructions: Optional[str] = None,
    api_key: Optional[str] = None
) -> Optional[str]:
    """
    Calls Gemini API to generate a complete, professional, custom README.md for a repository.
    """
    model = _get_genai_client(api_key)
    if not model:
        return None

    lang_text = language or "General / Multi-language"
    desc_text = description or "A developer project designed for performance and clean architecture."
    instructions = custom_instructions or "Create a standard, highly informative, and beautiful readme."

    prompt = (
        f"You are a technical writer. Write a premium, professional, and exhaustive README.md file "
        f"for a GitHub repository named '{repo_name}'.\n"
        f"Primary Language/Stack: {lang_text}\n"
        f"Description: {desc_text}\n"
        f"Custom user requests: {instructions}\n\n"
        f"Requirements:\n"
        f"1. Do NOT wrap the entire output in a markdown block (e.g. ```markdown ... ```). "
        f"Provide the raw markdown text directly so it is ready to be saved.\n"
        f"2. Use clean markdown formatting, headers, lists, and tables where appropriate.\n"
        f"3. Include typical sections: Project Name, Description, Getting Started (Prerequisites & Installation), "
        f"Usage, Testing, Project Structure, Contributing, and License.\n"
        f"4. Add specific setup instructions corresponding to the language: {lang_text}."
    )

    try:
        response = model.generate_content(
            contents=prompt,
            generation_config={
                "temperature": 0.3
            }
        )
        return response.text
    except Exception as e:
        print(f"Gemini API Error in generate_readme_with_ai: {e}")
        return None
