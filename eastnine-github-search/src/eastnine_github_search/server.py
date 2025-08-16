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

def main():
    """Main entry point for the server"""
    mcp.run()

if __name__ == "__main__":
    main()
