
# MT ACCESS

MT ACCESS is a remote application access management system designed to manage and provide controlled access to Windows applications such as MetaTrader 4 (MT4) and MetaTrader 5 (MT5).

The project consists of a backend API, a React frontend, a Windows Agent, and an Apache Guacamole remote access gateway.

## Project Structure

```text
mt-access/
│
├── backend/
│   ├── .env
│   ├── .env.example
│   └── ...
│
├── frontend/
│   ├── .env
│   ├── .env.example
│   └── ...
│
├── guacamole/
│   ├── .env
│   ├── .env.example
│   └── ...
│
├── .gitignore
└── README.md
```

## Technologies Used

- Backend: Python, FastAPI
- Frontend: React, Vite
- Database: MySQL
- Remote Access: Apache Guacamole
- Remote Desktop Protocol: RDP
- Containerization: Docker

## Environment Configuration

MT ACCESS uses three separate environment files.

Each component has:
- `.env` – Actual local configuration containing secrets and environment-specific values.
- `.env.example` – Template containing the required environment variables.

Actual `.env` files must never be committed to GitHub.

### 1. Backend Environment

Location:

`backend/.env`

Create your local environment file by copying the example:

```powershell
Copy-Item backend/.env.example backend/.env
```

The backend environment contains:

| Variable | Purpose |
|---|---|
| ENVIRONMENT | Application environment (development/production) |
| DATABASE_URL | MySQL database connection |
| SECRET_KEY | Application security and token signing |
| ACCESS_TOKEN_EXPIRE_MINUTES | Authentication token expiry |
| ALLOWED_APP_ROOTS | Permitted Windows application directories |
| CORS_ORIGINS | Allowed frontend origins |
| AGENT_SECRET | Authentication secret for the Windows Agent |
| INITIAL_ADMIN_EMAIL | Initial administrator email |
| INITIAL_ADMIN_PASSWORD | Initial administrator password |
| GUAC_JSON_SECRET_KEY | Guacamole JSON authentication secret |
| RDP_CREDENTIAL_ENCRYPTION_KEY | Encryption key for stored RDP credentials |
| RDP_ALLOWED_REMOTE_APP_ALIASES | Permitted RemoteApp aliases |
| GUAC_TOKEN_TTL_SECONDS | Guacamole token lifetime |

Generate secure keys using Python.

**SECRET_KEY:**

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**AGENT_SECRET:**

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**GUAC_JSON_SECRET_KEY:**

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

**RDP_CREDENTIAL_ENCRYPTION_KEY:**

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 2. Frontend Environment

Location:

`frontend/.env`

Create your local environment file:

```powershell
Copy-Item frontend/.env.example frontend/.env
```

Environment variables:

| Variable | Purpose |
|---|---|
| VITE_API_BASE_URL | Backend API address |
| VITE_GUACAMOLE_URL | Guacamole gateway address accessed through the Vite proxy |

Default development configuration:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_GUACAMOLE_URL=http://localhost:5173/guacamole
```

Restart the Vite development server after changing frontend environment variables.

### 3. Guacamole Environment

Location:

`guacamole/.env`

Create your local environment file:

```powershell
Copy-Item guacamole/.env.example guacamole/.env
```

Environment variables:

| Variable | Purpose |
|---|---|
| JSON_SECRET_KEY | Secret used for Guacamole JSON authentication |
| GUACD_LOG_LEVEL | Logging level for the guacd service |

**Important:**

The following values must match:

- `backend/.env` → `GUAC_JSON_SECRET_KEY`
- `guacamole/.env` → `JSON_SECRET_KEY`

Both must contain exactly the same secret.

Do not generate two different values for these variables.

## Git and Environment File Security

The root `.gitignore` excludes actual environment files from Git tracking.

The following files must remain private:

```text
backend/.env
frontend/.env
guacamole/.env
```

The following example files should be committed to Git:

```text
backend/.env.example
frontend/.env.example
guacamole/.env.example
```

This allows other developers to understand the required configuration without receiving sensitive credentials.

### Verify Git Ignore Configuration

Run these commands from the project root:

```powershell
git check-ignore backend/.env
git check-ignore frontend/.env
git check-ignore guacamole/.env
```

All three actual environment files should be ignored.

Check that example files are not ignored:

```powershell
git check-ignore backend/.env.example
git check-ignore frontend/.env.example
git check-ignore guacamole/.env.example
```

These commands should produce no output.

**Note:** If an actual `.env` file was committed previously, `.gitignore` does not automatically remove it from Git tracking. It must be untracked separately, and any exposed credentials should be rotated.

## Initial Setup for Developers

### Step 1: Clone the Repository

```powershell
git clone <repository-url>
cd mt-access
```

### Step 2: Create Environment Files

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
Copy-Item guacamole/.env.example guacamole/.env
```

### Step 3: Configure Backend

Update `backend/.env` with:

- MySQL database details.
- Secure application secrets.
- Agent authentication secret.
- Guacamole authentication secret.
- RDP encryption key.
- Initial administrator credentials.

### Step 4: Configure Frontend

Check the API and Guacamole URLs in `frontend/.env`.

### Step 5: Configure Guacamole

Update `guacamole/.env`.

Ensure its `JSON_SECRET_KEY` matches the backend's `GUAC_JSON_SECRET_KEY`.

### Step 6: Start the Project

Follow the individual backend, frontend, Windows Agent, and Guacamole setup instructions in their respective folders.

## Security Guidelines

1. Never commit actual `.env` files.
2. Never share application secrets or passwords through GitHub.
3. Use unique and randomly generated secrets.
4. Do not use development credentials in production.
5. Keep the RDP credential encryption key secure.
6. Rotate credentials if they are exposed.
7. Configure HTTPS before production deployment.
8. Restrict database and remote access gateway exposure.
9. Do not store production passwords in `.env.example`.

## Important Notes

- `.env.example` files are templates, not production configurations.
- Every developer must create their own local `.env` files.
- Environment variables must match the requirements of the respective application components.
- Keep the example files updated whenever new required environment variables are introduced.

## Project Development

MT ACCESS is developed in phases covering:

1. Backend Foundation
2. Application Assignment
3. Windows Agent
4. Remote Access Integration
5. React Frontend
6. Security and Testing
7. Deployment

Refer to the project documentation and phase-specific instructions for implementation and deployment details.
