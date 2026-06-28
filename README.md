# Security Log Analysis Assistant

## Project Purpose
The Security Log Analysis Assistant is a production-quality, local-first platform designed for SOC (Security Operations Center) teams and Blue Teams. It enables offline analysis of security logs using local Small Language Models (SLMs) through Ollama, providing threat detection, incident correlation, and AI-powered recommendations without relying on cloud services.

## Architecture Overview
The system follows a clean architecture with a modular backend powered by FastAPI and a modern React frontend.
- **Backend:** Modular services for parsing, detection, correlation, RAG, and AI analysis.
- **Frontend:** SPA built with React, Vite, and Tailwind CSS.
- **AI/ML:** Uses local Ollama instance for LLM inference and ChromaDB for vector storage (RAG).
- **Data:** SQLite for relational data, ensuring zero-configuration local persistence.

## Technology Stack
- **Backend:** FastAPI, SQLAlchemy, SQLite, Pydantic
- **AI:** Ollama (Qwen3 8B), ChromaDB, LangChain
- **Frontend:** React, Vite, Tailwind CSS, TypeScript
- **Deployment:** Docker, Docker Compose

## How to Run
### Prerequisites
- Docker & Docker Compose
- Ollama (installed locally)

### Setup
1. Clone the repository.
2. Ensure Ollama is running and the `qwen3:8b` model is pulled: `ollama pull qwen3:8b`.
3. Run the application using Docker Compose:
   ```bash
   docker-compose up --build
   ```
4. Access the frontend at `http://localhost:5173`.

## Folder Structure
Refer to `docs/FOLDER_STRUCTURE.md` for a detailed breakdown of the project organization.
