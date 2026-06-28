# Module Reference

## AI Module (`backend/app/ai/`)
- **OllamaClient**: Handles communication with the local Ollama API.
- **IncidentAnalyzer**: Orchestrates the analysis of correlated incidents using LLMs.
- **ThreatExplainer**: Provides human-readable explanations for security alerts.

## RAG Module (`backend/app/rag/`)
- **VectorStoreService**: Interfaces with ChromaDB for storing and retrieving embeddings.
- **EmbeddingService**: Generates vector embeddings for documents and queries.
- **KnowledgeIngestionService**: Processes documents into the vector store.

## Detection Module (`backend/app/detection/`)
- **BruteForceDetector**: Analyzes logs for pattern-based brute force attempts.
- **IOCDetector**: Matches log data against known Indicators of Compromise.

## Correlation Module (`backend/app/correlation/`)
- **CorrelationEngine**: Groups related logs and alerts into a single incident.
- **MITREMapper**: Automatically maps detected activities to the MITRE ATT&CK framework.

## MCP Module (`backend/app/mcp/`)
- **MCPClient**: Implements the Model Context Protocol to allow the AI to use local security tools like Sigma validators or WHOIS lookups.
