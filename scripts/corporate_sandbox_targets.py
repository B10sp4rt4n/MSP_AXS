"""Reviewed sandbox destinations. No arbitrary database, role or endpoint overrides."""
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SandboxTargets:
    databases: dict
    roles: dict


LEGACY = SandboxTargets(
    {d: f"axs_corp_{d.lower()}_sbx" for d in ("CORE", "GOV", "EVENT")},
    {"CORE": "axs_corp_sandbox_core", "GOV": "axs_corp_sandbox_gov",
     "EVENT": "axs_corp_sandbox_event", "PROVISIONER": "axs_corporate_provisioner"},
)
INTEGRATED = SandboxTargets(
    {d: name + "_20261114" for d, name in LEGACY.databases.items()},
    {d: name + "_20261114" for d, name in LEGACY.roles.items()},
)


def sandbox_targets(values):
    profile = values.get("AXS_CORPORATE_SANDBOX_RUN_PROFILE", "legacy")
    if profile == "legacy":
        return LEGACY
    if profile == "integrated-20261114":
        return INTEGRATED
    raise RuntimeError("Sandbox: perfil de ensayo no aprobado")


def render_sandbox_sql(sql, targets):
    """Render only fixed, reviewed identifiers in trusted migration sources."""
    replacements = {**dict(zip(LEGACY.databases.values(), targets.databases.values())),
                    **dict(zip(LEGACY.roles.values(), targets.roles.values()))}
    pattern = r"\b(?:" + "|".join(map(re.escape, sorted(replacements, key=len, reverse=True))) + r")\b"
    return re.sub(pattern, lambda match: replacements[match.group()], sql)
