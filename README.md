# EastNine GitHub Search MCP Server

A Model Context Protocol (MCP) server that helps team members quickly find scripts in your personal GitHub repositories using natural language descriptions.

## Features

- 🔍 **Natural Language Search**: Describe what you're looking for in plain language (e.g., "file compression script", "database backup tool")
- 📁 **Personal Repository Focus**: Searches only in your public GitHub repositories
- 🎯 **Script Detection**: Automatically identifies script files based on common extensions
- 📖 **Content Retrieval**: Get the full content of any found script
- ⚡ **Fast Results**: Efficient search with relevance scoring

## Installation

1. Clone this repository:
```bash
git clone <your-repo-url>
cd eastnine-github-search
```

2. Install dependencies:
```bash
pip install -e .
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your GitHub credentials
```

4. Get a GitHub Personal Access Token:
   - Go to GitHub Settings > Developer settings > Personal access tokens
   - Generate a new token with `public_repo` scope
   - Add it to your `.env` file

## Configuration

Create a `.env` file with your GitHub token:

```env
GITHUB_TOKEN=your_github_personal_access_token
```

Or set it in your MCP client configuration:

```json
{
  "mcpServers": {
    "eastnine-github-search": {
      "command": "eastnine-github-search",
      "env": {
        "GITHUB_TOKEN": "your_github_personal_access_token"
      }
    }
  }
}
```

## Usage

### With MCP Client

Add this server to your MCP client configuration:

```json
{
  "mcpServers": {
    "eastnine-github-search": {
      "command": "eastnine-github-search"
    }
  }
}
```

### Available Tools

#### 1. `search_scripts`
Search for scripts using natural language description.

**Parameters:**
- `description` (string): Natural language description of what you're looking for

**Example:**
```
Search for "파일 압축하는 스크립트" (file compression script)
```

#### 2. `get_script_content`
Get the full content of a specific script file.

**Parameters:**
- `repository` (string): Repository name
- `file_path` (string): Path to the script file

**Example:**
```
Get content of "backup.py" from "my-scripts" repository
```

## Supported Script Types

The server recognizes these file extensions as scripts:
- Python: `.py`
- JavaScript/TypeScript: `.js`, `.ts`
- Shell scripts: `.sh`, `.bash`, `.zsh`, `.fish`
- PowerShell: `.ps1`
- Batch files: `.bat`, `.cmd`
- Ruby: `.rb`
- PHP: `.php`
- Perl: `.pl`
- Go: `.go`
- Rust: `.rs`
- Java: `.java`
- And many more...

## How It Works

1. **Keyword Extraction**: Converts natural language descriptions into relevant search keywords
2. **Repository Scanning**: Searches through all your public GitHub repositories
3. **Content Matching**: Uses GitHub's code search API to find relevant files
4. **Script Filtering**: Filters results to show only script files
5. **Relevance Scoring**: Ranks results by relevance and returns the top matches

## Korean Language Support

The server includes Korean keyword mapping for common terms:
- 압축 → compress, zip, archive
- 백업 → backup, dump, export
- 데이터베이스 → database, sql, mysql
- 서버 → server, api, web
- And more...

## Development

To run the server directly:

```bash
python -m src.eastnine_github_search.server
```

## License

MIT License
