"""Fixed, backend-only sandbox ACL contract. No credentials or remote execution."""
ROLES = {
    "CORE": "axs_corp_sandbox_core",
    "GOV": "axs_corp_sandbox_gov",
    "EVENT": "axs_corp_sandbox_event",
    "PROVISIONER": "axs_corporate_provisioner",
}
DATABASES = {"CORE": "axs_corp_core_sbx", "GOV": "axs_corp_gov_sbx", "EVENT": "axs_corp_event_sbx"}
ACK = "corporate_sandbox_attestation"
DELIVERY = ("delivered_at", "attempts", "next_attempt_at", "last_error")
# Table privileges and column privileges are intentionally distinct.
TABLE_GRANTS = {
    "CORE": {
        "usuarios": ("SELECT",), "msps_exo": ("SELECT",),
        "condominios_exo": ("SELECT",), "corporate_organizations": ("SELECT",),
        "corporate_memberships": ("SELECT",), "corporate_site_assignments": ("SELECT",),
        "msp_memberships": ("SELECT",), "user_tenant_scope": ("SELECT",),
        "provider_contracts": ("SELECT",),
        **{t: ("SELECT", "INSERT", "UPDATE") for t in ("corporate_sites", "corporate_destinations", "arco_cases")},
        "event_outbox": ("SELECT", "INSERT"), "security_outbox": ("SELECT", "INSERT"), ACK: ("SELECT",),
    },
    "GOV": {"authorities_gov": ("SELECT",), "policies_gov": ("SELECT", "INSERT"), ACK: ("SELECT",)},
    "EVENT": {"events_aup": ("SELECT", "INSERT"), ACK: ("SELECT",)},
    "PROVISIONER": {"condominios_exo": ("SELECT",), "corporate_organizations": ("SELECT", "INSERT"),
        "corporate_memberships": ("SELECT", "INSERT"), "event_outbox": ("INSERT",),
        "corporate_provisioning_operations": ("SELECT", "INSERT"), ACK: ("SELECT",)},
}
COLUMN_GRANTS = {
    "CORE": {"event_outbox": {"UPDATE": DELIVERY}, "security_outbox": {"UPDATE": DELIVERY}},
    "GOV": {"policies_gov": {"UPDATE": ("limites", "metadata_json", "estado", "valida_desde", "valida_hasta")}},
    "EVENT": {},
    "PROVISIONER": {
        "condominios_exo": {"INSERT": ("condominio_id", "msp_id", "nombre", "modalidad", "corporativo_habilitado"), "UPDATE": ("corporativo_habilitado",)},
        "corporate_provisioning_operations": {"UPDATE": ("estado", "confirmed_at", "confirmation_event_uid")},
    },
}
SEQUENCES = {"CORE": (), "GOV": (), "EVENT": ("events_aup",), "PROVISIONER": ("condominios_exo",)}
