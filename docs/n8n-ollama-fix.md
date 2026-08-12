# Ollama and n8n connectivity notes

- n8n should use `http://local-rag-ollama:11434` for direct Ollama access.
- `http://aisha:11434`, `::1:11434`, `127.0.0.1:11434`, and the Tailscale IP are not reliable inside the n8n container.
- Use the `ollama-connectivity-test.workflow.json` export to validate the private Docker-network path.
