import importlib
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from fastapi.testclient import TestClient

os.environ["CHROMA_PATH"] = str(Path("C:/Users/ZBook/Documents/Aisha/.test-chroma"))

import app.main as app_main

app_main = importlib.reload(app_main)
app = app_main.app

client = TestClient(app)


def test_platform_endpoint_exposes_ai_surfaces() -> None:
    response = client.get("/platform")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert "ai_platform" in body
    assert "ai_services" in body
    assert "ai_services_compose" in body
    assert "rag_api" in body
    assert "ingestion" in body
    assert "local_rag" in body
    assert "integrations" in body
    assert "n8n" in body
    assert "mcp" in body
    assert "skills" in body
    assert body["rag_api"]["service"] == "RAG API"
    assert body["ingestion"]["service"] == "ingestion and indexing"
    assert body["ai_services"]["deployment_order"][0] == "local LLM service"


def test_platform_status_endpoint_is_compact() -> None:
    response = client.get("/platform/status")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["sections"] == ["ai_platform", "ai_services", "rag_api", "ingestion", "local_rag", "integrations"]
    assert body["ai_platform"] == "available"
    assert body["ai_services"] == "available"
    assert body["rag_api"] == "available"
    assert body["ingestion"] == "available"
    assert body["local_rag"] == "available"
    assert body["integrations"] == ["n8n", "MCP", "Skills"]
    assert "discoverable from the app layer" in body["notes"][2]


def test_platform_summary_endpoint_is_minimal() -> None:
    response = client.get("/platform/summary")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["ready"] is True
    assert body["sections"] == ["ai_platform", "ai_services", "rag_api", "ingestion", "local_rag", "integrations"]
    assert body["ai_services"] == ["local LLM service", "embedding service", "vector database", "RAG API"]
    assert "platform endpoints" in body["notes"][0]


def test_platform_integrations_endpoint_exposes_registry() -> None:
    response = client.get("/platform/integrations")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["integrations"]["entries"][0]["name"] == "n8n"
    assert body["integrations"]["entries"][1]["name"] == "MCP"
    assert body["integrations"]["entries"][2]["name"] == "Skills"
    assert body["n8n"]["service"] == "n8n"
    assert body["mcp"]["service"] == "MCP gateway"
    assert body["skills"]["service"] == "Skills registry"


def test_platform_services_endpoint_exposes_ai_service_plan() -> None:
    response = client.get("/platform/services")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["deployment_order"] == ["local LLM service", "embedding service", "vector database", "RAG API"]
    assert body["compose_name"] == "aisha-ai-services"
    assert body["compose_services"] == ["local LLM service", "embedding service", "vector database", "RAG API"]
    assert body["services"][0]["name"] == "local LLM service"
    assert body["services"][2]["depends_on"] == ["embedding service"]


def test_platform_infrastructure_endpoint_exposes_phase_two_manifest() -> None:
    response = client.get("/platform/infrastructure")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["manifest"] == "infrastructure"
    assert body["schema_path"] == "bootstrap/infrastructure.schema.json"
    assert body["phase_names"] == ["storage", "networking", "monitoring", "backups", "exposure"]
    assert body["service_order"] == ["reverse-proxy", "storage", "monitoring", "backups"]
    assert body["volumes"] == ["prometheus-data", "backup-data"]
    assert body["networks"] == ["edge", "internal"]


def test_platform_storage_network_endpoint_exposes_phase_two_layout() -> None:
    response = client.get("/platform/storage-network")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["storage"]["root"] == "/srv/data/services"
    assert body["storage"]["volumes"] == ["prometheus-data", "backup-data"]
    assert body["storage"]["volume_paths"]["prometheus-data"] == "/srv/data/services/prometheus-data"
    assert body["networking"]["networks"] == ["edge", "internal"]
    assert body["networking"]["reverse_proxy_network"] == "edge"
    assert body["networking"]["boundaries"]["public"] == ["edge"]
    assert body["networking"]["boundaries"]["private"] == ["internal"]


def test_platform_monitoring_endpoint_exposes_operational_targets() -> None:
    response = client.get("/platform/monitoring")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["service"] == "monitoring"
    assert body["metric_targets"][0] == "cpu"
    assert "service availability" in body["dashboard_expectations"]
    assert body["alerting_targets"] == ["containers", "healthchecks", "backups"]
    assert body["log_sources"] == ["reverse-proxy", "monitoring", "backups"]
    assert body["hooks"]["scrape"] == ["metrics", "health", "logs"]


def test_platform_backups_endpoint_exposes_restore_policy() -> None:
    response = client.get("/platform/backups")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["service"] == "backups"
    assert body["volume_names"] == ["prometheus-data", "backup-data"]
    assert body["schedule"] == "daily"
    assert "weekly" in body["retention_policy"]
    assert "verification volume" in body["restore_check"]
    assert body["hooks"]["schedule"] == "daily snapshot rotation"
    assert body["targets"][0]["path"] == "/srv/data/services/prometheus-data"


def test_platform_exposure_endpoint_exposes_boundary_policy() -> None:
    response = client.get("/platform/exposure")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["service"] == "reverse-proxy"
    assert body["public_entrypoint"] == "edge"
    assert body["tls_terminator"] == "traefik"
    assert body["exposed_services"] == ["reverse-proxy"]
    assert "monitoring" in body["internal_services"]
    assert body["access_policy"]["public"] == ["reverse-proxy"]
    assert "internal networks" in body["boundary_notes"]


def test_platform_dns_tls_endpoint_exposes_certificate_strategy() -> None:
    response = client.get("/platform/dns-tls")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["service"] == "reverse-proxy"
    assert "split-horizon" in body["dns_strategy"]
    assert "automatic TLS termination" in body["tls_strategy"]
    assert "ACME-compatible" in body["certificate_source"]
    assert body["domain_boundaries"] == ["public", "private"]
    assert "renew certificates" in body["renewal_notes"]


def test_platform_rag_api_endpoint_exposes_retrieval_flow() -> None:
    response = client.get("/platform/rag-api")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["service"] == "RAG API"
    assert body["steps"][0]["name"] == "retrieve"
    assert body["steps"][2]["depends_on"] == ["rerank", "local LLM service"]
    assert body["inputs"] == ["user question", "indexed vectors", "document metadata"]
    assert body["outputs"][0] == "grounded answer"
    assert "external access is explicitly approved" in body["boundary_notes"]


def test_platform_ingestion_endpoint_exposes_indexing_flow() -> None:
    response = client.get("/platform/ingestion")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["service"] == "ingestion and indexing"
    assert body["steps"][0]["name"] == "discover"
    assert body["steps"][3]["depends_on"] == ["chunk", "embedding service"]
    assert body["steps"][4]["name"] == "index"
    assert body["retry_notes"].startswith("retry parse")
    assert "private vector store" in body["boundary_notes"]


def test_platform_local_rag_endpoint_exposes_runtime_layers() -> None:
    response = client.get("/platform/local-rag")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["components"][0] == "document parser"
    assert body["capabilities"][3] == "vector search"
    assert body["data_flow"][4] == "retrieve candidates"
    assert body["storage_plan"]["location"] == "/srv/data/services/vector-database"
    assert body["ingestion"]["service"] == "ingestion and indexing"
    assert body["roadmap_items"][0] == "hybrid search"
    assert "private and reproducible" in body["deployment_notes"]


def test_platform_skills_endpoint_exposes_registry_entries() -> None:
    response = client.get("/platform/skills")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["service"] == "Skills registry"
    assert body["skills"][0]["name"] == "bootstrap-validation"
    assert body["skills"][1]["name"] == "integration-review"
    assert body["skills"][2]["name"] == "release-prep"
    assert body["skills"][3]["name"] == "operator-checklist"
    assert "repository-backed manifests" in body["discovery_notes"]


def test_platform_agent_platform_endpoint_exposes_planners_and_memory() -> None:
    response = client.get("/platform/agent-platform")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["planners"] == ["task planner", "workflow planner", "policy planner"]
    assert body["routers"] == ["tool router", "model router", "skill router"]
    assert body["execution_layers"][0] == "local execution"
    assert body["memory_layers"] == ["short-term memory", "project memory", "operational memory"]
    assert body["memory"]["memory_types"][0] == "conversation"


def test_platform_memory_endpoint_exposes_long_term_state_model() -> None:
    response = client.get("/platform/memory")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["memory_types"] == ["conversation", "preferences", "projects", "tasks", "documents"]
    assert "repository-backed summaries" in body["storage"]
    assert "revision history" in body["retention_notes"]
    assert "indexed search first" in body["retrieval_notes"]


def test_platform_workflow_engine_endpoint_exposes_execution_stages() -> None:
    response = client.get("/platform/workflow-engine")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["stages"] == ["plan", "route", "execute", "verify", "report"]
    assert body["orchestration_modes"] == ["manual approval", "semi-automated", "fully automated"]
    assert body["task_boundaries"][2] == "approval-gated changes"
    assert "verify outputs" in body["execution_notes"]


def test_platform_task_execution_endpoint_exposes_handoff_rules() -> None:
    response = client.get("/platform/task-execution")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["task_states"] == ["queued", "planned", "running", "verified", "completed"]
    assert body["handoff_rules"][1] == "request approval before external side effects"
    assert body["verification_steps"][-1] == "confirm memory updates"
    assert "durable records" in body["notes"]


def test_platform_autonomous_ops_endpoint_exposes_safety_boundaries() -> None:
    response = client.get("/platform/autonomous-ops")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["diagnostics"][0] == "container health"
    assert "backup verification" in body["diagnostics"]
    assert body["self_healing"][1] == "repair broken compose stacks"
    assert body["maintenance_recommendations"][0] == "upgrade dependencies"
    assert body["optimization_targets"] == ["latency", "uptime", "storage efficiency", "resource usage"]
    assert "approval-gated" in body["approval_notes"]


def test_platform_repair_guide_endpoint_exposes_recovery_rules() -> None:
    response = client.get("/platform/repair-guide")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["issue_classes"][0] == "unhealthy containers"
    assert body["recommended_actions"][2] == "renew certificates"
    assert body["escalation_rules"][1] == "request approval before destructive recovery"
    assert body["verification_checks"][-1] == "validate search responses"


def test_platform_maintenance_endpoint_exposes_recurring_checks() -> None:
    response = client.get("/platform/maintenance")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["tasks"][0] == "rotate backups"
    assert body["cadence"] == ["daily", "weekly", "monthly"]
    assert body["checks"][2] == "certificate freshness"
    assert "reviewable" in body["notes"]


def test_platform_self_healing_endpoint_exposes_incident_flow() -> None:
    response = client.get("/platform/self-healing")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["triggers"][0] == "unhealthy container"
    assert body["phases"] == ["detect", "assess", "repair", "verify", "escalate"]
    assert body["repair_actions"][2] == "restore the latest good snapshot"
    assert body["verification_steps"][-1] == "confirm search quality recovers"
    assert body["escalation_rules"][2] == "request approval for destructive restoration"


def test_platform_diagnostics_endpoint_exposes_baselines() -> None:
    response = client.get("/platform/diagnostics")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["checks"][0] == "container health"
    assert body["signals"][1] == "log anomalies"
    assert body["baselines"][-1] == "search responses remain grounded"
    assert "run diagnostics before repair" in body["notes"]


def test_platform_operations_summary_endpoint_exposes_phase_five_checkpoint() -> None:
    response = client.get("/platform/operations-summary")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["diagnostics"]["checks"][0] == "container health"
    assert body["repair_guide"]["issue_classes"][1] == "failed backups"
    assert body["maintenance"]["tasks"][0] == "rotate backups"
    assert body["self_healing"]["phases"] == ["detect", "assess", "repair", "verify", "escalate"]
    assert "approval-gated" in body["summary_notes"]


def test_platform_personal_os_endpoint_exposes_unified_surface() -> None:
    response = client.get("/platform/personal-os")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["interface_layers"][0] == "unified web interface"
    assert body["assistant_modes"] == ["development assistant", "research assistant", "infrastructure assistant", "personal productivity"]
    assert body["memory_layers"]["memory"]["memory_types"][0] == "conversation"
    assert body["operations_layers"]["operations"]["maintenance"]["tasks"][0] == "rotate backups"
    assert body["integration_layers"]["skills"]["service"] == "Skills registry"
    assert "single personal operating surface" in body["roadmap_notes"]


def test_platform_web_interface_endpoint_exposes_dashboard_surface() -> None:
    response = client.get("/platform/web-interface")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["pages"] == ["home", "assistant", "operations", "memory", "integrations", "integration webhooks", "settings"]
    assert body["dashboard_sections"][0] == "status"
    assert body["entrypoints"][1] == "quick actions"
    assert body["entrypoints"][-1] == "integration webhook setup"
    assert "conversational at the top" in body["navigation_notes"]
    assert body["personal_os"]["assistant_modes"][0] == "development assistant"


def test_platform_conversational_management_endpoint_exposes_command_model() -> None:
    response = client.get("/platform/conversational-management")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["intents"] == ["status lookup", "task creation", "system summary", "maintenance reminder", "repair request"]
    assert body["managed_domains"][0] == "AI platform"
    assert body["response_modes"][2] == "clarifying question"
    assert body["escalation_rules"][1] == "escalate when a request is ambiguous"
    assert "provenance" in body["notes"]


def test_platform_persistent_memory_endpoint_exposes_durable_state() -> None:
    response = client.get("/platform/persistent-memory")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["storage_layers"][0] == "repository-backed summaries"
    assert body["persistence_rules"][1] == "version every meaningful update"
    assert body["retention_policy"][-1] == "prune stale or duplicate summaries"
    assert "restore durable memory" in body["restore_notes"]


def test_platform_knowledge_graph_endpoint_exposes_relationship_model() -> None:
    response = client.get("/platform/knowledge-graph")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["entities"][0] == "people"
    assert body["relationships"] == ["depends on", "references", "belongs to", "summarizes", "triggers"]
    assert body["provenance_rules"][1] == "prefer repository-backed facts"
    assert "preserving provenance" in body["traversal_notes"]


def test_platform_home_automation_endpoint_exposes_household_controls() -> None:
    response = client.get("/platform/home-automation")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["target_systems"][0] == "Home Assistant"
    assert body["control_surfaces"][-1] == "manual override"
    assert body["sensor_sources"][1] == "environmental sensors"
    assert body["safety_rules"][0] == "keep external actions approval-gated"
    assert "observable first" in body["notes"]


def test_platform_productivity_endpoint_exposes_planning_loop() -> None:
    response = client.get("/platform/productivity")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["goals"][0] == "daily priorities"
    assert body["planning_loops"] == ["capture", "prioritize", "schedule", "execute", "review"]
    assert body["focus_modes"][2] == "low-friction task capture"
    assert body["task_flow"][-1] == "review completed work"
    assert "minimal overhead" in body["notes"]


def test_platform_assistant_modes_endpoint_exposes_specialized_modes() -> None:
    response = client.get("/platform/assistant-modes")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["modes"] == ["development assistant", "research assistant", "infrastructure assistant", "personal productivity"]
    assert body["responsibilities"][0] == "code and test work"
    assert body["guardrails"][1] == "ask before risky changes"
    assert "sharing memory" in body["notes"]


def test_platform_external_integrations_endpoint_exposes_outside_world_controls() -> None:
    response = client.get("/platform/external-integrations")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["systems"] == ["GitHub Actions", "browser automation", "Slack", "Discord", "Telegram", "calendar"]
    assert body["use_cases"][0] == "code review and CI"
    assert body["control_modes"][1] == "approval-gated writes"
    assert body["safety_rules"][2] == "log every external side effect"
    assert body["webhook_targets"][0]["name"] == "Slack"
    assert body["webhook_targets"][1]["env_var"] == "DISCORD_WEBHOOK_URL"
    assert body["webhook_targets"][2]["example_export"] == "scripts/telegram_alerts_n8n_export.json"
    assert body["setup_flow"][0] == "choose the target platform"
    assert "outside world" in body["notes"]


def test_platform_integration_webhooks_page_renders_html() -> None:
    response = client.get("/platform/integration-webhooks")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    body = response.text

    assert "Integration Webhooks" in body
    assert "Slack" in body
    assert "Discord" in body
    assert "Telegram" in body
    assert "mission_control_webhook_dispatcher.py" in body


def test_platform_web_dashboard_endpoint_renders_html() -> None:
    response = client.get("/platform/web-dashboard")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    body = response.text

    assert "Aisha Personal OS" in body
    assert "unified web interface" in body
    assert "development assistant" in body
    assert "Mission Control" in body
    assert "Open Mission Control" in body
    assert body.count("Open Mission Control") == 1
    assert "/platform/mission-control" in body
    assert "/platform/assets/aisha-launcher.css" in body
    assert "/platform/assets/aisha-launcher.js" in body
    assert "Dashboard sections" in body
    assert "/platform/integration-webhooks" in body
    assert "Integration Webhooks" in body
    assert "/openclaw/" in body
    assert "OpenClaw Control UI" in body



def test_platform_openclaw_control_ui_redirects_to_stock_ui() -> None:
    response = client.get("/openclaw/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "http://testserver:18789/openclaw/"


def test_platform_aisha_launcher_assets_are_served() -> None:
    script_response = client.get("/platform/assets/aisha-launcher.js")
    style_response = client.get("/platform/assets/aisha-launcher.css")

    assert script_response.status_code == 200
    assert "application/javascript" in script_response.headers["content-type"]
    assert "Chat with Aisha" in script_response.text
    assert "GATEWAY_PORT = '18790'" in script_response.text
    assert "isPlatformDashboard = window.location.pathname.startsWith('/platform/');" in script_response.text
    assert style_response.status_code == 200
    assert "text/css" in style_response.headers["content-type"]
    assert "#aisha-launcher" in style_response.text


def test_platform_aisha_proxy_forwards_to_openclaw(monkeypatch) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path != "/aisha/api/health":
                self.send_response(404)
                self.end_headers()
                return
            body = json.dumps({"status": "ok", "ready": True}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(app_main, "OPENCLAW_URL", f"http://127.0.0.1:{server.server_port}")
    try:
        response = client.get("/aisha/api/health")
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "ready": True}

def test_platform_mission_control_endpoint_renders_embedded_dashboard() -> None:
    response = client.get('/platform/mission-control')

    assert response.status_code == 200
    assert 'text/html' in response.headers['content-type']

    body = response.text

    assert 'Mission Control' in body
    assert '/mission-control/' in body
    assert '<iframe' in body
