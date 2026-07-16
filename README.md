# Security Log Analysis Assistant

Local-first SOC tooling for ingesting security logs, detecting suspicious behavior, correlating alerts into incidents, mapping activity to MITRE ATT&CK, and investigating results with a local AI Copilot.

The application runs as two local processes:

```text
React/Vite frontend :5173  ->  Flask API :8000  ->  SQLite + ChromaDB
                                              \-> Ollama (optional AI)
```

Docker is optional. The instructions below run the application directly on the host machine.

## What the application does

### Log ingestion

The Log Audit Ingestion page accepts uploaded files and processes them in the background. The parser automatically handles:

- Windows Event XML and exported `EventID=...` key/value logs
- JSON arrays, JSON objects, and NDJSON/JSONL
- RFC 5424, BSD, and plain Linux syslog
- CSV, TSV, pipe-delimited, firewall, proxy, and access-log exports
- Custom datasets with common aliases such as `src_ip`, `hostname`, `event_type`, `level`, and `message`

Every event is normalized into common fields such as timestamp, hostname, user, source IP, destination IP, event ID, event type, severity, process, command line, parent process, category, vendor, product, and raw log data. Detection logic operates on these normalized fields rather than on one vendor's syntax.

### Detection engine

The pipeline is:

```text
upload -> parse -> normalize -> save logs -> run detectors -> correlate alerts -> create incident
```

Current detection coverage includes:

- Repeated failed authentication / brute force using a sliding time window
- Port scanning and network discovery
- Privilege escalation behavior
- Lateral movement and remote-service activity
- Event-rate and high-severity density anomalies
- Privileged account login, Windows Event ID 4672
- Encoded PowerShell, Windows Event ID 4688
- Administrator/local-group modification, Windows Event ID 4732
- Malware detection, Windows Event ID 1116
- Blocked network connection, Windows Event ID 5157
- Account lockout, Windows Event ID 4740
- Security log clearing and suspicious PowerShell behavior

Externalized rules are stored in [backend/app/detection/rules.json](backend/app/detection/rules.json). Each rule includes an ID, name, type, MITRE technique, severity, confidence, and response guidance. The rule engine adds evidence, matched event count, source, and first/last seen timestamps to alerts.

The supplied Windows abnormal-activity sample is expected to produce detections for brute force, privileged login, encoded PowerShell, group modification, malware, blocked network traffic, and account lockout.

### Incident Response Queue

The queue displays correlated incidents grouped by the upload batch that produced them. Each incident card shows severity, status, description, source, threat score, MITRE mappings, timestamps, and investigation actions. The queue has a bounded desktop scroll region and responsive mobile layout so large batches remain usable.

### Parsed Audit Trail

The audit trail displays normalized log records in an expandable table. Filters support severity, category, source host/IP, and uploaded-file selection. Raw event details can be expanded per record. The audit panel remains stable while the records scroll inside the panel.

### Incident detail and reports

Incident detail provides status/severity controls, MITRE mappings, SOC timeline events, saved AI analyses, and evidence. Reports compile incident information into downloadable HTML summaries for handoff or review.

### AI Operations Copilot

The Copilot is a multi-turn chat interface backed by Ollama and optional ChromaDB retrieval:

- Local model inference through Ollama
- RAG grounding from the `Knowledge_base` directory
- Conversation history stored in SQLite
- Fast history/session switching
- Explicit response cancellation
- Background generation is not canceled by changing history tabs
- Correct local display of UTC timestamps
- Markdown, tables, code blocks, and copy actions in responses

Ollama is only required for Copilot responses and AI incident analysis. Log parsing, detection, correlation, incident storage, and the main queue work without it.

## Prerequisites

- Windows, macOS, or Linux
- Python 3.10 or newer
- Node.js 18 or newer and npm
- Git, if cloning the project
- Ollama, optional but required for AI features: <https://ollama.com>

## Run locally without Docker

Open two terminals from the repository root.

### 1. Create and activate a Python environment

Windows PowerShell:

```powershell
cd C:\path\to\security_log_analysit-
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run the environment executables directly or use Command Prompt:

```cmd
cd C:\path\to\security_log_analysit-
py -3 -m venv .venv
.venv\Scripts\activate.bat
```

macOS/Linux:

```bash
cd /path/to/security_log_analysit-
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install backend dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

### 3. Start the backend

```powershell
cd backend
python -m flask --app app.main run --host 127.0.0.1 --port 8000
```

The API is available at <http://127.0.0.1:8000> and uses `/api/v1` for application endpoints. The SQLite database, uploads, reports, and ChromaDB files are created under `backend/` according to the configured paths.

### 4. Install and start the frontend

In a second terminal:

```powershell
cd C:\path\to\security_log_analysit-\frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api` requests to `http://127.0.0.1:8000`.

### 5. Enable the AI Copilot (optional)

Install Ollama, then in a third terminal run:

```powershell
ollama serve
ollama pull qwen2.5:3b-instruct
ollama pull nomic-embed-text
```

If another model is preferred, set it before starting the backend:

```powershell
$env:OLLAMA_MODEL = "llama3.2:3b"
```

The backend automatically initializes the knowledge base on first RAG use. The initial load can take a little time.

## Test the supplied Windows sample manually

With the backend running, open the frontend, go to **Log Audit Ingestion**, and upload:

```text
C:\Users\VENKATESH\Downloads\windows_abnormal_activity.log
```

After processing, open **Incident Response Queue**. The sample contains 21 events and exercises the Windows detections listed above.

The parser and detector can also be exercised directly from the repository root without Docker:

```powershell
python -c "from app.parsers import parse_log_file; from app.detection import DetectionOrchestrator; p=parse_log_file(open(r'C:\Users\VENKATESH\Downloads\windows_abnormal_activity.log').read(),'windows_abnormal_activity.log'); a=DetectionOrchestrator().run_all([{**x,'id':i+1} for i,x in enumerate(p)]); print('parsed:',len(p)); print('alerts:',len(a)); print(sorted(set(x.get('rule_id') or x.get('type') for x in a)))"
```

Run that command from the `backend` directory while the virtual environment is active.

## Useful development commands

Frontend type-check/build:

```powershell
cd frontend
npx tsc --noEmit
npm run build
```

Backend syntax validation:

```powershell
python -m py_compile backend/app/main.py backend/app/background/pipeline.py backend/app/parsers/*.py backend/app/detection/*.py
```

Backend tests, when pytest is installed:

```powershell
python -m pytest -q backend/tests
```

## Configuration

The main backend settings are in [backend/app/core/settings.py](backend/app/core/settings.py). Environment variables include:

| Variable | Purpose | Default |
|---|---|---|
| `OLLAMA_BASE_URL` | Ollama API address | `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | Explicit Ollama model | automatic selection |
| `OLLAMA_MAX_CONTEXT` | Maximum AI context size | `16384` |
| `OLLAMA_MIN_CONTEXT` | Minimum AI context size | `4096` |
| `OLLAMA_AUTO_SELECT_MODEL` | Select a suitable installed model | `true` |
| `VITE_PROXY_TARGET` | Frontend API proxy target | `http://127.0.0.1:8000` |

Do not commit sensitive logs, uploaded files, SQLite databases, ChromaDB data, or Ollama credentials.

## Project structure

```text
backend/
  app/
    api/              Flask API routes
    background/       Upload processing pipeline
    correlation/      Alert grouping, scoring, MITRE mapping
    detection/        Built-in detectors and external rules.json
    parsers/          Format parsers and universal normalizer
    rag/              ChromaDB knowledge retrieval
    models/           SQLAlchemy database models
  security_assistant.db
  requirements.txt
frontend/
  src/pages/          Dashboard, logs, incidents, reports, Copilot
  src/components/     Cards, tables, badges, timeline, chat bubbles
  src/hooks/          API-backed state and chat streaming
Knowledge_base/       SOC playbooks, definitions, ATT&CK references
docs/                 Project and module documentation
```

## Troubleshooting

**Frontend cannot reach the API**

Confirm the backend is running on port 8000 and that the frontend is running on port 5173. If the backend uses another port, set `VITE_PROXY_TARGET` before `npm run dev`.

**PowerShell refuses `npm` or virtual-environment activation**

Use `npm.cmd` instead of `npm`, use Command Prompt, or invoke `.venv\Scripts\python.exe` directly.

**Copilot says Ollama is offline**

Run `ollama serve`, verify `ollama list`, and pull an installed model. The rest of the application remains usable without Ollama.

**No incidents appear after upload**

Check the file status in Ingested Datasets, wait for `processed`, reload the queue, and inspect backend console output. Detection only runs after parsing completes.

**RAG initialization is slow**

The first Copilot/RAG request indexes the knowledge base. Later requests reuse the local ChromaDB store.

## Security and privacy

The application is designed for local-first analysis. Logs remain in the local SQLite/upload storage, and AI prompts are sent to the configured local Ollama service. Review the data paths and local service exposure before using production or sensitive telemetry.

## Additional documentation

- [TEST_PROJECT_GUIDE.md](TEST_PROJECT_GUIDE.md)
- [docs/FOLDER_STRUCTURE.md](docs/FOLDER_STRUCTURE.md)
- [docs/MODULE_REFERENCE.md](docs/MODULE_REFERENCE.md)
- [docs/IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md)
