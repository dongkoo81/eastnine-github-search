#!/usr/bin/env python3
"""
EastNine GitHub Search MCP Server

A Model Context Protocol server that searches for scripts in personal GitHub repositories
using natural language descriptions.
"""

import os
import re
from typing import Any, Dict, List, Optional
import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables (MCP env takes priority over .env file)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# If not found in environment, try loading from .env file
if not GITHUB_TOKEN:
    load_dotenv()
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN must be provided either as environment variable or in .env file")

# Fixed username for dongkoo81's repositories
GITHUB_USERNAME = "dongkoo81"

# GitHub API headers
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "EastNine-GitHub-Search-MCP"
}

# Common script file extensions
SCRIPT_EXTENSIONS = {
    '.py', '.js', '.ts', '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd',
    '.rb', '.php', '.pl', '.go', '.rs', '.java', '.scala', '.kt', '.swift',
    '.r', '.R', '.sql', '.lua', '.vim', '.awk', '.sed'
}

class GitHubSearcher:
    """GitHub repository searcher for scripts"""
    
    def __init__(self, username: str, token: str):
        self.username = username
        self.token = token
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
    
    def get_user_repositories(self) -> List[Dict[str, Any]]:
        """Get all public repositories for the user"""
        repos = []
        page = 1
        
        while True:
            url = f"https://api.github.com/users/{self.username}/repos"
            params = {
                "type": "public",
                "sort": "updated",
                "per_page": 100,
                "page": page
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            page_repos = response.json()
            if not page_repos:
                break
                
            repos.extend(page_repos)
            page += 1
            
        return repos
    
    def search_code_in_repo(self, repo_name: str, query: str) -> List[Dict[str, Any]]:
        """Search for code in a specific repository"""
        # GitHub code search API
        search_query = f"repo:{self.username}/{repo_name} {query}"
        url = "https://api.github.com/search/code"
        params = {
            "q": search_query,
            "per_page": 50
        }
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json().get("items", [])
        except requests.exceptions.RequestException as e:
            # Redirect error to stderr instead of stdout
            import sys
            print(f"Error searching in {repo_name}: {e}", file=sys.stderr)
            return []
    
    def get_file_content(self, repo_name: str, file_path: str) -> Optional[str]:
        """Get the content of a specific file"""
        url = f"https://api.github.com/repos/{self.username}/{repo_name}/contents/{file_path}"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            file_data = response.json()
            if file_data.get("encoding") == "base64":
                import base64
                content = base64.b64decode(file_data["content"]).decode("utf-8")
                return content
        except requests.exceptions.RequestException as e:
            # Redirect error to stderr instead of stdout
            import sys
            print(f"Error getting file content: {e}", file=sys.stderr)
            
        return None
    
    def is_script_file(self, filename: str) -> bool:
        """Check if a file is likely a script based on its extension"""
        _, ext = os.path.splitext(filename.lower())
        return ext in SCRIPT_EXTENSIONS
    
    def search_scripts_by_description(self, description: str) -> List[Dict[str, Any]]:
        """Search for scripts using natural language description"""
        results = []
        
        # Get all repositories
        repos = self.get_user_repositories()
        
        # Extract keywords from description
        keywords = self.extract_keywords(description)
        
        for repo in repos:
            repo_name = repo["name"]
            
            # Search using different strategies
            for keyword in keywords:
                # Search in code content
                code_results = self.search_code_in_repo(repo_name, keyword)
                
                for item in code_results:
                    if self.is_script_file(item["name"]):
                        results.append({
                            "repository": repo_name,
                            "file_path": item["path"],
                            "file_name": item["name"],
                            "html_url": item["html_url"],
                            "score": item.get("score", 0),
                            "matched_keyword": keyword,
                            "description": repo.get("description", ""),
                            "language": repo.get("language", "Unknown")
                        })
        
        # Remove duplicates and sort by score
        unique_results = {}
        for result in results:
            key = f"{result['repository']}/{result['file_path']}"
            if key not in unique_results or result['score'] > unique_results[key]['score']:
                unique_results[key] = result
        
        sorted_results = sorted(unique_results.values(), key=lambda x: x['score'], reverse=True)
        return sorted_results[:20]  # Return top 20 results
    
    def extract_keywords(self, description: str) -> List[str]:
        """Extract relevant keywords from natural language description"""
        # Convert to lowercase and remove special characters
        clean_desc = re.sub(r'[^\w\s]', ' ', description.lower())
        words = clean_desc.split()
        
        # Common programming/script related keywords mapping
        keyword_mapping = {
            '압축': ['compress', 'zip', 'archive', 'tar', 'gzip'],
            '백업': ['backup', 'dump', 'export', 'save'],
            '데이터베이스': ['database', 'db', 'sql', 'mysql', 'postgres', 'mongodb'],
            '파일': ['file', 'directory', 'folder', 'path'],
            '서버': ['server', 'http', 'api', 'web', 'flask', 'django'],
            '배포': ['deploy', 'deployment', 'build', 'release'],
            '모니터링': ['monitor', 'log', 'watch', 'alert'],
            '자동화': ['automation', 'auto', 'cron', 'schedule'],
            '테스트': ['test', 'testing', 'unit', 'integration'],
            '설정': ['config', 'configuration', 'setup', 'install'],
        }
        
        keywords = set()
        
        # Add original words
        keywords.update(words)
        
        # Add mapped keywords
        for word in words:
            if word in keyword_mapping:
                keywords.update(keyword_mapping[word])
        
        # Filter out common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
        keywords = [k for k in keywords if k not in stop_words and len(k) > 2]
        
        return list(keywords)

def analyze_script_functionality(content: str, file_path: str) -> str:
    """
    스크립트 내용을 분석하여 주요 기능과 동작을 설명하는 함수
    
    Args:
        content: 스크립트 파일 내용
        file_path: 파일 경로
    
    Returns:
        스크립트 기능 설명 문자열
    """
    description = []
    content_lower = content.lower()
    
    # 파일명에서 힌트 추출
    filename = os.path.basename(file_path).lower()
    
    # 주석에서 설명 추출 (Python의 경우)
    if file_path.endswith('.py'):
        # docstring 추출
        docstring_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
        if docstring_match:
            docstring = docstring_match.group(1).strip()
            if len(docstring) > 50:  # 의미있는 docstring인 경우
                description.append(f"📝 **스크립트 설명 (개발자 주석)**:\n{docstring[:500]}...")
    
    # 주요 기능 패턴 분석
    functionality = []
    
    # 데이터베이스 관련
    if any(keyword in content_lower for keyword in ['select', 'insert', 'update', 'delete', 'create table']):
        functionality.append("🗄️ **데이터베이스 작업**: SQL 쿼리 실행 (CRUD 작업)")
    
    if 'history list length' in content_lower or 'hll' in content_lower:
        functionality.append("📊 **HLL 관리**: Aurora MySQL History List Length 제어")
    
    # 멀티스레딩/동시성
    if any(keyword in content_lower for keyword in ['threading', 'thread', 'concurrent']):
        functionality.append("⚡ **멀티스레딩**: 동시 작업 처리로 성능 향상")
    
    # 모니터링
    if any(keyword in content_lower for keyword in ['monitor', 'metrics', 'cloudwatch']):
        functionality.append("📈 **모니터링**: 시스템 메트릭 수집 및 추적")
    
    # 파일 처리
    if any(keyword in content_lower for keyword in ['file', 'directory', 'path', 'os.path']):
        functionality.append("📁 **파일 처리**: 파일 시스템 작업 및 관리")
    
    # 네트워크/API
    if any(keyword in content_lower for keyword in ['requests', 'http', 'api', 'url']):
        functionality.append("🌐 **네트워크 통신**: HTTP API 호출 및 데이터 교환")
    
    # 백업/복원
    if any(keyword in content_lower for keyword in ['backup', 'restore', 'dump', 'export']):
        functionality.append("💾 **백업/복원**: 데이터 백업 및 복원 작업")
    
    # 자동화
    if any(keyword in content_lower for keyword in ['schedule', 'cron', 'automation', 'batch']):
        functionality.append("🤖 **자동화**: 스케줄링 및 배치 작업")
    
    # 테스트/부하
    if any(keyword in content_lower for keyword in ['test', 'load', 'stress', 'benchmark']):
        functionality.append("🧪 **테스트**: 성능 테스트 및 부하 생성")
    
    # 설정/구성
    if any(keyword in content_lower for keyword in ['config', 'setup', 'install', 'configure']):
        functionality.append("⚙️ **설정 관리**: 시스템 구성 및 초기화")
    
    if functionality:
        description.append("🎯 **주요 기능**:")
        description.extend([f"   {func}" for func in functionality])
    
    # 실행 흐름 분석
    execution_flow = []
    
    if 'if __name__ == "__main__"' in content:
        execution_flow.append("▶️ **메인 실행부**: 스크립트 직접 실행 가능")
    
    if any(keyword in content_lower for keyword in ['while true', 'infinite', 'loop']):
        execution_flow.append("🔄 **무한 루프**: 지속적인 작업 수행")
    
    if 'try:' in content and 'except' in content:
        execution_flow.append("🛡️ **예외 처리**: 오류 상황 대응 로직 포함")
    
    if execution_flow:
        description.append("🔧 **실행 특성**:")
        description.extend([f"   {flow}" for flow in execution_flow])
    
    return '\n'.join(description) if description else ""

def analyze_script_requirements(content: str, file_path: str) -> str:
    """
    스크립트 내용을 분석하여 실행 환경 요구사항을 파악하는 함수
    
    Args:
        content: 스크립트 파일 내용
        file_path: 파일 경로
    
    Returns:
        요구사항 분석 결과 문자열
    """
    requirements = []
    
    # 파일 확장자 기반 언어 감지
    _, ext = os.path.splitext(file_path.lower())
    
    if ext == '.py':
        requirements.append("🐍 **Python 환경** 필요")
        
        # Python 패키지 의존성 분석
        python_packages = []
        common_imports = {
            'mysql.connector': 'MySQL 연결',
            'pymysql': 'MySQL 연결',
            'psycopg2': 'PostgreSQL 연결',
            'boto3': 'AWS SDK',
            'requests': 'HTTP 클라이언트',
            'pandas': '데이터 분석',
            'numpy': '수치 계산',
            'flask': '웹 프레임워크',
            'django': '웹 프레임워크',
            'threading': '멀티스레딩 (내장)',
            'multiprocessing': '멀티프로세싱 (내장)'
        }
        
        for package, description in common_imports.items():
            if f'import {package}' in content or f'from {package}' in content:
                python_packages.append(f"  - `{package}`: {description}")
        
        if python_packages:
            requirements.append("📦 **필요한 Python 패키지:**")
            requirements.extend(python_packages)
    
    elif ext in ['.sh', '.bash']:
        requirements.append("🐚 **Bash 셸 환경** 필요")
    
    elif ext in ['.js', '.ts']:
        requirements.append("🟨 **Node.js 환경** 필요")
    
    # 데이터베이스 연결 감지
    db_patterns = {
        'mysql': ['mysql', 'aurora', 'rds'],
        'postgresql': ['postgres', 'psql'],
        'mongodb': ['mongo', 'mongodb'],
        'redis': ['redis']
    }
    
    content_lower = content.lower()
    for db_type, patterns in db_patterns.items():
        if any(pattern in content_lower for pattern in patterns):
            requirements.append(f"🗄️ **{db_type.upper()} 데이터베이스** 접속 필요")
            break
    
    # AWS 서비스 감지
    aws_services = []
    aws_patterns = {
        'EC2': ['ec2', 'instance'],
        'RDS': ['rds', 'aurora'],
        'S3': ['s3', 'bucket'],
        'Lambda': ['lambda'],
        'CloudWatch': ['cloudwatch', 'metrics']
    }
    
    for service, patterns in aws_patterns.items():
        if any(pattern in content_lower for pattern in patterns):
            aws_services.append(service)
    
    if aws_services:
        requirements.append(f"☁️ **AWS 서비스**: {', '.join(aws_services)}")
        requirements.append("🔑 **AWS 자격 증명** 필요")
    
    # 네트워크/포트 요구사항 감지
    if 'port' in content_lower or ':3306' in content or ':5432' in content:
        requirements.append("🌐 **네트워크 접속** 필요 (방화벽/보안그룹 설정)")
    
    # 고성능 요구사항 감지
    performance_keywords = ['threading', 'multiprocessing', 'concurrent', 'parallel', 'load', 'stress']
    if any(keyword in content_lower for keyword in performance_keywords):
        requirements.append("⚡ **고성능 환경** 권장 (멀티코어 CPU)")
    
    return '\n'.join(requirements) if requirements else ""

# Initialize the searcher
searcher = GitHubSearcher(GITHUB_USERNAME, GITHUB_TOKEN)

# Create FastMCP server
mcp = FastMCP("eastnine-github-search")

@mcp.tool()
def search_scripts(description: str) -> str:
    """Search for scripts in your GitHub repositories using natural language description
    
    Args:
        description: Natural language description of the script you're looking for 
                    (e.g., 'file compression script', 'database backup tool')
    """
    if not description:
        return "Error: Description is required"
    
    try:
        results = searcher.search_scripts_by_description(description)
        
        if not results:
            return f"No scripts found matching the description: '{description}'"
        
        # Format results
        output = f"Found {len(results)} scripts matching '{description}':\n\n"
        
        for i, result in enumerate(results, 1):
            output += f"{i}. **{result['file_name']}** in `{result['repository']}`\n"
            output += f"   📁 Path: `{result['file_path']}`\n"
            output += f"   🔗 URL: {result['html_url']}\n"
            output += f"   🏷️ Language: {result['language']}\n"
            if result['description']:
                output += f"   📝 Repo Description: {result['description']}\n"
            output += f"   🎯 Matched Keyword: {result['matched_keyword']}\n"
            output += f"   ⭐ Score: {result['score']}\n\n"
        
        return output
        
    except Exception as e:
        return f"Error searching scripts: {str(e)}"

@mcp.tool()
def get_script_content(repository: str, file_path: str) -> str:
    """Get the full content of a specific script file
    
    Args:
        repository: Repository name
        file_path: Path to the script file
    """
    if not repository or not file_path:
        return "Error: Both repository and file_path are required"
    
    try:
        content = searcher.get_file_content(repository, file_path)
        
        if content is None:
            return f"Could not retrieve content for {file_path} in {repository}"
        
        # Determine file extension for syntax highlighting
        _, ext = os.path.splitext(file_path)
        language = ext[1:] if ext else "text"
        
        output = f"# Content of `{file_path}` from `{repository}`\n\n"
        output += f"```{language}\n{content}\n```"
        
        return output
        
    except Exception as e:
        return f"Error getting script content: {str(e)}"

@mcp.tool()
def download_script(repository: str, file_path: str, local_path: str = None, branch: str = "main") -> str:
    """Download a script file from GitHub repository to local filesystem
    
    Args:
        repository: Repository name
        file_path: Path to the script file in the repository
        local_path: Local path where to save the file (optional, defaults to download_scripts directory with original filename)
        branch: Branch name to download from (default: main)
    """
    if not repository or not file_path:
        return "Error: Both repository and file_path are required"
    
    try:
        # Construct raw GitHub URL
        raw_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{repository}/{branch}/{file_path}"
        
        # Download the file
        response = searcher.session.get(raw_url)
        response.raise_for_status()
        
        # Determine local file path
        if local_path is None:
            # Default to download_scripts directory
            download_dir = os.path.join(os.getcwd(), "download_scripts")
            filename = os.path.basename(file_path)
            local_path = os.path.join(download_dir, filename)
        else:
            # If local_path is a directory, append the filename
            if os.path.isdir(local_path):
                filename = os.path.basename(file_path)
                local_path = os.path.join(local_path, filename)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        # Write file to local filesystem
        with open(local_path, 'wb') as f:
            f.write(response.content)
        
        # Get file size for confirmation
        file_size = len(response.content)
        
        # Analyze script functionality and requirements
        script_content = response.content.decode('utf-8')
        script_functionality = analyze_script_functionality(script_content, file_path)
        script_requirements = analyze_script_requirements(script_content, file_path)
        
        result = f"✅ Successfully downloaded script!\n\n" \
                f"📁 Repository: {repository}\n" \
                f"📄 Remote file: {file_path}\n" \
                f"💾 Local path: {local_path}\n" \
                f"🌿 Branch: {branch}\n" \
                f"📊 File size: {file_size:,} bytes\n" \
                f"🔗 Source URL: {raw_url}\n\n"
        
        # Add script functionality description
        if script_functionality:
            result += f"## 📋 스크립트 기능 분석\n\n{script_functionality}\n\n"
        
        # Add environment setup suggestion
        if script_requirements:
            result += "🚀 **스크립트를 실행하기 위한 환경을 만들어 드릴까요?**\n\n"
            result += f"**감지된 요구사항:**\n{script_requirements}\n\n"
            result += "**제안 옵션:**\n"
            result += "1. 🐳 **CloudShell 환경** - 즉시 사용 가능, 무료, AWS 도구 사전 설치\n"
            result += "2. 🖥️ **로컬 환경 설정** - 필요한 패키지 설치 및 설정 가이드\n"
            result += "3. ☁️ **EC2 인스턴스** - 전용 서버 환경 (고성능 필요시)\n\n"
            result += "어떤 환경을 선호하시나요? 선택해주시면 상세한 설정 가이드를 제공해드립니다!"
        
        return result
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return f"❌ File not found: {file_path} in repository {repository} (branch: {branch})"
        else:
            return f"❌ HTTP error downloading file: {e}"
    except OSError as e:
        return f"❌ Error writing file to {local_path}: {e}"
    except Exception as e:
        return f"❌ Error downloading script: {str(e)}"

@mcp.tool()
def setup_script_environment(environment_type: str, script_path: str = None) -> str:
    """스크립트 실행을 위한 환경 설정 가이드를 제공합니다
    
    Args:
        environment_type: 환경 타입 ('cloudshell', 'local', 'ec2')
        script_path: 스크립트 파일 경로 (선택사항)
    """
    if environment_type.lower() == 'cloudshell':
        return """
🐳 **AWS CloudShell 환경 설정 가이드**

## 1. CloudShell 시작
```bash
# AWS 콘솔에서 CloudShell 아이콘 클릭
# 또는 AWS CLI에서: aws cloudshell
```

## 2. 필요한 도구 설치
```bash
# Python 패키지 설치
pip3 install mysql-connector-python boto3 requests

# MySQL 클라이언트 (이미 설치됨)
mysql --version
```

## 3. AWS 자격 증명 확인
```bash
# 현재 자격 증명 확인
aws sts get-caller-identity

# 리전 설정
aws configure set region ap-northeast-2
```

## 4. 스크립트 업로드
```bash
# 로컬에서 CloudShell로 파일 업로드
# CloudShell 인터페이스의 "Actions" > "Upload file" 사용
```

## 5. 실행 권한 부여
```bash
chmod +x your_script.py
python3 your_script.py
```

**장점**: 즉시 사용 가능, 무료, AWS 도구 사전 설치
**단점**: 세션 제한 시간, 제한된 컴퓨팅 리소스
        """
    
    elif environment_type.lower() == 'local':
        return """
🖥️ **로컬 환경 설정 가이드**

## 1. Python 환경 설정
```bash
# Python 버전 확인
python3 --version

# 가상환경 생성
python3 -m venv script_env
source script_env/bin/activate  # Linux/Mac
# script_env\\Scripts\\activate  # Windows
```

## 2. 필요한 패키지 설치
```bash
pip install mysql-connector-python
pip install boto3
pip install requests
pip install pandas  # 데이터 분석 필요시
```

## 3. AWS 자격 증명 설정
```bash
# AWS CLI 설치
pip install awscli

# 자격 증명 설정
aws configure
# Access Key ID: [입력]
# Secret Access Key: [입력]
# Default region: ap-northeast-2
# Default output format: json
```

## 4. 데이터베이스 접속 설정
```bash
# 보안 그룹에서 로컬 IP 허용 필요
# RDS/Aurora 엔드포인트 확인
```

**장점**: 완전한 제어, 높은 성능, 영구 저장
**단점**: 초기 설정 복잡, 의존성 관리 필요
        """
    
    elif environment_type.lower() == 'ec2':
        return """
☁️ **EC2 인스턴스 환경 설정 가이드**

## 1. EC2 인스턴스 생성
```bash
# 권장 사양
# - Instance Type: t3.medium 이상
# - OS: Amazon Linux 2023 또는 Ubuntu 22.04
# - Storage: 20GB 이상
```

## 2. 보안 그룹 설정
```bash
# 인바운드 규칙
# - SSH (22): 내 IP
# - MySQL (3306): VPC 내부 (RDS 접속용)
```

## 3. 인스턴스 접속 및 설정
```bash
# SSH 접속
ssh -i your-key.pem ec2-user@your-instance-ip

# 시스템 업데이트
sudo yum update -y  # Amazon Linux
# sudo apt update && sudo apt upgrade -y  # Ubuntu

# Python 및 도구 설치
sudo yum install -y python3 python3-pip mysql
pip3 install mysql-connector-python boto3 requests
```

## 4. IAM 역할 설정 (권장)
```bash
# EC2에 IAM 역할 연결하여 AWS 서비스 접근
# 필요한 정책: AmazonRDSReadOnlyAccess, CloudWatchReadOnlyAccess
```

## 5. 스크립트 배포
```bash
# SCP로 파일 전송
scp -i your-key.pem script.py ec2-user@your-instance-ip:~/

# 또는 Git 클론
git clone https://github.com/your-repo/scripts.git
```

**장점**: 고성능, 24/7 실행 가능, 완전한 제어
**단점**: 비용 발생, 관리 부담, 보안 설정 필요
        """
    
    else:
        return "지원되는 환경 타입: 'cloudshell', 'local', 'ec2'"

def main():
    """Main entry point for the server"""
    mcp.run()

if __name__ == "__main__":
    main()
