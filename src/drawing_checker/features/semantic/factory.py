"""Dựng SemanticService theo cấu hình. `MAIN_AI_PROVIDER=off` (mặc định) → None: pipeline chạy như không có AI."""

from drawing_checker.config import Settings
from drawing_checker.features.semantic.budget import UsageLedger
from drawing_checker.features.semantic.provider import CallStore, ClaudeProvider, ReplayProvider
from drawing_checker.features.semantic.service import SemanticService


def build_semantic(settings: Settings) -> SemanticService | None:
    if settings.ai_provider == "off":
        return None
    store = CallStore(settings.ai_dir / "calls")
    if settings.ai_provider == "replay":
        provider = ReplayProvider(store, settings.ai_model)
    else:
        ledger = UsageLedger(settings.ai_dir / "usage.jsonl", settings.ai_monthly_budget_usd)
        key = settings.anthropic_api_key.get_secret_value() if settings.anthropic_api_key else None
        provider = ClaudeProvider(settings.ai_model, settings.ai_effort, ledger, store, api_key=key)
    return SemanticService(provider, settings.ai_max_usd_per_run)
