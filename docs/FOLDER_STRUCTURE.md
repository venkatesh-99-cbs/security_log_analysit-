# Folder Structure

## Root Directories
- `backend/`: FastAPI application source code.
- `frontend/`: React + Vite application source code.
- `docs/`: System documentation.
- `tests/`: Unit and integration tests.
- `deployment/`: Deployment configurations (K8s, etc.).
- `scripts/`: Utility scripts for maintenance and setup.
- `knowledge_base/`: Raw documents for RAG ingestion.
- `uploads/`: Temporary storage for uploaded log files.
- `reports/`: Generated incident and executive reports.
- `datasets/`: Sample datasets for testing and development.
- `docker/`: Dockerfiles for various components.

## Backend Structure (`backend/app/`)
- `api/`: FastAPI route definitions.
- `core/`: Global settings, constants, and logging.
- `database/`: DB session management and migrations.
- `models/`: SQLAlchemy database models.
- `schemas/`: Pydantic models for data validation.
- `services/`: Business logic layer.
- `repositories/`: Data access layer.
- `parsers/`: Log parsing logic for different formats (Windows, Linux, etc.).
- `detection/`: Threat detection engines.
- `correlation/`: Incident correlation and threat scoring.
- `rag/`: Retrieval-Augmented Generation services and vector store.
- `ai/`: Ollama client and AI analysis logic.
- `reports/`: Report generation logic.
- `mcp/`: Model Context Protocol integration for local tools.
- `background/`: Background task processing (parsers, detectors).
- `utils/`: Helper functions and common utilities.

## Frontend Structure (`frontend/src/`)
- `pages/`: Main application views.
- `components/`: Reusable UI components.
- `layouts/`: Page layout wrappers.
- `hooks/`: Custom React hooks for state and data fetching.
- `services/`: API client services.
- `types/`: TypeScript interface definitions.
- `store/`: Global state management (Zustand/Context).
- `utils/`: UI-related utility functions.
