import os
import json
from fastapi import FastAPI, Depends, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.config import settings
from app.database import engine, Base, get_db
from app.models import Profile, Repository, Analysis, GeneratedReadme
from app.schemas import ScanRequest, ReadmeRequest, ProfileOut, ReadmeOut, HistoryItem
from app.github import scan_github_portfolio
from app.heuristics import generate_heuristic_analysis, generate_heuristic_readme
from app.llm import analyze_portfolio_with_ai, generate_readme_with_ai

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="GitHub Portfolio Reviewer",
    description="Audits portfolios, checks documentation, and writes readmes using local rules or Gemini AI."
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/portfolio/scan", response_model=ProfileOut)
async def scan_portfolio(request: ScanRequest, db: Session = Depends(get_db)):
    """
    Scans a GitHub profile, runs heuristics/AI audit, and stores results.
    """
    username = request.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty.")
    
    # 1. Fetch GitHub data
    github_token = request.github_token or settings.GITHUB_TOKEN
    try:
        scan_data = await scan_github_portfolio(username, token=github_token)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GitHub scanning failed: {str(e)}")

    profile_info = scan_data["profile"]
    repos_list = scan_data["repositories"]

    # 2. Run analysis (Heuristics fallback or Gemini AI)
    gemini_key = request.gemini_api_key or settings.GEMINI_API_KEY
    analysis_data = None
    
    if gemini_key:
        # Attempt Gemini AI analysis
        analysis_data = analyze_portfolio_with_ai(profile_info, repos_list, api_key=gemini_key)
        
    if not analysis_data:
        # Fallback to local rule-based engine
        analysis_data = generate_heuristic_analysis(profile_info, repos_list)

    # 3. Save to database (Upsert pattern)
    # Remove existing profile to refresh all dependencies cleanly
    existing_profile = db.query(Profile).filter(Profile.username.ilike(username)).first()
    if existing_profile:
        db.delete(existing_profile)
        db.commit()

    db_profile = Profile(
        username=profile_info["username"],
        avatar_url=profile_info["avatar_url"],
        name=profile_info["name"],
        bio=profile_info["bio"],
        public_repos=profile_info["public_repos"],
        followers=profile_info["followers"],
        following=profile_info["following"]
    )
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)

    # Add repositories
    for repo in repos_list:
        db_repo = Repository(
            profile_id=db_profile.id,
            name=repo["name"],
            full_name=repo["full_name"],
            description=repo["description"],
            html_url=repo["html_url"],
            language=repo["language"],
            stars=repo["stars"],
            forks=repo["forks"],
            open_issues=repo["open_issues"],
            size=repo["size"],
            has_readme=repo["has_readme"],
            has_license=repo["has_license"],
            has_gitignore=repo["has_gitignore"],
            has_contributing=repo["has_contributing"],
            has_tests=repo["has_tests"],
            has_ci=repo["has_ci"],
            has_docker=repo["has_docker"]
        )
        db.add(db_repo)

    # Add analysis
    db_analysis = Analysis(
        profile_id=db_profile.id,
        score=analysis_data["score"],
        summary=analysis_data["summary"],
        improvements=json.dumps(analysis_data["improvements"]),
        recommended_projects=json.dumps(analysis_data["recommended_projects"]),
        is_ai_generated=analysis_data["is_ai_generated"]
    )
    db.add(db_analysis)
    db.commit()
    
    # Reload profile with relationships populated
    db.refresh(db_profile)
    
    # Convert DB model details to response schema structure
    # Pydantic will auto-convert strings to Dict/List if we map properly
    response_data = {
        "username": db_profile.username,
        "avatar_url": db_profile.avatar_url,
        "name": db_profile.name,
        "bio": db_profile.bio,
        "public_repos": db_profile.public_repos,
        "followers": db_profile.followers,
        "following": db_profile.following,
        "scanned_at": db_profile.scanned_at,
        "repositories": db_profile.repositories,
        "analysis": {
            "id": db_analysis.id,
            "score": db_analysis.score,
            "summary": db_analysis.summary,
            "improvements": json.loads(db_analysis.improvements),
            "recommended_projects": json.loads(db_analysis.recommended_projects),
            "is_ai_generated": db_analysis.is_ai_generated,
            "created_at": db_analysis.created_at
        }
    }
    return response_data

@app.get("/api/portfolio/{username}", response_model=ProfileOut)
def get_portfolio(username: str, db: Session = Depends(get_db)):
    """
    Retrieves a cached profile analysis from the local database.
    """
    db_profile = db.query(Profile).filter(Profile.username.ilike(username)).first()
    if not db_profile:
        raise HTTPException(status_code=404, detail=f"No cached analysis found for user '{username}'. Please scan first.")
        
    db_analysis = db_profile.analysis
    
    response_data = {
        "username": db_profile.username,
        "avatar_url": db_profile.avatar_url,
        "name": db_profile.name,
        "bio": db_profile.bio,
        "public_repos": db_profile.public_repos,
        "followers": db_profile.followers,
        "following": db_profile.following,
        "scanned_at": db_profile.scanned_at,
        "repositories": db_profile.repositories,
        "analysis": {
            "id": db_analysis.id,
            "score": db_analysis.score,
            "summary": db_analysis.summary,
            "improvements": json.loads(db_analysis.improvements),
            "recommended_projects": json.loads(db_analysis.recommended_projects),
            "is_ai_generated": db_analysis.is_ai_generated,
            "created_at": db_analysis.created_at
        }
    }
    return response_data

@app.get("/api/history", response_model=list[HistoryItem])
def get_history(db: Session = Depends(get_db)):
    """
    Returns lists of recently scanned github accounts.
    """
    profiles = db.query(Profile).order_by(Profile.scanned_at.desc()).limit(15).all()
    history = []
    for p in profiles:
        history.append({
            "username": p.username,
            "name": p.name,
            "avatar_url": p.avatar_url,
            "scanned_at": p.scanned_at,
            "score": p.analysis.score if p.analysis else 0,
            "repo_count": len(p.repositories)
        })
    return history

@app.post("/api/projects/readme", response_model=ReadmeOut)
def generate_readme(request: ReadmeRequest, db: Session = Depends(get_db)):
    """
    Generates or fetches a customized readme for a repository.
    """
    username = request.username.strip()
    repo_name = request.repo_name.strip()
    
    # Check if repository details are in our database
    db_profile = db.query(Profile).filter(Profile.username.ilike(username)).first()
    db_repo = None
    if db_profile:
        db_repo = db.query(Repository).filter(
            Repository.profile_id == db_profile.id,
            Repository.name.ilike(repo_name)
        ).first()

    language = db_repo.language if db_repo else "General"
    description = db_repo.description if db_repo else ""

    gemini_key = request.gemini_api_key or settings.GEMINI_API_KEY
    readme_content = None

    if gemini_key:
        readme_content = generate_readme_with_ai(
            repo_name=repo_name,
            language=language,
            description=description,
            custom_instructions=request.custom_instructions,
            api_key=gemini_key
        )
        is_ai = True
    else:
        readme_content = generate_heuristic_readme(
            repo_name=repo_name,
            language=language,
            description=description
        )
        is_ai = False

    if not readme_content:
        raise HTTPException(status_code=500, detail="README generation failed.")

    # Save to GeneratedReadme database cache
    db_readme = GeneratedReadme(
        username=username,
        repo_name=repo_name,
        content=readme_content,
        is_ai_generated=is_ai
    )
    db.add(db_readme)
    db.commit()
    db.refresh(db_readme)

    return db_readme

# Static Files Serving & Catchall SPA router
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
os.makedirs(os.path.join(static_dir, "css"), exist_ok=True)
os.makedirs(os.path.join(static_dir, "js"), exist_ok=True)

# Mount styles and scripts directly
app.mount("/css", StaticFiles(directory=os.path.join(static_dir, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(static_dir, "js")), name="js")

@app.get("/")
def read_index():
    index_path = os.path.join(static_dir, "index.html")
    if not os.path.exists(index_path):
        # Return a simple fallback placeholder until the UI files are created
        return {"message": "GitHub Portfolio Reviewer API is online. Loading UI..."}
    return FileResponse(index_path)
