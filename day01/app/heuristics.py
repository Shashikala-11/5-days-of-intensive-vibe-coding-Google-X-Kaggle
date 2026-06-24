import json
from typing import List, Dict, Any
from datetime import datetime

def calculate_portfolio_score(profile_data: Dict[str, Any], repositories: List[Dict[str, Any]]) -> int:
    """
    Computes a score from 0 to 100 representing portfolio completeness and best practices.
    """
    if not repositories:
        return 30
    
    score = 30 # Base score for having an active account
    
    # Check profile metadata
    if profile_data.get("bio"):
        score += 3
    if profile_data.get("public_repos", 0) > 5:
        score += 4
    if profile_data.get("followers", 0) > 5:
        score += 3

    # Repo checks
    total_repo_score = 0
    for repo in repositories:
        repo_score = 0
        if repo.get("has_readme"):
            repo_score += 15
        if repo.get("has_license"):
            repo_score += 8
        if repo.get("has_gitignore"):
            repo_score += 5
        if repo.get("has_contributing"):
            repo_score += 4
        if repo.get("has_tests"):
            repo_score += 15
        if repo.get("has_ci"):
            repo_score += 10
        if repo.get("has_docker"):
            repo_score += 5
        if repo.get("description"):
            repo_score += 5
        
        # Star bonus
        stars = repo.get("stars", 0)
        repo_score += min(stars * 2, 8)
        
        total_repo_score += repo_score
        
    avg_repo_score = total_repo_score / len(repositories)
    # Scale avg_repo_score (max possible repo_score is about 75)
    normalized_repo_score = min((avg_repo_score / 65) * 60, 60)
    
    final_score = int(min(score + normalized_repo_score, 100))
    return final_score

def generate_suggestions(repositories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Scans repositories for missing items and generates actionable, structured improvement recommendations.
    """
    suggestions = []
    if not repositories:
        return [
            {
                "title": "Create public repositories",
                "description": "This profile has no public repositories. To showcase your skills, upload projects or make existing ones public.",
                "category": "Repository Management",
                "severity": "High"
            }
        ]

    total = len(repositories)
    missing_readme = [r for r in repositories if not r.get("has_readme")]
    missing_license = [r for r in repositories if not r.get("has_license")]
    missing_gitignore = [r for r in repositories if not r.get("has_gitignore")]
    missing_contributing = [r for r in repositories if not r.get("has_contributing")]
    missing_tests = [r for r in repositories if not r.get("has_tests")]
    missing_ci = [r for r in repositories if not r.get("has_ci")]
    missing_docker = [r for r in repositories if not r.get("has_docker")]
    missing_desc = [r for r in repositories if not r.get("description")]

    # 1. README Suggestion
    if len(missing_readme) > 0:
        pct = int((len(missing_readme) / total) * 100)
        repo_names = ", ".join([r["name"] for r in missing_readme[:3]])
        suffix = "..." if len(missing_readme) > 3 else ""
        suggestions.append({
            "title": "Add README.md to projects",
            "description": f"{pct}% of your repositories ({repo_names}{suffix}) are missing a README.md. A README is critical for explaining installation, usage, and project purpose to visitors.",
            "category": "Documentation",
            "severity": "High"
        })

    # 2. LICENSE Suggestion
    if len(missing_license) / total > 0.4:
        pct = int((len(missing_license) / total) * 100)
        suggestions.append({
            "title": "Establish project licensing",
            "description": f"About {pct}% of your projects lack a LICENSE file. Without an open-source license (such as MIT, Apache 2.0, or GPL), others cannot legally reuse or contribute to your work.",
            "category": "Compliance",
            "severity": "Medium"
        })

    # 3. Gitignore Suggestion
    if len(missing_gitignore) / total > 0.25:
        pct = int((len(missing_gitignore) / total) * 100)
        repo_names = ", ".join([r["name"] for r in missing_gitignore[:2]])
        suggestions.append({
            "title": "Add .gitignore files",
            "description": f"{pct}% of your projects ({repo_names}) lack a gitignore file. Adding language-specific .gitignore files prevents commit pollution (e.g. node_modules/, venv/, env files, or build caches).",
            "category": "Cleanliness & Security",
            "severity": "High"
        })

    # 4. Tests Suggestion
    if len(missing_tests) / total > 0.5:
        pct = int((len(missing_tests) / total) * 100)
        suggestions.append({
            "title": "Implement automated testing suites",
            "description": f"Over {pct}% of your projects do not have recognized test directories or files. Add tests (e.g., PyTest for Python, Jest/Vitest for JS, Go testing) to demonstrate production-grade coding habits.",
            "category": "Quality Assurance",
            "severity": "High"
        })

    # 5. CI/CD Suggestion
    if len(missing_ci) / total > 0.6:
        pct = int((len(missing_ci) / total) * 100)
        suggestions.append({
            "title": "Configure CI/CD automated checks",
            "description": f"{pct}% of your repositories have no CI configuration. Introduce GitHub Actions (.github/workflows/test.yml) to automatically run tests and lint checks on pull requests.",
            "category": "DevOps",
            "severity": "Medium"
        })

    # 6. Description Suggestion
    if len(missing_desc) > 0:
        repo_names = ", ".join([r["name"] for r in missing_desc[:3]])
        suffix = "..." if len(missing_desc) > 3 else ""
        suggestions.append({
            "title": "Provide repository descriptions",
            "description": f"The following repositories are missing short descriptions: {repo_names}{suffix}. Adding a description helps searchability on GitHub and explains the project's utility at a glance.",
            "category": "Repository Management",
            "severity": "Low"
        })

    # 7. Docker / Containerization Suggestion
    web_repos = [r for r in repositories if r.get("language") in ["Python", "TypeScript", "JavaScript", "Go", "Java"]]
    if len(web_repos) > 0 and len(missing_docker) / len(web_repos) > 0.5:
        suggestions.append({
            "title": "Containerize application environments",
            "description": "Many of your projects use backend/frontend language stacks but lack Dockerfiles. Containerizing your applications simplifies deployment and ensures reproducible developer setups.",
            "category": "Architecture",
            "severity": "Low"
        })

    return suggestions

def get_recommendations_for_language(lang: str) -> List[Dict[str, Any]]:
    """
    Returns 3 curated portfolio project suggestions based on a primary programming language.
    """
    clean_lang = (lang or "").lower()
    
    if "python" in clean_lang:
        return [
            {
                "title": "Asynchronous Distributed Task Broker",
                "description": "Build a lightweight Redis-backed task queue similar to Celery, supporting delayed executions, task retry policies, and worker status monitoring dashboards.",
                "tech_stack": "Python 3.11+, Asyncio, Redis, FastAPI, Docker",
                "difficulty": "Advanced",
                "tasks": [
                    "Implement a custom message envelope structure and JSON/MsgPack serializer.",
                    "Build a concurrent worker pool daemon that polls Redis queues using BRPOP.",
                    "Expose a FastAPI management endpoint to monitor active workers and queue lengths.",
                    "Write integration tests simulating worker failures and validating automatic retries."
                ]
            },
            {
                "title": "Semantic Multi-Format Document Search Engine",
                "description": "Create a local codebase query tool that reads PDF/Markdown files, generates vector embeddings, stores them locally, and lets users search files using natural language (RAG).",
                "tech_stack": "Python, LangChain/LlamaIndex, Qdrant/ChromaDB, SentenceTransformers, FastAPI",
                "difficulty": "Medium-Hard",
                "tasks": [
                    "Write asynchronous file parser scripts to clean, chunk, and structure raw documents.",
                    "Implement semantic embedding storage using a local vector database instance.",
                    "Create a hybrid search engine combining keyword matching (BM25) and semantic vector search.",
                    "Build a responsive web panel to inspect search rankings and highlight matched snippets."
                ]
            },
            {
                "title": "REST API Security Shield & Proxy",
                "description": "Develop a reverse-proxy server that intercepts API requests, performs JWT validation, implements leaky-bucket rate limiting, and caches GET queries in-memory.",
                "tech_stack": "Python, FastAPI, Redis, PyJWT, Pytest",
                "difficulty": "Medium",
                "tasks": [
                    "Implement a rate-limiter middleware using Redis sliding-window counter algorithm.",
                    "Build dynamic request routing maps that forward calls to target microservices.",
                    "Add token introspection and role-based access control (RBAC) verification filters.",
                    "Create custom logging logs detailing routing latency, status codes, and blocked IPs."
                ]
            }
        ]
        
    elif "javascript" in clean_lang or "typescript" in clean_lang or "html" in clean_lang:
        return [
            {
                "title": "Real-Time Collaborative Visual Workspace",
                "description": "A collaborative virtual canvas (like Figma/Miro) where multiple active users can draw shapes, drop text elements, drag objects around, and chat in real-time.",
                "tech_stack": "TypeScript, React, HTML5 Canvas, WebSockets (Socket.io), Node.js, Express",
                "difficulty": "Advanced",
                "tasks": [
                    "Design a synchronization protocol that distributes canvas coordinates and actions.",
                    "Build a conflict-free state resolution engine to merge drawing changes smoothly.",
                    "Optimize canvas rendering using requestAnimationFrame and off-screen buffers.",
                    "Create active-user cursor overlays and typing alerts inside a sleek visual layout."
                ]
            },
            {
                "title": "Developer CLI Analytics Workbench",
                "description": "A terminal CLI tool that analyzes local Git repositories, maps commit schedules, computes code ownership distributions, and generates nice charts in the console.",
                "tech_stack": "TypeScript, Node.js, Commander.js, Ink, Git-utils",
                "difficulty": "Medium",
                "tasks": [
                    "Parse git log inputs to extract structured commit dates, author emails, and changed files.",
                    "Build beautiful terminal outputs and progress bar loaders using Ink / React-in-terminal.",
                    "Add file filter flags to exclude vendor dependencies (node_modules, vendor) from stats.",
                    "Implement a command to export findings into structured JSON, HTML, or Markdown reports."
                ]
            },
            {
                "title": "Serverless API Gateway with Rate-Limiting",
                "description": "Implement a cloud-native API gateway that acts as a router, enforces api key validation, handles CORS rules, and dynamically runs routing scripts.",
                "tech_stack": "Node.js, Express, AWS Lambda (Serverless), Redis, Vitest",
                "difficulty": "Medium-Hard",
                "tasks": [
                    "Build a dynamic configuration loader that registers and maps routing paths.",
                    "Implement token bucket rate-limiting algorithms backed by a local Redis database.",
                    "Write performance benchmarks comparing proxy latency overhead against raw server connections.",
                    "Integrate structured Winston logger pipelines pushing telemetry into files."
                ]
            }
        ]
        
    else:
        # Fallback multi-language project recommendations
        return [
            {
                "title": "Microservices API Gateway & Load Balancer",
                "description": "Build a customizable API gateway that sits in front of backend microservices, performs path routing, load-balances requests (Round Robin / Least Connections), and blocks unauthorized traffic.",
                "tech_stack": "Any backend language (Go, Python, Node, Java), Redis, Docker",
                "difficulty": "Hard",
                "tasks": [
                    "Design a request proxying pipeline that forwards client requests and streams back responses.",
                    "Implement health check endpoints that poll target microservices and prune unhealthy routes.",
                    "Create JWT auth filter chains and rate-limiting modules using Redis.",
                    "Write benchmark scripts using Apache Bench or wrk to test throughput and latency."
                ]
            },
            {
                "title": "Static Documentation Site Generator",
                "description": "Develop a lightweight static site generator that compiles folders of markdown files into highly responsive, styled HTML pages complete with search bars, dark-mode switches, and navigation menus.",
                "tech_stack": "Any scripting language, Markdown parser library, Vanilla CSS, JS",
                "difficulty": "Medium",
                "tasks": [
                    "Write a directory walker that loads nested markdown files and parses frontmatter metadata.",
                    "Create responsive, clean HTML templates using custom CSS grids and side navigation.",
                    "Build a client-side search indexing system (e.g. Lunr.js-like search catalog).",
                    "Add automated watch features (using file system events) that rebuild pages on edits."
                ]
            },
            {
                "title": "Distributed In-Memory Key-Value Storage Engine",
                "description": "Create a simple TCP-based in-memory key-value database supporting basic CRUD commands (GET, SET, DEL), key expiration times, and snapshot persistence on disk.",
                "tech_stack": "System language (Go, Rust, C++, Python), Socket programming",
                "difficulty": "Advanced",
                "tasks": [
                    "Design a lightweight binary protocol or textual parser for command inputs.",
                    "Build a concurrent-safe hash map with key expiration hooks using active/passive pruning.",
                    "Write a background writer routine that dumps memory states into a binary snapshot file.",
                    "Implement master-replica replication to sync database states across multiple running instances."
                ]
            }
        ]

def generate_heuristic_readme(repo_name: str, language: str, description: str) -> str:
    """
    Generates a structured, professional README.md template tailored to the repository's programming language.
    """
    lang_clean = (language or "").lower()
    desc = description or "A developer project designed for performance and clean architecture."

    # Section for Python projects
    if "python" in lang_clean:
        return f"""# {repo_name} ⭐

{desc}

---

## 🚀 Getting Started

This Python project is optimized for local setup and testing. Follow the steps below to initialize the project environment.

### 📋 Prerequisites

Ensure you have python installed (Python 3.9 or higher recommended):
```bash
python --version
```

### ⚙️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/{repo_name}.git
   cd {repo_name}
   ```

2. **Set up a Virtual Environment:**
   * **Windows (PowerShell):**
     ```powershell
     python -m venv venv
     .\\venv\\Scripts\\Activate.ps1
     ```
   * **macOS / Linux:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 🛠️ Usage Instructions

Describe how to run the main codebase or service. If it is an API or CLI:

* **To run the application:**
  ```bash
  # Replace with your primary entry file (e.g., app/main.py, run.py)
  python main.py
  ```

---

## 🧪 Testing & Code Quality

Automated tests are located in the `tests/` directory.

* **Run all tests using pytest:**
  ```bash
  pip install pytest
  pytest
  ```

* **Run code lint checks:**
  ```bash
  pip install flake8 black
  black . --check
  flake8 .
  ```

---

## 📁 Project Structure

```text
{repo_name}/
├── app/              # Application source code
│   ├── __init__.py
│   └── main.py
├── tests/            # Test scripts
│   └── test_main.py
├── requirements.txt  # Project dependencies
├── .gitignore        # Git ignore rules
└── README.md         # Documentation
```

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check [issues page](https://github.com/your-username/{repo_name}/issues).

1. Fork the project.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
"""

    # Section for Javascript / Typescript projects
    elif "javascript" in lang_clean or "typescript" in lang_clean or "html" in lang_clean:
        is_ts = "typescript" in lang_clean
        package_manager = "npm"
        run_dev = "npm run dev"
        build_cmd = "npm run build"
        test_cmd = "npm run test"
        
        return f"""# {repo_name} ⚡

{desc}

---

## 🚀 Getting Started

This JavaScript/TypeScript project is structured for modern web development workflows. Follow the steps below to set it up locally.

### 📋 Prerequisites

Ensure you have [Node.js](https://nodejs.org/) installed:
```bash
node --version
npm --version
```

### ⚙️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/{repo_name}.git
   cd {repo_name}
   ```

2. **Install package dependencies:**
   ```bash
   {package_manager} install
   ```

3. **Configure Environment Variables:**
   Create a `.env` file in the root directory and define necessary values:
   ```text
   PORT=3000
   API_URL=https://api.example.com
   ```

---

## 🛠️ Development & Deployment

* **Launch the local development server:**
  ```bash
  {run_dev}
  ```

* **Compile the production build:**
  ```bash
  {build_cmd}
  ```

---

## 🧪 Testing & Code Quality

* **Run unit tests:**
  ```bash
  {test_cmd}
  ```

* **Run Linting checks:**
  ```bash
  npm run lint
  ```

---

## 📁 Project Structure

```text
{repo_name}/
├── src/                  # Source files
│   ├── components/       # UI Components
│   ├── hooks/            # Custom Hooks
│   ├── App.jsx           # Entry Component
│   └── main.jsx          # Mount Script
├── public/               # Static assets
├── .gitignore            # Git exclusion rules
├── package.json          # Script commands and npm configurations
{"├── tsconfig.json       # TypeScript compiler settings" if is_ts else ""}
└── README.md             # Documentation
```

---

## 🤝 Contributing

1. Fork the project.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more info.
"""

    # Generic Fallback README
    else:
        return f"""# {repo_name} 🛠️

{desc}

---

## 🚀 Getting Started

Follow these steps to configure and build the application environment on your local machine.

### ⚙️ Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/{repo_name}.git
   cd {repo_name}
   ```

2. **Initialize dependencies:**
   Review the codebase configuration files and download dependencies for the environment.

3. **Build the project:**
   Compile or bundle the files according to your development toolkit.

---

## 🛠️ Usage

Describe running commands, CLI options, or how to launch services:
```bash
# Example execution command
./run-project
```

---

## 📁 Project Directory Layout

```text
{repo_name}/
├── src/              # Application source code
├── tests/            # Automated test suite
├── .gitignore        # Git ignores
├── LICENSE           # Project license
└── README.md         # Project documentation
```

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!
1. Fork the project.
2. Create a branch (`git checkout -b feature/new-idea`).
3. Save changes and commit (`git commit -m 'Add new-idea'`).
4. Push and create a Pull Request.

---

## 📄 License

Distributed under the MIT License.
"""

def generate_heuristic_analysis(profile_data: Dict[str, Any], repositories: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Simulates a full portfolio review with statistical evaluations.
    """
    # 1. Compute portfolio score
    score = calculate_portfolio_score(profile_data, repositories)
    
    # 2. Extract primary languages used in the portfolio
    languages = {}
    for repo in repositories:
        lang = repo.get("language")
        if lang:
            languages[lang] = languages.get(lang, 0) + 1
            
    sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)
    primary_lang = sorted_langs[0][0] if sorted_langs else "General"
    
    # 3. Create portfolio summary
    summary_text = (
        f"Audited {len(repositories)} repositories for user {profile_data.get('username')}. "
        f"The primary development technology detected is {primary_lang}."
    )
    if len(repositories) > 0:
        readme_pct = int((sum(1 for r in repositories if r.get("has_readme")) / len(repositories)) * 100)
        test_pct = int((sum(1 for r in repositories if r.get("has_tests")) / len(repositories)) * 100)
        summary_text += (
            f" Out of these repositories, {readme_pct}% have a README.md file, and {test_pct}% "
            f"have defined tests. Focus on adding robust documentation and automated checks to "
            f"improve your portfolio score."
        )
    else:
        summary_text += " Please create repositories and upload files to trigger a full audit checklist."
        
    # 4. Generate improvements list
    improvements = generate_suggestions(repositories)
    
    # 5. Pick recommended projects
    recommended_projects = get_recommendations_for_language(primary_lang)
    
    return {
        "score": score,
        "summary": summary_text,
        "improvements": improvements,
        "recommended_projects": recommended_projects,
        "is_ai_generated": False
    }
