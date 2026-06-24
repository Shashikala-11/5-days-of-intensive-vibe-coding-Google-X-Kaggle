from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    avatar_url = Column(String, nullable=True)
    name = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    public_repos = Column(Integer, default=0)
    followers = Column(Integer, default=0)
    following = Column(Integer, default=0)
    scanned_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    repositories = relationship("Repository", back_populates="profile", cascade="all, delete-orphan")
    analysis = relationship("Analysis", back_populates="profile", uselist=False, cascade="all, delete-orphan")

class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    name = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    html_url = Column(String, nullable=False)
    language = Column(String, nullable=True)
    stars = Column(Integer, default=0)
    forks = Column(Integer, default=0)
    open_issues = Column(Integer, default=0)
    size = Column(Integer, default=0)
    
    # Audit indicators
    has_readme = Column(Boolean, default=False)
    has_license = Column(Boolean, default=False)
    has_gitignore = Column(Boolean, default=False)
    has_contributing = Column(Boolean, default=False)
    has_tests = Column(Boolean, default=False)
    has_ci = Column(Boolean, default=False)
    has_docker = Column(Boolean, default=False)

    profile = relationship("Profile", back_populates="repositories")

class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False, unique=True)
    score = Column(Integer, default=0)
    summary = Column(Text, nullable=True)
    improvements = Column(Text, nullable=True) # Stored as JSON string
    recommended_projects = Column(Text, nullable=True) # Stored as JSON string
    is_ai_generated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("Profile", back_populates="analysis")

class GeneratedReadme(Base):
    __tablename__ = "generated_readmes"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True, nullable=False)
    repo_name = Column(String, index=True, nullable=False)
    content = Column(Text, nullable=False)
    is_ai_generated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
