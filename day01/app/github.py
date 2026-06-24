import httpx
import asyncio
from typing import Dict, List, Any, Optional

async def get_github_client(token: Optional[str] = None) -> httpx.AsyncClient:
    """
    Creates an async HTTP client with standard GitHub API headers.
    """
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "github-portfolio-reviewer"
    }
    if token:
        headers["Authorization"] = f"token {token}"
    
    return httpx.AsyncClient(headers=headers, timeout=15.0)

async def fetch_profile(client: httpx.AsyncClient, username: str) -> Dict[str, Any]:
    """
    Fetches user profile details from the GitHub API.
    """
    url = f"https://api.github.com/users/{username}"
    response = await client.get(url)
    
    if response.status_code == 404:
        raise ValueError(f"GitHub user '{username}' not found.")
    elif response.status_code != 200:
        raise Exception(f"GitHub API Error: {response.status_code} - {response.text}")
        
    return response.json()

async def fetch_repositories(client: httpx.AsyncClient, username: str) -> List[Dict[str, Any]]:
    """
    Fetches the public repositories list for a user.
    """
    # Grab up to 50 repos to keep requests within reasonable limits
    url = f"https://api.github.com/users/{username}/repos?per_page=50&sort=updated"
    response = await client.get(url)
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch repositories: {response.status_code} - {response.text}")
        
    return response.json()

async def audit_repository_contents(client: httpx.AsyncClient, owner: str, repo_name: str) -> Dict[str, bool]:
    """
    Queries the root contents of a repository to check for key configuration files and folders.
    """
    url = f"https://api.github.com/repos/{owner}/{repo_name}/contents"
    
    audit = {
        "has_readme": False,
        "has_license": False,
        "has_gitignore": False,
        "has_contributing": False,
        "has_tests": False,
        "has_ci": False,
        "has_docker": False
    }
    
    try:
        response = await client.get(url)
        if response.status_code != 200:
            return audit # Return all false if repo is empty or API blocks it
            
        items = response.json()
        if not isinstance(items, list):
            return audit
            
        for item in items:
            name = item.get("name", "").lower()
            item_type = item.get("type", "") # "file" or "dir"
            
            if name.startswith("readme"):
                audit["has_readme"] = True
            elif "license" in name:
                audit["has_license"] = True
            elif name == ".gitignore":
                audit["has_gitignore"] = True
            elif "contributing" in name:
                audit["has_contributing"] = True
            elif "dockerfile" in name:
                audit["has_docker"] = True
            
            # Check for tests folder
            if item_type == "dir" and name in ["test", "tests", "spec", "__tests__", "testing"]:
                audit["has_tests"] = True
            
            # Check for test files in root (e.g. test_main.py, app.test.js)
            if item_type == "file" and ("test" in name or "spec" in name):
                # Ensure it's not a config file like jest.config.js
                if not name.endswith("config.js") and not name.endswith("config.ts"):
                    audit["has_tests"] = True
                    
            # Check for CI folders (GitHub actions)
            if name == ".github" and item_type == "dir":
                audit["has_ci"] = True
                
    except Exception as e:
        print(f"Error auditing repository contents for {owner}/{repo_name}: {e}")
        
    return audit

async def scan_github_portfolio(
    username: str, 
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Orchestrates the retrieval of user profile and repository audits.
    """
    async with await get_github_client(token) as client:
        # 1. Fetch user info
        profile = await fetch_profile(client, username)
        
        # 2. Fetch all repos
        repos = await fetch_repositories(client, username)
        
        # We only scan up to 12 repositories to prevent hitting rate limits and timeouts
        repos_to_scan = repos[:12]
        
        # 3. Fetch root directories of each repo to audit structure (run concurrently in batches)
        sem = asyncio.Semaphore(4) # Limit concurrency to 4 simultaneous scans
        
        async def worker(repo):
            async with sem:
                audit_results = await audit_repository_contents(client, username, repo["name"])
                return {
                    "name": repo["name"],
                    "full_name": repo["full_name"],
                    "description": repo.get("description"),
                    "html_url": repo["html_url"],
                    "language": repo.get("language"),
                    "stars": repo.get("stargazers_count", 0),
                    "forks": repo.get("forks_count", 0),
                    "open_issues": repo.get("open_issues_count", 0),
                    "size": repo.get("size", 0),
                    **audit_results
                }
                
        tasks = [worker(repo) for repo in repos_to_scan]
        scanned_repos = await asyncio.gather(*tasks)
        
        return {
            "profile": {
                "username": profile["login"],
                "avatar_url": profile.get("avatar_url"),
                "name": profile.get("name"),
                "bio": profile.get("bio"),
                "public_repos": profile.get("public_repos", 0),
                "followers": profile.get("followers", 0),
                "following": profile.get("following", 0)
            },
            "repositories": scanned_repos
        }
