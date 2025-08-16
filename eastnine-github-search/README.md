# EastNine GitHub Search MCP Server

A Model Context Protocol (MCP) server that enables natural language searching of scripts in personal GitHub repositories. This server allows AI assistants to search through dongkoo81's GitHub repositories to find relevant scripts and code files based on natural language descriptions.

## Features

- **Natural Language Search**: Search for scripts using descriptive queries
- **Multi-language Support**: Supports various script file types including Python, JavaScript, Shell, and more
- **GitHub Integration**: Direct integration with GitHub API for real-time repository access
- **MCP Compatible**: Built on the Model Context Protocol standard for seamless AI assistant integration

## Supported File Types

The server searches for scripts with the following extensions:
- **Python**: `.py`
- **JavaScript/TypeScript**: `.js`, `.ts`
- **Shell Scripts**: `.sh`, `.bash`, `.zsh`, `.fish`
- **Windows Scripts**: `.ps1`, `.bat`, `.cmd`
- **Other Languages**: `.rb`, `.php`, `.pl`, `.go`, `.rs`, `.java`, `.scala`, `.kt`, `.swift`, `.r`, `.R`, `.sql`, `.lua`, `.vim`, `.awk`, `.sed`

## Installation

### Prerequisites

- Python 3.10 or higher
- GitHub Personal Access Token
- uv (recommended) or pip

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/dongkoo81/eastnine-github-search.git
   cd eastnine-github-search
   ```

2. **Install dependencies**:
   ```bash
   # Using uv (recommended)
   uv sync

   # Or using pip
   pip install -e .
   ```

3. **Configure GitHub Token**:
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env and add your GitHub token
   echo "GITHUB_TOKEN=your_github_personal_access_token_here" > .env
   ```

4. **Create GitHub Personal Access Token**:
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Generate a new token with `repo` scope for private repositories
   - Copy the token to your `.env` file

## Usage

### As MCP Server

The server can be used with any MCP-compatible AI assistant:

```bash
# Run the server directly
python -m eastnine_github_search

# Or use the installed script
eastnine-github-search
```

### Configuration for AI Assistants

Add this server to your AI assistant's MCP configuration:

```json
{
  "mcpServers": {
    "eastnine-github-search": {
      "command": "eastnine-github-search",
      "env": {
        "GITHUB_TOKEN": "your_github_token_here"
      }
    }
  }
}
```

## Available Tools

The MCP server provides the following tools:

### `search_github_scripts`

Search for scripts in GitHub repositories using natural language.

**Parameters**:
- `query` (string): Natural language description of what you're looking for
- `limit` (integer, optional): Maximum number of results to return (default: 10)

**Example**:
```python
# Search for Python automation scripts
search_github_scripts(query="Python script for file automation", limit=5)

# Search for shell scripts related to deployment
search_github_scripts(query="bash script for deployment")
```

## Development

### Project Structure

```
eastnine-github-search/
├── src/
│   └── eastnine_github_search/
│       ├── __init__.py
│       ├── __main__.py
│       └── server.py          # Main MCP server implementation
├── pyproject.toml             # Project configuration
├── uv.lock                    # Dependency lock file
├── .env.example               # Environment template
├── .gitignore
└── README.md
```

### Running in Development

```bash
# Install in development mode
uv sync

# Run the server
python -m eastnine_github_search

# Or run directly
python src/eastnine_github_search/server.py
```

### Testing

```bash
# Test the MCP server
mcp-client test eastnine-github-search
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GITHUB_TOKEN` | GitHub Personal Access Token with repo access | Yes |

## Security Notes

- Keep your GitHub token secure and never commit it to version control
- The token should have minimal required permissions (repo scope for private repos)
- Consider using environment-specific tokens for different deployments

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Changelog

### v0.1.0 (2025-08-16)
- Initial release
- Basic GitHub repository search functionality
- MCP server implementation
- Support for multiple script file types
- Natural language query processing

## Support

For issues and questions:
- Create an issue on GitHub
- Check the documentation for common problems
- Ensure your GitHub token has the correct permissions

---

Built with ❤️ using the Model Context Protocol (MCP) framework.
