# EastNine GitHub Search MCP Server

A comprehensive Model Context Protocol (MCP) server that enables natural language searching of scripts in personal GitHub repositories and provides step-by-step AWS Aurora MySQL environment setup capabilities. This server allows AI assistants to search through dongkoo81's GitHub repositories, analyze scripts, and configure AWS test environments.

## Features

- **Natural Language Search**: Search for scripts using descriptive queries
- **Script Analysis**: Automatic functionality and requirements analysis
- **AWS Environment Setup**: Step-by-step Aurora MySQL cluster configuration
- **Multi-language Support**: Supports various script file types including Python, JavaScript, Shell, and more
- **GitHub Integration**: Direct integration with GitHub API for real-time repository access
- **AWS CLI Integration**: Real-time AWS resource queries and environment configuration
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
- AWS CLI configured with appropriate permissions
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

4. **Configure AWS CLI**:
   ```bash
   # Configure AWS credentials
   aws configure
   
   # Or set environment variables
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_DEFAULT_REGION=your_region
   ```

5. **Create GitHub Personal Access Token**:
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

### Script Search and Analysis

#### `search_scripts`
Search for scripts in GitHub repositories using natural language.

**Parameters**:
- `description` (string): Natural language description of what you're looking for

**Example**:
```python
search_scripts(description="Python script for database backup")
search_scripts(description="AWS Aurora monitoring script")
```

#### `get_script_content`
Get the full content of a specific script file.

**Parameters**:
- `repository` (string): GitHub repository name
- `file_path` (string): File path within the repository

#### `download_script`
Download a script file to local system with automatic analysis.

**Parameters**:
- `repository` (string): GitHub repository name
- `file_path` (string): File path within the repository
- `branch` (string, optional): Branch name (default: "main")

### AWS Environment Setup

#### `setup_environment_guide`
Step-by-step guide for AWS Aurora MySQL environment configuration.

**Parameters**:
- `step` (string): Configuration step ("start", "vpc", "security", "subnet", "cluster", "parameter", "instance")

**6-Step Process**:
1. **VPC Selection**: Choose or create VPC for Aurora cluster
2. **Security Group**: Configure security groups with MySQL port access
3. **DB Subnet Group**: Select subnet groups (private subnets only)
4. **Cluster Name**: Define unique cluster identifier
5. **Parameter Group**: Configure cluster parameter groups
6. **Instance Type**: Select appropriate instance type

#### `configure_aws_environment`
Unified tool for saving environment configurations.

**Parameters**:
- `action` (string): Action type ("save_vpc", "save_security_group", "save_db_subnet_group", "save_cluster_name", "save_parameter_group", "save_instance_type", "show_status", "reset")
- Various resource-specific parameters

#### `setup_test_environment`
Generate complete AWS CLI scripts for Aurora cluster creation with status monitoring.

## AWS Security Guidelines

### Network Security
- **Private Subnets Only**: Aurora clusters must be deployed in private subnets
- **No Public Access**: Public subnet usage is prohibited for security
- **Security Groups**: Proper MySQL port (3306) configuration

### Configuration Security
- **Default Parameters**: Parameter groups use default values only
- **No Custom Modifications**: Parameter value changes require explicit user request
- **Expert Consultation**: Recommend AWS expert consultation for parameter changes

## Script Generation Features

When generating AWS CLI scripts, the server includes:

- **Complete Setup**: All necessary AWS CLI commands in proper order
- **Status Monitoring**: 10-second interval monitoring for cluster and instance creation
- **Progress Display**: Real-time status updates during creation process
- **Error Handling**: Comprehensive error checking and recovery
- **Resource Cleanup**: Optional cleanup scripts for cost management
- **Security Compliance**: Adherence to AWS security best practices

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
| `AWS_ACCESS_KEY_ID` | AWS Access Key ID | Yes |
| `AWS_SECRET_ACCESS_KEY` | AWS Secret Access Key | Yes |
| `AWS_DEFAULT_REGION` | AWS Default Region | Yes |

## Security Notes

- Keep your GitHub token secure and never commit it to version control
- The token should have minimal required permissions (repo scope for private repos)
- Configure AWS credentials securely using AWS CLI or environment variables
- Follow AWS security best practices for Aurora cluster deployment
- Use private subnets only for database deployments
- Avoid modifying parameter group values without expert consultation

## Use Cases

### Script Discovery
- Find database backup scripts
- Locate AWS automation tools
- Search for monitoring solutions
- Discover deployment scripts

### AWS Environment Setup
- Configure Aurora MySQL test environments
- Set up development databases
- Create staging environments
- Generate production-ready scripts

### Development Workflow
- Download and analyze scripts
- Configure AWS resources
- Generate deployment scripts
- Monitor resource creation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Changelog

### v0.2.0 (2025-08-18)
- Added comprehensive AWS Aurora MySQL environment setup
- Implemented 6-step configuration process
- Added DB subnet group selection
- Enhanced security guidelines and restrictions
- Added status monitoring for cluster and instance creation
- Improved script analysis and requirements detection

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
- Verify AWS CLI configuration and permissions

---

Built with ❤️ using the Model Context Protocol (MCP) framework for comprehensive script management and AWS environment automation.
