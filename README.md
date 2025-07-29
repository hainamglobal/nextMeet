# Sae Video Conferencing App

A comprehensive video conferencing application built with Frappe framework that acts as an intermediary between clients and an SFU (Selective Forwarding Unit) mediasoup server.

## Architecture

```
┌─────────────┐    HTTP/WS     ┌─────────────────────┐
│   Client    │ ◄─────────────► │ Frappe Server      │
│ (Frontend)  │                │ (Auth, Perms etc)   │
│             │                └─────────────────────┘
│             │
│             │    Socket.IO (JWT Auth)
│             │ ◄──────────────────────────────────┐
└─────────────┘                                    │
                                                   ▼
                                            ┌─────────────┐
                                            │ SFU Server  │
                                            │ (mediasoup) │
                                            └─────────────┘
```

### Components

1. **Client (Frontend)**: Vue.js application with WebRTC capabilities and direct SFU communication
2. **Frappe Server**: Handles authentication, permissions, and meeting management
3. **SFU Server**: Dedicated mediasoup server for WebRTC media routing with JWT authentication

### Prerequisites

- Frappe Framework (v15+)
- Node.js (v16+)
- Python 3.10+
- mediasoup SFU server dependencies

### 1. Install the Frappe App

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app sae
```

### 2. Setup SFU Server

```bash
# Navigate to SFU server directory
cd apps/sae/sfu-server

# Install dependencies (including new JWT support)
npm install

# Configure environment
cp .env.example .env
# Edit .env with your settings:
# JWT_SECRET=your_jwt_secret_here
# PORT=3000
# HOST=localhost

# Start SFU server
npm start
```

### 3. Configure Frappe Site

Add to your site config:

```python
# JWT secret for SFU authentication (must match SFU .env)
sfu_secret = "your_jwt_secret_here"
sfu_server_url = "http://localhost"
sfu_server_port = 3000
```

### 4. Install Python Dependencies

```bash
# Install Python dependencies
bench pip install python-socketio python-engineio PyJWT
```

### 5. Build Frontend

```bash
# Build frontend with new SFU client
cd apps/sae/frontend
yarn install
yarn build
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/sae
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.

### License

AGPL-3.0
