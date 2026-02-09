# Simple MCP Server

A basic Model Context Protocol (MCP) server for testing deployment.

## Features

- 4 simple tools: `add`, `multiply`, `greet`, `get_server_info`
- 1 resource: `demo://ping`
- No authentication (simplified for deployment testing)

## Setup

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Server

```bash
python server.py
```

The server will start on `http://0.0.0.0:8000`

## Testing

### Using MCP Inspector

1. Open MCP Inspector
2. Connect to: `http://localhost:8000`
3. Test the available tools and resources

### Using curl

```bash
# Check if server is running
curl http://localhost:8000/health

# Access MCP endpoint
curl http://localhost:8000/mcp/v1/sse
```

## Deployment

### Local Deployment
```bash
python server.py
```

### Using Docker (if you have Dockerfile)
```bash
docker build -t mcp-server .
docker run -p 8000:8000 mcp-server
```

### Deploy to Cloud Platforms

The server can be deployed to:
- **Heroku**: Push to Heroku with the included Procfile
- **Railway**: Connect your repo and deploy
- **Fly.io**: Use `fly launch`
- **Render**: Connect repo and set start command to `python server.py`

## Available Tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `add` | `a: int, b: int` | Add two numbers |
| `multiply` | `a: int, b: int` | Multiply two numbers |
| `greet` | `name: str` | Greet someone by name |
| `get_server_info` | none | Get server information |

## Available Resources

| Resource | Description |
|----------|-------------|
| `demo://ping` | Returns "pong" |

## Requirements

- Python 3.10+
- Dependencies listed in `requirements.txt`

## License

MIT
