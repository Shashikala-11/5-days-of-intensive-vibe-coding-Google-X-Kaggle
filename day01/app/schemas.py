from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ScanRequest(BaseModel):
    username: str
    github_token: Optional[str] = None
    gemini_api_key: Optional[str] = None

class ReadmeRequest(BaseModel):
    username: str
    repo_name: str
    gemini_api_key: Optional[str] = None
    custom_instructions: Optional[str] = None

class RepositoryBase(BaseModel):
    name: str
    full_name: str
    description: Optional[str] = None
    html_url: str
    language: Optional[str] = None
    stars: int
    forks: int
    open_issues: int
    size: int
    has_readme: bool
    has_license: bool
    has_gitignore: bool
    has_contributing: bool
    has_tests: bool
    has_ci: bool
    has_docker: bool

class RepositoryOut(RepositoryBase):
    id: int
    profile_id: int

    class Config:
        from_attributes = True

class AnalysisOut(BaseModel):
    id: int
    score: int
    summary: str
    improvements: List[Dict[str, Any]] # Decoded JSON
    recommended_projects: List[Dict[str, Any]] # Decoded JSON
    is_ai_generated: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ProfileOut(BaseModel):
    username: str
    avatar_url: Optional[str] = None
    name: Optional[str] = None
    bio: Optional[str] = None
    public_repos: int
    followers: int
    following: int
    scanned_at: datetime
    repositories: List[RepositoryOut] = []
    analysis: Optional[AnalysisOut] = None

    class Config:
        from_attributes = True

class HistoryItem(BaseModel):
    username: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    scanned_at: datetime
    score: int
    repo_count: int

class ReadmeOut(BaseModel):
    username: str
    repo_name: str
    content: str
    is_ai_generated: bool
    created_at: datetime

    class Config:
        from_attributes = True
