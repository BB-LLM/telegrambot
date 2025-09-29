# Mem0 REST API Server

Mem0 provides a REST API server (written using FastAPI). Users can perform all operations through REST endpoints. The API also includes OpenAPI documentation, accessible at `/docs` when the server is running.

## Features

- **Create memories:** Create memories based on messages for a user, agent, or run.
- **Retrieve memories:** Get all memories for a given user, agent, or run.
- **Search memories:** Search stored memories based on a query.
- **Update memories:** Update an existing memory.
- **Delete memories:** Delete a specific memory or all memories for a user, agent, or run.
- **Reset memories:** Reset all memories for a user, agent, or run.
- **OpenAPI Documentation:** Accessible via `/docs` endpoint.

## Running the server
PYTHONPATH=./ python server/server.py --port 8080

## running the demo
PYTHONPATH=./ streamlit run server/app.py--server.fileWatcherType none --server.port 8081
【windows】streamlit run app.py --server.fileWatcherType none --server.port 8081

[mac] PYTHONPATH=./ streamlit run server/app.py --server.fileWatcherType none --server.port 8081


qdrant-key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.zyODVTAKCSNpo0cBBh6yXMlf29A8nJAaz42KTTZP2hk"