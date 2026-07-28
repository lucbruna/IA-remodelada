"""
plugin_slack.py
===============
Integracao com Slack/Teams — notificacoes, comandos, bot interativo.

Suporta:
  - Slack (via Incoming Webhooks + Slack API)
  - Microsoft Teams (via Incoming Webhooks)
  - Discord (via Webhooks)

Requer: SLACK_WEBHOOK_URL e/ou TEAMS_WEBHOOK_URL e/ou DISCORD_WEBHOOK_URL no .env
"""

__version__ = "1.0.0"
PLUGIN_NAME = "Slack/Teams/Discord Bot"

import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL", "")
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
TEAMS_WEBHOOK = os.environ.get("TEAMS_WEBHOOK_URL", "")
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL", "")


def _send_slack(text: str, blocks: list = None, channel: str = "") -> bool:
    import requests
    if not SLACK_WEBHOOK:
        return False
    payload = {"text": text}
    if blocks:
        payload["blocks"] = blocks
    if channel:
        payload["channel"] = channel
    try:
        resp = requests.post(SLACK_WEBHOOK, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def _send_teams(text: str, title: str = "IA Remodelada") -> bool:
    import requests
    if not TEAMS_WEBHOOK:
        return False
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "0076D7",
        "summary": title,
        "sections": [{"activityTitle": title, "text": text, "markdown": True}],
    }
    try:
        resp = requests.post(TEAMS_WEBHOOK, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def _send_discord(text: str, username: str = "IA Remodelada") -> bool:
    import requests
    if not DISCORD_WEBHOOK:
        return False
    payload = {"content": text[:2000], "username": username}
    try:
        resp = requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
        return resp.status_code in (200, 204)
    except Exception:
        return False


def _send_all(text: str, title: str = "") -> dict:
    results = {}
    if SLACK_WEBHOOK:
        results["slack"] = _send_slack(text)
    if TEAMS_WEBHOOK:
        results["teams"] = _send_teams(text, title or "IA Remodelada")
    if DISCORD_WEBHOOK:
        results["discord"] = _send_discord(text)
    if not results:
        results["nenhum"] = False
    return results


def register(api):

    def notification_send(message: str, title: str = "", channels: str = "all") -> str:
        channels_list = [c.strip().lower() for c in channels.split(",")]
        results = {}

        if "all" in channels_list or "slack" in channels_list:
            results["Slack"] = _send_slack(f"*{title}*\n{message}" if title else message)
        if "all" in channels_list or "teams" in channels_list:
            results["Teams"] = _send_teams(message, title or "IA Remodelada")
        if "all" in channels_list or "discord" in channels_list:
            results["Discord"] = _send_discord(message)

        if not any(results.values()):
            return (
                "❌ Nenhum canal configurado.\n"
                "Configure no .env:\n"
                "  SLACK_WEBHOOK_URL=...\n"
                "  TEAMS_WEBHOOK_URL=...\n"
                "  DISCORD_WEBHOOK_URL=..."
            )

        status = "\n".join(
            f"  {'✅' if ok else '❌'} {name}" for name, ok in results.items()
        )
        return f"📤 Notificacao enviada:\n{status}"

    def notification_deploy(environment: str, version: str, status: str = "success", details: str = "") -> str:
        emoji = "✅" if status == "success" else "❌" if status == "failed" else "🔄"
        msg = (
            f"{emoji} **Deploy {status.upper()}**\n\n"
            f"• Ambiente: `{environment}`\n"
            f"• Versao: `{version}`\n"
            f"• Horario: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        if details:
            msg += f"\n• Detalhes: {details}"
        return notification_send(msg, f"Deploy {status}")

    def notification_alert(metric: str, value: str, threshold: str = "", severity: str = "warning") -> str:
        emoji = {"critical": "🔴", "warning": "🟡", "info": "🟢"}.get(severity, "⚪")
        msg = (
            f"{emoji} **ALERTA: {metric}**\n\n"
            f"• Valor atual: `{value}`\n"
        )
        if threshold:
            msg += f"• Limite: `{threshold}`\n"
        msg += f"• Horario: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return notification_send(msg, f"Alerta: {metric}")

    def notification_report(title: str, content: str, recipients: str = "") -> str:
        msg = f"📊 **{title}**\n\n{content}"
        return notification_send(msg, title)

    def notification_status() -> str:
        channels = []
        channels.append(f"  {'✅' if SLACK_WEBHOOK else '❌'} Slack Webhook")
        channels.append(f"  {'✅' if SLACK_TOKEN else '❌'} Slack Bot Token")
        channels.append(f"  {'✅' if TEAMS_WEBHOOK else '❌'} Teams Webhook")
        channels.append(f"  {'✅' if DISCORD_WEBHOOK else '❌'} Discord Webhook")
        configured = sum(1 for c in [SLACK_WEBHOOK, TEAMS_WEBHOOK, DISCORD_WEBHOOK] if c)
        return (
            f"📡 **Status das Integracoes** ({configured}/3 configuradas)\n\n"
            + "\n".join(channels)
        )

    def slack_send_message(channel: str, message: str) -> str:
        if not SLACK_WEBHOOK and not SLACK_TOKEN:
            return "❌ Slack nao configurado."
        ok = _send_slack(message, channel=channel)
        return f"✅ Mensagem enviada em #{channel}" if ok else "❌ Falha ao enviar."

    def slack_send_block(title: str, text: str, color: str = "#36a64f") -> str:
        if not SLACK_WEBHOOK:
            return "❌ Slack webhook nao configurado."
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": title, "emoji": True},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": text[:3000]},
            },
        ]
        ok = _send_slack("", blocks=blocks)
        return f"✅ Block enviado: {title}" if ok else "❌ Falha ao enviar."

    def teams_send_card(title: str, text: str, color: str = "0076D7") -> str:
        if not TEAMS_WEBHOOK:
            return "❌ Teams webhook nao configurado."
        import requests
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": color,
            "summary": title,
            "sections": [{"activityTitle": title, "text": text[:2000], "markdown": True}],
        }
        try:
            resp = requests.post(TEAMS_WEBHOOK, json=payload, timeout=10)
            return f"✅ Card enviado: {title}" if resp.status_code == 200 else "❌ Falha."
        except Exception as e:
            return f"❌ Erro: {e}"

    api.register_tool("notification_send", notification_send,
        "Envia notificacao para Slack, Teams e/ou Discord.",
        {"message": {"type": "string", "description": "Mensagem a enviar"},
         "title": {"type": "string", "description": "Titulo (opcional)"},
         "channels": {"type": "string", "description": "Canais: all, slack, teams, discord (separados por virgula)"}},
        ["message"])

    api.register_tool("notification_deploy", notification_deploy,
        "Notifica deploy concluido.",
        {"environment": {"type": "string", "description": "Producao, staging, dev"},
         "version": {"type": "string", "description": "Versao/commit"},
         "status": {"type": "string", "description": "success, failed, running"},
         "details": {"type": "string"}}, ["environment", "version"])

    api.register_tool("notification_alert", notification_alert,
        "Envia alerta de metrica.",
        {"metric": {"type": "string"}, "value": {"type": "string"},
         "threshold": {"type": "string"}, "severity": {"type": "string"}}, ["metric", "value"])

    api.register_tool("notification_report", notification_report,
        "Envia relatorio formatado.",
        {"title": {"type": "string"}, "content": {"type": "string"},
         "recipients": {"type": "string"}}, ["title", "content"])

    api.register_tool("notification_status", notification_status,
        "Status de todas as integracoes de notificacao.", {}, [])

    api.register_tool("slack_send_message", slack_send_message,
        "Envia mensagem para um canal Slack.",
        {"channel": {"type": "string", "description": "Nome do canal"},
         "message": {"type": "string"}}, ["channel", "message"])

    api.register_tool("slack_send_block", slack_send_block,
        "Envia bloco formatado para Slack.",
        {"title": {"type": "string"}, "text": {"type": "string"},
         "color": {"type": "string"}}, ["title", "text"])

    api.register_tool("teams_send_card", teams_send_card,
        "Envia card formatado para Teams.",
        {"title": {"type": "string"}, "text": {"type": "string"},
         "color": {"type": "string"}}, ["title", "text"])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Notificacoes e integracao com Slack, Microsoft Teams e Discord via webhooks.",
        "tools": ["notification_send", "notification_deploy", "notification_alert",
                   "notification_report", "notification_status",
                   "slack_send_message", "slack_send_block", "teams_send_card"],
    }
