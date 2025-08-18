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
import json

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

# Global variables to store user selections during environment setup
ENVIRONMENT_CONFIG = {
    'vpc_id': None,
    'vpc_name': None,
    'security_group_id': None,
    'security_group_name': None,
    'db_subnet_group_name': None,
    'cluster_name': None,
    'parameter_group': None,
    'instance_type': None
}

class GitHubSearcher:
    """GitHub repository searcher for scripts"""
    
    def __init__(self, username: str, token: str):
        self.username = username
        self.token = token
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
    
    def get_user_repositories(self) -> List[Dict[str, Any]]:
        """Get all public repositories for the user.
        
        Returns:
            List[Dict[str, Any]]: List of repository dictionaries containing
                                 repository information from GitHub API.
        """
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
        """Search for code in a specific repository using GitHub code search API.
        
        Args:
            repo_name (str): Name of the repository to search in
            query (str): Search query string
            
        Returns:
            List[Dict[str, Any]]: List of search results from GitHub code search API
        """
        # GitHub code search API with optimized parameters
        search_query = f"repo:{self.username}/{repo_name} {query}"
        url = "https://api.github.com/search/code"
        params = {
            "q": search_query,
            "per_page": 100,  # 최대 결과 수
            "sort": "indexed",  # 최신 인덱싱된 파일 우선
            "order": "desc"     # 내림차순 정렬
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
        """Get the content of a specific file from GitHub repository.
        
        Args:
            repo_name (str): Name of the repository
            file_path (str): Path to the file within the repository
            
        Returns:
            Optional[str]: File content as string if successful, None if failed
        """
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
        """Check if a file is likely a script based on its extension.
        
        Args:
            filename (str): Name of the file to check
            
        Returns:
            bool: True if file extension matches known script extensions, False otherwise
        """
        _, ext = os.path.splitext(filename.lower())
        return ext in SCRIPT_EXTENSIONS
    
    def search_scripts_by_description(self, description: str) -> List[Dict[str, Any]]:
        """Search for scripts using natural language description.
        
        This method searches through all user repositories to find scripts that match
        the given natural language description using optimized GitHub code search API.
        
        Args:
            description (str): Natural language description of the script to search for
            
        Returns:
            List[Dict[str, Any]]: List of script search results with metadata
        """
        # Use optimized single API call method
        return self.search_scripts_optimized(description)
    
    def search_scripts_optimized(self, description: str) -> List[Dict[str, Any]]:
        """Optimized search for scripts using GitHub code search API.
        
        This method searches across all user repositories in a single API call
        instead of searching each repository individually.
        
        Args:
            description (str): Natural language description of the script to search for
            
        Returns:
            List[Dict[str, Any]]: List of script search results with metadata
        """
        results = []
        
        # Strategy 1: Simple search without extension filtering
        search_query = f"user:{self.username} {description}"
        url = "https://api.github.com/search/code"
        params = {
            "q": search_query,
            "per_page": 100,
            "sort": "indexed",
            "order": "desc"
        }
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            items = response.json().get("items", [])
            
            for item in items:
                if self.is_script_file(item["name"]):
                    # Extract repository name from full_name
                    repo_name = item["repository"]["name"]
                    results.append({
                        "repository": repo_name,
                        "file_path": item["path"],
                        "file_name": item["name"],
                        "html_url": item["html_url"],
                        "score": item.get("score", 0),
                        "matched_keyword": description,
                        "description": item["repository"].get("description", ""),
                        "language": item["repository"].get("language", "Unknown")
                    })
            
            # If we found results, return them
            if results:
                return results[:20]  # Return top 20 results
            
            # Strategy 2: If no results, try searching with just keywords
            keywords = description.split()
            for keyword in keywords[:3]:  # Try first 3 keywords
                if len(keyword) > 2:  # Only meaningful keywords
                    search_query = f"user:{self.username} {keyword}"
                    params["q"] = search_query
                    
                    response = self.session.get(url, params=params)
                    response.raise_for_status()
                    items = response.json().get("items", [])
                    
                    for item in items:
                        if self.is_script_file(item["name"]):
                            repo_name = item["repository"]["name"]
                            results.append({
                                "repository": repo_name,
                                "file_path": item["path"],
                                "file_name": item["name"],
                                "html_url": item["html_url"],
                                "score": item.get("score", 0),
                                "matched_keyword": keyword,
                                "description": item["repository"].get("description", ""),
                                "language": item["repository"].get("language", "Unknown")
                            })
                    
                    if results:
                        break
            
            return results[:20]  # Return top 20 results
            
        except requests.exceptions.RequestException as e:
            import sys
            print(f"Error in optimized search: {e}", file=sys.stderr)
            return []
    






# Initialize the searcher
searcher = GitHubSearcher(GITHUB_USERNAME, GITHUB_TOKEN)

# Create FastMCP server with instructions
instructions = """
You are working with the EastNine GitHub Search MCP Server that helps users find and manage scripts from dongkoo81's GitHub repositories.

CRITICAL WORKFLOW RULES - YOU MUST FOLLOW THESE EXACTLY:

1. ENVIRONMENT SETUP SEQUENCE (STRICT ORDER - NEVER SKIP STEPS):
   - When user wants to set up AWS environment, you MUST follow this EXACT sequence:
   - Step 1: Call setup_environment_guide("start") or setup_environment_guide("vpc")
   - Step 2: Wait for user VPC selection, then call setup_environment_guide("security")
   - Step 3: Wait for user security group selection, then call setup_environment_guide("cluster")
   - Step 4: Wait for user cluster name selection, then call setup_environment_guide("parameter")
   - Step 5: Wait for user parameter group selection, then call setup_environment_guide("instance")
   - Step 6: Wait for user instance type selection, then call setup_test_environment()
   - NEVER skip steps or call them out of order!

2. UNIFIED CONFIGURATION MANAGEMENT:
   - Use ONLY configure_aws_environment() tool for saving ALL user selections
   - This single tool replaces all individual save functions with action-based approach:
     * configure_aws_environment(action="save_vpc", vpc_id="...", vpc_name="...")
     * configure_aws_environment(action="save_security_group", security_group_id="...", security_group_name="...")
     * configure_aws_environment(action="save_cluster_name", cluster_name="...")
     * configure_aws_environment(action="save_parameter_group", parameter_group="...")
     * configure_aws_environment(action="save_instance_type", instance_type="...")
   - Use configure_aws_environment(action="show_status") to display current configuration
   - Use configure_aws_environment(action="reset") to clear all settings if needed

3. USER SELECTION MEMORY AND STATUS DISPLAY:
   - The configure_aws_environment() tool automatically shows current status after each save
   - ALWAYS show current configuration status before presenting new options using the unified tool
   - Confirm each selection before moving to next step

4. PROACTIVE ENVIRONMENT SETUP - MANDATORY:
   - CRITICAL: After ANY download_script() call that detects AWS/database scripts, you MUST immediately ask users about environment setup
   - NEVER just explain the download result - ALWAYS follow up with environment setup question
   - Required question format: "이 스크립트를 테스트하기 위한 AWS 환경을 구성하시겠습니까?"
   - When user responds positively ("네", "환경 구성해주세요", "시작해줘", "좋아요"), immediately call setup_environment_guide("start")
   - This is NOT optional - you MUST ask every time after downloading AWS-related scripts
   - Be helpful and explain why the environment would be useful for testing the specific script

5. USER INTERACTION AND SELECTION GUIDANCE:
   - When showing options (VPC, security groups, cluster names, etc.), ALWAYS ask user to choose
   - Support Korean natural language selections and AUTOMATICALLY call configure_aws_environment():
     * "1번 VPC 사용해줘" → Call configure_aws_environment(action="save_vpc", vpc_id=..., vpc_name=...), then proceed to security group
     * "2번 VPC로 해줘" → Call configure_aws_environment(action="save_vpc", ...), then proceed to security group
     * "2번 보안 그룹으로 해줘" → Call configure_aws_environment(action="save_security_group", ...)
     * "1번 서브넷 그룹 사용해줘" → Call configure_aws_environment(action="save_db_subnet_group", db_subnet_group_name="...")
     * "default로 해줘" → Call configure_aws_environment(action="save_db_subnet_group", db_subnet_group_name="default")
     * "test-cluster로 이름 정해줘" → Call configure_aws_environment(action="save_cluster_name", cluster_name="test-cluster")

   - CRITICAL: When user makes a selection, you MUST:
     1. Parse their selection (번호, 이름, 또는 특성)
     2. Find the corresponding resource info from the displayed list
     3. Call configure_aws_environment() with appropriate action and parameters
     4. AUTOMATICALLY proceed to next step by calling the next setup_environment_guide() step
   - AUTOMATIC PROGRESSION AFTER SAVING:
     * After saving VPC → Call setup_environment_guide("security")
     * After saving security group → Call setup_environment_guide("subnet")
     * After saving DB subnet group → Call setup_environment_guide("cluster")
     * After saving cluster name → Call setup_environment_guide("parameter")
     * After saving parameter group → Call setup_environment_guide("instance")
     * After saving instance type → Call setup_test_environment()
   - NEVER ask user to manually call the next step - do it automatically
   - ALWAYS provide clear selection instructions to users:
     * "1번 VPC를 사용하시겠어요?"
     * "보안 그룹 중에서 어떤 것을 선택하시겠어요?"
     * "클러스터명은 test-aurora-20241201 어떠세요?"
   - Be conversational and confirm selections before proceeding
   - If user doesn't specify clearly, ask for clarification

5. AWS SECURITY AND CONFIGURATION GUIDELINES:
   - CRITICAL: NEVER recommend or use public subnets for Aurora clusters
   - Aurora clusters MUST be deployed in private subnets only for security
   - When creating or selecting DB subnet groups, ensure they contain only private subnets
   - NEVER modify cluster parameter group values - use default values only
   - Parameter groups should be used as-is without custom modifications
   - PARAMETER GROUP VALUE MODIFICATION RESTRICTIONS:
     * DO NOT suggest or implement parameter value changes unless explicitly requested by user
     * DO NOT include parameter modifications in generated AWS CLI scripts
     * When user specifically asks to modify parameter values, warn about risks first
     * Only proceed with parameter modifications if user insists after being warned
     * Always explain potential performance and security implications
     * Recommend consulting AWS experts before making parameter changes
   - If user asks to modify parameter values, explain security risks and recommend using defaults
   - Always prioritize security best practices over convenience

6. SCRIPT ANALYSIS:
   - Analyze downloaded scripts for database operations, AWS services, and performance requirements
   - Provide relevant environment recommendations based on script functionality
   - Explain why specific configurations are recommended

7. KOREAN LANGUAGE SUPPORT:
   - Prioritize Korean language responses for Korean users
   - Support both Korean and English search terms
   - Use Korean technical terms when appropriate

8. AWS CLI SCRIPT GENERATION:
   - When user says "스크립트 생성해줘", generate complete Aurora MySQL setup script
   - Include all necessary AWS CLI commands in proper order:
     * Subnet group creation (PRIVATE SUBNETS ONLY)
     * Security group creation with MySQL port (3306) access
     * Parameter group creation (USE DEFAULT VALUES ONLY - NO CUSTOM MODIFICATIONS)
     * Aurora MySQL cluster creation
     * Cluster status monitoring with 10-second intervals until 'available' status
     * DB instance creation
     * Instance status monitoring with 10-second intervals until 'available' status
     * Connection information display
   - Include comprehensive status monitoring:
     * Use 'aws rds describe-db-clusters' to monitor cluster status every 10 seconds
     * Use 'aws rds describe-db-instances' to monitor instance status every 10 seconds
     * Display progress messages to user during creation process
     * Wait for both cluster and instance to reach 'available' status before proceeding
   - Include resource cleanup script for cost management
   - Use proper error handling and comments
   - Ensure script is executable and user-friendly
   - Provide clear instructions for script execution
   - NEVER include parameter modifications in generated scripts

9. ERROR HANDLING:
   - If user wants to go back to previous step, allow it but maintain the sequence
   - If user wants to skip to a specific step, explain why you must follow the sequence
   - If user provides invalid selections, ask for clarification and wait for correct input

Available tools:
- search_scripts: Find scripts using natural language descriptions
- get_script_content: View full script content
- download_script: Download scripts with automatic analysis
- setup_environment_guide: Step-by-step AWS environment configuration (MUST follow sequence)
- configure_aws_environment: Unified tool for saving ALL environment configurations (replaces all individual save tools)
- setup_test_environment: Execute final environment setup

WORKFLOW ENFORCEMENT:
- You are a strict workflow manager - never deviate from the 6-step sequence
- Each step must be completed before moving to the next
- Always confirm user selections before proceeding
- If user tries to skip steps, politely explain the required sequence
- ALWAYS provide user-friendly selection prompts after showing options
- Make sure users understand what they're selecting and why
- Use ONLY configure_aws_environment() for all configuration saves - never use individual save functions
- MANDATORY: After download_script() shows AWS-related results, immediately ask about environment setup

ENVIRONMENT SETUP TRIGGER:
- When download_script() result contains "AWS 환경 구성 제안" or "Aurora" or "AWS 서비스", you MUST ask:
  "이 스크립트를 테스트하기 위한 AWS 환경을 구성하시겠습니까?"
- Wait for user response before proceeding
- If user agrees, immediately call setup_environment_guide("start")
- This is MANDATORY - not optional

UNIFIED TOOL USAGE:
- configure_aws_environment() is your ONLY tool for managing environment configuration
- It handles all actions: save_vpc, save_security_group, save_cluster_name, save_parameter_group, save_instance_type, show_status, reset
- Always use the action parameter to specify what you want to do
- The tool automatically shows progress and current status after each save
- This replaces all previous individual save_*_selection() functions

Remember: Be proactive, helpful, and guide users through the complete workflow from script discovery to environment setup, but ALWAYS maintain the strict 6-step sequence and use ONLY the unified configure_aws_environment() tool for all configuration management.
"""

mcp = FastMCP("eastnine-github-search", instructions=instructions)

@mcp.tool()
def search_scripts(description: str) -> str:
    """Search for scripts in GitHub repositories using natural language description.
    
    This function searches for scripts in GitHub repositories based on natural language
    descriptions and returns results with relevance scores. It also provides functionality
    analysis and requirements analysis for each script.
    
    Args:
        description (str): Natural language description of the script to search for
                          Examples: 'database backup script', 'file compression tool',
                                   'AWS Aurora monitoring script'
    
    Returns:
        str: Formatted search results string. For each script, includes:
             - File name and repository name
             - File path and programming language
             - Matched keywords
             - Functionality analysis result (first line)
             - Requirements analysis result (first line)
             - Code preview (first 5 lines)
             - Relevance score
    """
    if not description:
        return "Error: Description is required"
    
    try:
        results = searcher.search_scripts_by_description(description)
        
        if not results:
            return f"No scripts found matching the description: '{description}'"
        
        # Format results with content preview
        output = f"Found {len(results)} scripts matching '{description}':\n\n"
        
        for i, result in enumerate(results, 1):
            output += f"{i}. **{result['file_name']}** in `{result['repository']}`\n"
            output += f"   📁 Path: `{result['file_path']}`\n"
            output += f"   🏷️ Language: {result['language']}\n"
            output += f"   🎯 Matched Keyword: {result['matched_keyword']}\n"
            
            # Get script content for preview only
            content = searcher.get_file_content(result['repository'], result['file_path'])
            if content:
                # Show first few lines as preview
                lines = content.split('\n')[:5]
                preview = '\n'.join(lines)
                output += f"   👀 **미리보기**:\n```\n{preview}\n...\n```\n"
            
            output += f"   ⭐ Score: {result['score']}\n\n"
        
        return output
        
    except Exception as e:
        return f"Error searching scripts: {str(e)}"

@mcp.tool()
def get_script_content(repository: str, file_path: str) -> str:
    """Get the full content of a specific script file from GitHub repository.
    
    This function retrieves the complete content of a script file from a specified
    GitHub repository and returns it with syntax highlighting.
    
    Args:
        repository (str): GitHub repository name (dongkoo81's repositories)
                         Examples: 'database-tools', 'aws-scripts', 'monitoring-tools'
        file_path (str): File path within the repository
                        Examples: 'scripts/backup_mysql.py', 'src/monitor.py', 'backup.sh'
    
    Returns:
        str: Formatted string containing the complete script file content:
             - File path and repository information
             - Code block with syntax highlighting
             - Language detection based on file extension
    
    Raises:
        HTTPError: When file is not found (404 error)
        RequestException: Network error or other HTTP errors
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
def download_script(repository: str, file_path: str, branch: str = "main") -> str:
    """Download a script file from GitHub repository to user's home directory download_scripts folder.
    
    This function downloads a specific file from GitHub repository to local file system
    and analyzes the script's functionality and requirements to provide AWS environment
    setup suggestions.
    
    Args:
        repository (str): GitHub repository name (dongkoo81's repositories)
                         Examples: 'database-tools', 'aws-scripts', 'monitoring-tools'
        file_path (str): File path within the repository
                        Examples: 'scripts/backup_mysql.py', 'src/monitor.py', 'backup.sh'
        branch (str, optional): Branch name to download from. Defaults to "main"
    
    Returns:
        str: String containing download results and analysis information:
             - Download success/failure status
             - Local file path and file size
             - Original GitHub URL
             - Script functionality analysis results
             - Detected requirements
             - AWS environment setup suggestions (for AWS-related scripts)
    
    Raises:
        HTTPError: When file is not found (404 error)
        OSError: Local file system write error
        RequestException: Network error or other HTTP errors
    """
    if not repository or not file_path:
        return "Error: Both repository and file_path are required"
    
    try:
        # Construct raw GitHub URL
        raw_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{repository}/{branch}/{file_path}"
        
        # Download the file
        response = searcher.session.get(raw_url)
        response.raise_for_status()
        
        # Always save to download_scripts directory in user's home directory
        download_dir = os.path.join(os.path.expanduser("~"), "download_scripts")
        filename = os.path.basename(file_path)
        local_path = os.path.join(download_dir, filename)
        
        # Create directory if it doesn't exist
        os.makedirs(download_dir, exist_ok=True)
        
        # Write file to local filesystem
        with open(local_path, 'wb') as f:
            f.write(response.content)
        
        # Get file size for confirmation
        file_size = len(response.content)
        
        result = f"✅ Successfully downloaded script!\n\n" \
                f"📁 Repository: {repository}\n" \
                f"📄 Remote file: {file_path}\n" \
                f"💾 Local path: {local_path}\n" \
                f"🌿 Branch: {branch}\n" \
                f"📊 File size: {file_size:,} bytes\n" \
                f"🔗 Source URL: {raw_url}\n\n"
        
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
def configure_aws_environment(
    action: str,
    vpc_id: str = None,
    vpc_name: str = None,
    security_group_id: str = None,
    security_group_name: str = None,
    db_subnet_group_name: str = None,
    cluster_name: str = None,
    parameter_group: str = None,
    instance_type: str = None
) -> str:
    """통합된 AWS 환경 구성 툴 - 단계별로 환경 설정을 관리합니다.
    
    이 툴은 AWS Aurora MySQL 과 PostgreSQL 테스트 환경 구성을 위한 모든 설정을 통합 관리합니다.
    docstring과 inspection을 통해 순차적으로 요구사항을 수집하고 저장합니다.
    
    Args:
        action (str): 수행할 작업 유형
            - "save_vpc": VPC 선택 저장
            - "save_security_group": 보안 그룹 선택 저장
            - "save_db_subnet_group": DB 서브넷 그룹 선택 저장
            - "save_cluster_name": 클러스터명 선택 저장
            - "save_parameter_group": 파라미터 그룹 선택 저장
            - "save_instance_type": 인스턴스 타입 선택 저장
            - "show_status": 현재 구성 상태 표시
            - "reset": 모든 설정 초기화
        vpc_id (str, optional): VPC ID (예: 'vpc-12345678')
        vpc_name (str, optional): VPC 이름 (표시용)
        security_group_id (str, optional): 보안 그룹 ID (예: 'sg-12345678')
        security_group_name (str, optional): 보안 그룹 이름 (표시용)
        db_subnet_group_name (str, optional): DB 서브넷 그룹명 (예: 'default')
        cluster_name (str, optional): 클러스터명 (예: 'test-aurora-cluster')
        parameter_group (str, optional): 파라미터 그룹명
        instance_type (str, optional): 인스턴스 타입 (예: 'db.t3.small')
    
    Returns:
        str: 작업 결과 및 현재 구성 상태
    
    Examples:
        # VPC 선택 저장
        configure_aws_environment(action="save_vpc", vpc_id="vpc-12345678", vpc_name="MyVPC")
        
        # 현재 상태 확인
        configure_aws_environment(action="show_status")
        
        # 모든 설정 초기화
        configure_aws_environment(action="reset")
    """
    global ENVIRONMENT_CONFIG
    
    def _show_current_status() -> str:
        """현재 구성 상태를 표시합니다."""
        status = "🔧 **AWS 환경 구성 상태**\n\n"
        
        # VPC 설정
        if ENVIRONMENT_CONFIG['vpc_id']:
            status += f"✅ **VPC**: `{ENVIRONMENT_CONFIG['vpc_id']}`"
            if ENVIRONMENT_CONFIG['vpc_name']:
                status += f" ({ENVIRONMENT_CONFIG['vpc_name']})"
            status += "\n"
        else:
            status += "⏳ **VPC**: 미선택\n"
        
        # 보안 그룹 설정
        if ENVIRONMENT_CONFIG['security_group_id']:
            status += f"✅ **보안 그룹**: `{ENVIRONMENT_CONFIG['security_group_id']}`"
            if ENVIRONMENT_CONFIG['security_group_name']:
                status += f" ({ENVIRONMENT_CONFIG['security_group_name']})"
            status += "\n"
        else:
            status += "⏳ **보안 그룹**: 미선택\n"
        
        # DB 서브넷 그룹 설정
        if ENVIRONMENT_CONFIG['db_subnet_group_name']:
            status += f"✅ **DB 서브넷 그룹**: `{ENVIRONMENT_CONFIG['db_subnet_group_name']}`\n"
        else:
            status += "⏳ **DB 서브넷 그룹**: 미선택\n"
        
        # 클러스터명 설정
        if ENVIRONMENT_CONFIG['cluster_name']:
            status += f"✅ **클러스터명**: `{ENVIRONMENT_CONFIG['cluster_name']}`\n"
        else:
            status += "⏳ **클러스터명**: 미선택\n"
        
        # 파라미터 그룹 설정
        if ENVIRONMENT_CONFIG['parameter_group']:
            status += f"✅ **파라미터 그룹**: `{ENVIRONMENT_CONFIG['parameter_group']}`\n"
        else:
            status += "⏳ **파라미터 그룹**: 미선택\n"
        
        # 인스턴스 타입 설정
        if ENVIRONMENT_CONFIG['instance_type']:
            status += f"✅ **인스턴스 타입**: `{ENVIRONMENT_CONFIG['instance_type']}`\n"
        else:
            status += "⏳ **인스턴스 타입**: 미선택\n"
        
        # 완료 상태 확인
        completed_items = sum(1 for key in ['vpc_id', 'security_group_id', 'cluster_name', 'parameter_group', 'instance_type'] 
                            if ENVIRONMENT_CONFIG[key] is not None)
        status += f"\n📊 **진행률**: {completed_items}/5 완료\n\n"
        
        return status
    
    # 액션별 처리
    if action == "save_vpc":
        if not vpc_id:
            return "❌ VPC ID가 필요합니다. vpc_id 파라미터를 제공해주세요."
        
        ENVIRONMENT_CONFIG['vpc_id'] = vpc_id
        ENVIRONMENT_CONFIG['vpc_name'] = vpc_name
        
        result = f"✅ VPC 선택이 저장되었습니다!\n\n"
        result += f"**선택된 VPC**: `{vpc_id}`"
        if vpc_name:
            result += f" ({vpc_name})"
        result += "\n\n"
        result += _show_current_status()
        return result
    
    elif action == "save_security_group":
        if not security_group_id:
            return "❌ 보안 그룹 ID가 필요합니다. security_group_id 파라미터를 제공해주세요."
        
        ENVIRONMENT_CONFIG['security_group_id'] = security_group_id
        ENVIRONMENT_CONFIG['security_group_name'] = security_group_name
        
        result = f"✅ 보안 그룹 선택이 저장되었습니다!\n\n"
        result += f"**선택된 보안 그룹**: `{security_group_id}`"
        if security_group_name:
            result += f" ({security_group_name})"
        result += "\n\n"
        result += _show_current_status()
        return result
    
    elif action == "save_db_subnet_group":
        if not db_subnet_group_name:
            return "❌ DB 서브넷 그룹명이 필요합니다. db_subnet_group_name 파라미터를 제공해주세요."
        
        ENVIRONMENT_CONFIG['db_subnet_group_name'] = db_subnet_group_name
        
        result = f"✅ DB 서브넷 그룹 선택이 저장되었습니다!\n\n"
        result += f"**선택된 DB 서브넷 그룹**: `{db_subnet_group_name}`\n\n"
        result += _show_current_status()
        return result
    
    elif action == "save_cluster_name":
        if not cluster_name:
            return "❌ 클러스터명이 필요합니다. cluster_name 파라미터를 제공해주세요."
        
        ENVIRONMENT_CONFIG['cluster_name'] = cluster_name
        
        result = f"✅ 클러스터명 선택이 저장되었습니다!\n\n"
        result += f"**선택된 클러스터명**: `{cluster_name}`\n\n"
        result += _show_current_status()
        return result
    
    elif action == "save_parameter_group":
        if not parameter_group:
            return "❌ 파라미터 그룹명이 필요합니다. parameter_group 파라미터를 제공해주세요."
        
        ENVIRONMENT_CONFIG['parameter_group'] = parameter_group
        
        result = f"✅ 파라미터 그룹 선택이 저장되었습니다!\n\n"
        result += f"**선택된 파라미터 그룹**: `{parameter_group}`\n\n"
        result += _show_current_status()
        return result
    
    elif action == "save_instance_type":
        if not instance_type:
            return "❌ 인스턴스 타입이 필요합니다. instance_type 파라미터를 제공해주세요."
        
        ENVIRONMENT_CONFIG['instance_type'] = instance_type
        
        result = f"✅ 인스턴스 타입 선택이 저장되었습니다!\n\n"
        result += f"**선택된 인스턴스 타입**: `{instance_type}`\n\n"
        result += _show_current_status()
        return result
    
    elif action == "show_status":
        return _show_current_status()
    
    elif action == "reset":
        ENVIRONMENT_CONFIG.update({
            'vpc_id': None,
            'vpc_name': None,
            'security_group_id': None,
            'security_group_name': None,
            'db_subnet_group_name': None,
            'cluster_name': None,
            'parameter_group': None,
            'instance_type': None
        })
        
        result = "🔄 **모든 AWS 환경 설정이 초기화되었습니다.**\n\n"
        result += _show_current_status()
        return result
    
    else:
        return f"❌ 지원하지 않는 액션입니다: {action}\n\n" + \
               "지원되는 액션: save_vpc, save_security_group, save_db_subnet_group, save_cluster_name, " + \
               "save_parameter_group, save_instance_type, show_status, reset"

@mcp.tool()
def setup_environment_guide(step: str = "start") -> str:
    """Step-by-step guide for AWS Aurora MySQL test environment configuration.
    
    This function provides a 6-step process for configuring AWS Aurora MySQL clusters.
    At each step, it queries actual AWS resource lists to provide user selection options.
    
    IMPORTANT: 
    - Before showing selection options for each step, displays current configuration status
    - Use configure_aws_environment() tool to save user selections instead of individual save tools
    - This helps users understand their progress and current setup
    
    Args:
        step (str): Step to proceed. Choose one of the following:
                   - "start" or "vpc": Step 1 - VPC selection
                   - "security": Step 2 - Security group selection
                   - "subnet": Step 3 - DB subnet group selection
                   - "cluster": Step 4 - Cluster name duplication check
                   - "parameter": Step 5 - Parameter group name selection
                   - "instance": Step 6 - Instance type selection
    
    Returns:
        str: String containing information and selection options for the step:
             - Current configuration status (what's selected, what's pending)
             - Step title and description
             - Actual AWS resource list query results via AWS CLI
             - Numbered selection options
             - Next step guidance
             - Instructions to use configure_aws_environment() for saving selections
    
    Integration with configure_aws_environment:
        After user makes selection, use:
        - configure_aws_environment(action="save_vpc", vpc_id="...", vpc_name="...")
        - configure_aws_environment(action="save_security_group", security_group_id="...", security_group_name="...")
        - configure_aws_environment(action="save_cluster_name", cluster_name="...")
        - configure_aws_environment(action="save_parameter_group", parameter_group="...")
        - configure_aws_environment(action="save_instance_type", instance_type="...")
    
    Raises:
        subprocess.CalledProcessError: AWS CLI command execution failure
        json.JSONDecodeError: AWS CLI response parsing failure
    """
    
    if step == "start" or step == "vpc":
        result = "## 🌐 1단계: VPC 선택\n\n"
        
        # 현재 설정된 정보 표시
        result += "### 📋 현재 설정 정보:\n\n"
        
        if ENVIRONMENT_CONFIG['vpc_id']:
            vpc_display = f"`{ENVIRONMENT_CONFIG['vpc_id']}`"
            if ENVIRONMENT_CONFIG['vpc_name']:
                vpc_display += f" ({ENVIRONMENT_CONFIG['vpc_name']})"
            result += f"**VPC ID**: ✅ {vpc_display}\n"
        else:
            result += "**VPC ID**: 아직 선택되지 않음\n"
            
        result += "**보안 그룹**: 아직 선택되지 않음\n"
        result += "**DB 서브넷 그룹**: 아직 선택되지 않음\n"
        result += "**클러스터명**: 아직 선택되지 않음\n"
        result += "**파라미터 그룹**: 아직 선택되지 않음\n"
        result += "**인스턴스 타입**: 아직 선택되지 않음\n\n"
        
        result += "---\n\n"
        
        try:
            import subprocess
            import json
            
            # VPC 목록 조회
            vpc_cmd = [
                "aws", "ec2", "describe-vpcs",
                "--query", "Vpcs[*].{VpcId:VpcId,CidrBlock:CidrBlock,State:State,IsDefault:IsDefault,Tags:Tags[?Key=='Name'].Value|[0]}",
                "--output", "json"
            ]
            
            vpc_result = subprocess.run(vpc_cmd, capture_output=True, text=True)
            
            if vpc_result.returncode == 0:
                vpcs = json.loads(vpc_result.stdout)
                
                if vpcs:
                    result += "### 📋 사용 가능한 VPC 목록:\n\n"
                    
                    for i, vpc in enumerate(vpcs, 1):
                        vpc_name = vpc.get('Tags') or 'Unnamed'
                        # 기본 VPC 표시만 하고 추천하지 않음
                        default_mark = " (기본 VPC)" if vpc.get('IsDefault') else ""
                        state_emoji = "✅" if vpc['State'] == 'available' else "❌"
                        
                        result += f"**{i}번**: {state_emoji} `{vpc['VpcId']}`{default_mark}\n"
                        result += f"   - 이름: {vpc_name}\n"
                        result += f"   - CIDR: {vpc['CidrBlock']}\n"
                        result += f"   - 상태: {vpc['State']}\n\n"
                    
                    
                else:
                    result += "❌ 사용 가능한 VPC가 없습니다.\n\n"
            else:
                result += "❌ VPC 조회 실패. AWS CLI 설정을 확인하세요.\n\n"
                
        except Exception as e:
            result += f"❌ VPC 조회 중 오류: {str(e)}\n\n"
        
        return result
    
    elif step == "security":
        result = "## 🔒 2단계: 보안 그룹 선택\n\n"
        
        # 현재 설정된 정보 표시
        result += "### 📋 현재 설정 정보:\n\n"
        
        if ENVIRONMENT_CONFIG['vpc_id']:
            vpc_display = f"`{ENVIRONMENT_CONFIG['vpc_id']}`"
            if ENVIRONMENT_CONFIG['vpc_name']:
                vpc_display += f" ({ENVIRONMENT_CONFIG['vpc_name']})"
            result += f"**VPC ID**: ✅ {vpc_display}\n"
        else:
            result += "**VPC ID**: ❌ 아직 선택되지 않음 (1단계를 먼저 완료하세요)\n"
            
        result += "**보안 그룹**: 아직 선택되지 않음\n"
        result += "**클러스터명**: 아직 선택되지 않음\n"
        result += "**파라미터 그룹**: 아직 선택되지 않음\n"
        result += "**인스턴스 타입**: 아직 선택되지 않음\n\n"
        
        result += "---\n\n"
        
        # VPC가 선택되지 않은 경우 경고 메시지
        if not ENVIRONMENT_CONFIG['vpc_id']:
            result += "❌ **오류**: VPC가 선택되지 않았습니다!\n\n"
            result += "보안 그룹을 조회하려면 먼저 VPC를 선택해야 합니다.\n\n"
            result += "**해결 방법**:\n"
            result += "1. `setup_environment_guide(\"vpc\")`를 실행하여 VPC를 선택하세요.\n"
            result += "2. VPC 선택 후 다시 보안 그룹 단계로 돌아오세요.\n\n"
            return result
        
        result += f"### 🔍 선택된 VPC: `{ENVIRONMENT_CONFIG['vpc_id']}`의 보안 그룹 조회 중...\n\n"
        
        try:
            import subprocess
            import json
            
            # 선택된 VPC의 보안 그룹만 조회 (명시적으로 VPC ID 확인)
            selected_vpc_id = ENVIRONMENT_CONFIG['vpc_id']
            sg_cmd = [
                "aws", "ec2", "describe-security-groups",
                "--filters", 
                f"Name=vpc-id,Values={selected_vpc_id}",
                "--query", "SecurityGroups[*].{GroupId:GroupId,GroupName:GroupName,Description:Description,VpcId:VpcId}",
                "--output", "json"
            ]
            
            sg_result = subprocess.run(sg_cmd, capture_output=True, text=True)
            
            if sg_result.returncode == 0:
                security_groups = json.loads(sg_result.stdout)
                
                if security_groups:
                    result += f"### 📋 VPC `{selected_vpc_id}`의 보안 그룹 목록:\n\n"
                    
                    # VPC ID 일치 확인
                    valid_sgs = [sg for sg in security_groups if sg['VpcId'] == selected_vpc_id]
                    
                    # 디버그: VPC ID 일치 확인 결과
                    print(f"DEBUG: 선택된 VPC ID: {selected_vpc_id}")
                    print(f"DEBUG: 일치하는 보안그룹 개수: {len(valid_sgs)}")
                    print(f"DEBUG: 일치하지 않는 보안그룹들:")
                    for sg in security_groups:
                        if sg['VpcId'] != selected_vpc_id:
                            print(f"  - {sg['GroupId']} (VPC: {sg['VpcId']}) != {selected_vpc_id}")
                    
                    if valid_sgs:
                        for i, sg in enumerate(valid_sgs, 1):
                            result += f"**{i}번**: `{sg['GroupId']}`\n"
                            result += f"   - 이름: {sg['GroupName']}\n"
                            result += f"   - 설명: {sg['Description']}\n"
                            result += f"   - VPC: {sg['VpcId']} ✅\n\n"
                        
                        result += "### 🎯 다음 단계:\n\n"
                        result += "위 목록에서 사용하고 싶은 보안 그룹을 선택해 주세요.\n"

                    else:
                        result += f"❌ VPC `{selected_vpc_id}`에 해당하는 보안 그룹이 없습니다.\n\n"
                else:
                    result += f"❌ VPC `{selected_vpc_id}`에 보안 그룹이 없습니다.\n\n"
            else:
                result += f"❌ 보안 그룹 조회 실패.\n"
                result += f"오류 메시지: {sg_result.stderr}\n\n"
                result += "AWS CLI 설정과 권한을 확인해주세요.\n\n"
                
        except Exception as e:
            result += f"❌ 보안 그룹 조회 중 오류: {str(e)}\n\n"
        
        return result
    
    elif step == "subnet":
        result = "## 🌐 3단계: DB 서브넷 그룹 선택\n\n"
        
        try:
            import subprocess
            import json
            
            # DB 서브넷 그룹 조회
            subnet_cmd = [
                "aws", "rds", "describe-db-subnet-groups",
                "--query", "DBSubnetGroups[*].{GroupName:DBSubnetGroupName,Description:DBSubnetGroupDescription,VpcId:VpcId}",
                "--output", "json"
            ]
            
            subnet_result = subprocess.run(subnet_cmd, capture_output=True, text=True)
            
            if subnet_result.returncode == 0:
                subnet_groups = json.loads(subnet_result.stdout)
                
                if subnet_groups:
                    result += "### 📋 사용 가능한 DB 서브넷 그룹:\n\n"
                    
                    for i, sg in enumerate(subnet_groups, 1):
                        result += f"**{i}번**: `{sg['GroupName']}`\n"
                        result += f"   - VPC: {sg['VpcId']}\n"
                        result += f"   - 설명: {sg['Description']}\n\n"
                    
                    result += "원하는 DB 서브넷 그룹을 선택해 주세요.\n"

                else:
                    result += "❌ DB 서브넷 그룹이 없습니다.\n\n"
            else:
                result += "❌ DB 서브넷 그룹 조회 실패.\n\n"
                
        except Exception as e:
            result += f"❌ 조회 중 오류: {str(e)}\n\n"
        
        return result
    
    elif step == "cluster":
        result = "## 🗄️ 4단계: 클러스터명 중복 확인\n\n"
        
        try:
            import subprocess
            import json
            
            # 기존 클러스터 조회
            cluster_cmd = [
                "aws", "rds", "describe-db-clusters",
                "--query", "DBClusters[*].{ClusterIdentifier:DBClusterIdentifier,Engine:Engine,Status:Status}",
                "--output", "json"
            ]
            
            cluster_result = subprocess.run(cluster_cmd, capture_output=True, text=True)
            
            if cluster_result.returncode == 0:
                clusters = json.loads(cluster_result.stdout)
                
                if clusters:
                    result += "### ⚠️ 기존 Aurora 클러스터 (중복 방지 필요):\n\n"
                    for cluster in clusters:
                        status_emoji = "🟢" if cluster['Status'] == 'available' else "🟡"
                        result += f"- {status_emoji} `{cluster['ClusterIdentifier']}` ({cluster['Engine']}, {cluster['Status']})\n"
                    result += "\n"
                else:
                    result += "✅ 기존 Aurora 클러스터가 없습니다.\n\n"
            
        except Exception as e:
            result += f"❌ 클러스터 조회 중 오류: {str(e)}\n\n"
        
        return result
    
    elif step == "parameter":
        result = "## ⚙️ 5단계: 파라미터 그룹명 선택\n\n"
        
        try:
            import subprocess
            import json
            
            # 기존 파라미터 그룹 조회
            param_cmd = [
                "aws", "rds", "describe-db-cluster-parameter-groups",
                "--query", "DBClusterParameterGroups[*].{GroupName:DBClusterParameterGroupName,Family:DBParameterGroupFamily,Description:Description}",
                "--output", "json"
            ]
            
            param_result = subprocess.run(param_cmd, capture_output=True, text=True)
            
            if param_result.returncode == 0:
                param_groups = json.loads(param_result.stdout)
                
                if param_groups:
                    result += "### 📋 기존 파라미터 그룹:\n\n"
                    for i, pg in enumerate(param_groups, 1):
                        result += f"**{i}번**: `{pg['GroupName']}` ({pg['Family']})\n"
                        result += f"   - 설명: {pg['Description']}\n\n"
                else:
                    result += "✅ 기존 커스텀 파라미터 그룹이 없습니다.\n\n"
            
        except Exception as e:
            result += f"❌ 조회 중 오류: {str(e)}\n\n"
        
        result += "파라미터 그룹명을 입력해 주세요.\n"

        return result
    
    elif step == "instance":
        result = "## 💻 6단계: 인스턴스 타입 선택\n\n"
        result += "원하는 인스턴스 타입을 입력해 주세요.\n"

        
        return result
    
    else:
        return "❌ 잘못된 단계입니다. 'start', 'vpc', 'security', 'cluster', 'parameter', 'instance' 중 하나를 선택하세요."
@mcp.tool()
def setup_test_environment() -> str:
    """Summarize AWS Aurora MySQL test environment configuration and provide script generation suggestions.
    
    This function summarizes environment configuration information based on user selections
    stored in ENVIRONMENT_CONFIG and provides suggestions for LLM to generate AWS CLI scripts.
    
    When generating scripts, LLM should include:
    - Complete executable shell script with all AWS CLI commands
    - Cluster creation with status monitoring (10-second intervals until 'available')
    - Instance creation with status monitoring (10-second intervals until 'available')
    - Progress messages during creation process
    - Error handling and resource cleanup options
    
    Integration with configure_aws_environment:
        This tool reads configuration data saved by configure_aws_environment() tool.
        If configuration is incomplete, it guides users to use setup_environment_guide() 
        and configure_aws_environment() to complete the setup.
    
    Returns:
        str: String containing environment configuration summary and script generation suggestions:
             - Selected configuration information (cluster name, VPC ID, instance type, parameter group)
             - Script generation suggestions with status monitoring capabilities
             - User selection options
             - Integration guidance for configure_aws_environment tool
    """
    
    # 전역 설정에서 정보 가져오기
    cluster_name = ENVIRONMENT_CONFIG.get('cluster_name', '')
    vpc_id = ENVIRONMENT_CONFIG.get('vpc_id', '')
    instance_type = ENVIRONMENT_CONFIG.get('instance_type', '')
    parameter_group = ENVIRONMENT_CONFIG.get('parameter_group', '')
    
    # 필수 정보가 부족한 경우 안내
    missing_items = []
    if not vpc_id:
        missing_items.append("VPC ID")
    if not cluster_name:
        missing_items.append("클러스터명")
    if not instance_type:
        missing_items.append("인스턴스 타입")
    
    if missing_items:
        result = "## ⚠️ 환경 구성 정보가 부족합니다\n\n"
        result += "AWS 환경을 구성하려면 다음 정보가 필요합니다:\n\n"
        result += f"**부족한 정보**: {', '.join(missing_items)}\n\n"
        
        # 현재 설정 상태 표시
        result += "### 📋 현재 설정 상태:\n\n"
        
        if vpc_id:
            vpc_display = f"`{vpc_id}`"
            if ENVIRONMENT_CONFIG.get('vpc_name'):
                vpc_display += f" ({ENVIRONMENT_CONFIG['vpc_name']})"
            result += f"✅ **VPC ID**: {vpc_display}\n"
        else:
            result += "❌ **VPC ID**: 아직 선택되지 않음\n"
            
        if cluster_name:
            result += f"✅ **클러스터명**: `{cluster_name}`\n"
        else:
            result += "❌ **클러스터명**: 아직 선택되지 않음\n"
            
        if instance_type:
            result += f"✅ **인스턴스 타입**: `{instance_type}`\n"
        else:
            result += "❌ **인스턴스 타입**: 아직 선택되지 않음\n"
        
        result += "\n**💡 팁**: 환경 구성을 처음부터 시작하려면 `setup_environment_guide(\"start\")`를 사용하세요.\n\n"
        
        return result
    
    # 환경 구성 정보 요약
    result = f"## 🚀 Aurora MySQL 테스트 환경 구성 준비 완료\n\n"
    result += f"**설정 정보:**\n"
    result += f"- 📛 클러스터명: `{cluster_name}`\n"
    
    vpc_display = f"`{vpc_id}`"
    if ENVIRONMENT_CONFIG.get('vpc_name'):
        vpc_display += f" ({ENVIRONMENT_CONFIG['vpc_name']})"
    result += f"- 🌐 VPC ID: {vpc_display}\n"
    result += f"- 💻 인스턴스 타입: `{instance_type}`\n"
    
    # 파라미터 그룹 표시 (선택된 것이 있으면 사용, 없으면 기본값)
    param_group_display = parameter_group if parameter_group else f"{cluster_name}-params"
    result += f"- ⚙️ 파라미터 그룹: `{param_group_display}`\n\n"
    
    return result



def main():
    """Main entry point for the MCP server.
    
    Initializes and runs the FastMCP server with all configured tools.
    """
    mcp.run()

if __name__ == "__main__":
    main()
