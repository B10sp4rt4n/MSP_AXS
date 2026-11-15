"""Read-only activation gate for manually migrated corporate visits."""
from sqlalchemy import inspect, text


def check_schema(conn, role="axs_core_app"):
    if conn.dialect.name != "postgresql":
        raise RuntimeError("Corporate visits require PostgreSQL")
    table = "corporate_visits"
    actual = conn.execute(text("""SELECT relrowsecurity,relforcerowsecurity FROM pg_class
        WHERE oid=to_regclass('public.corporate_visits')""")).one_or_none()
    if actual != (True, True):
        raise RuntimeError("Corporate visits: migration or FORCE RLS missing")
    schema = inspect(conn)
    if set(schema.get_pk_constraint(table)["constrained_columns"]) != {"tenant_id", "visit_id"}:
        raise RuntimeError("Corporate visits: wrong primary key")
    fks = {tuple(fk["constrained_columns"]): (fk["referred_table"], tuple(fk["referred_columns"]))
           for fk in schema.get_foreign_keys(table)}
    if fks != {("tenant_id", "site_id", "destination_id"):
               ("corporate_destinations", ("tenant_id", "site_id", "destination_id")),
               ("tenant_id", "host_user_id"): ("corporate_memberships", ("tenant_id", "user_id"))}:
        raise RuntimeError("Corporate visits: scope foreign keys missing")
    perms = conn.execute(text("""SELECT has_table_privilege(current_user,'public.corporate_visits','SELECT'),
        has_table_privilege(current_user,'public.corporate_visits','INSERT'),
        has_table_privilege(current_user,'public.corporate_visits','DELETE') OR
        has_table_privilege(current_user,'public.corporate_visits','TRUNCATE')""")).one()
    if perms != (True, True, False) or conn.exec_driver_sql("SELECT current_user").scalar_one() != role:
        raise RuntimeError("Corporate visits: runtime permission mismatch")
    columns = conn.execute(text("""SELECT column_name FROM information_schema.columns
        WHERE table_schema='public' AND table_name='corporate_visits'
        AND has_column_privilege(current_user,'public.corporate_visits',column_name,'UPDATE')""")).scalars()
    if set(columns) != {"state", "authorized_by", "authorized_at", "entered_at", "exited_at", "cancelled_at"}:
        raise RuntimeError("Corporate visits: unexpected mutable columns")
    policies = conn.execute(text("SELECT cmd,roles,qual,with_check FROM pg_policies WHERE schemaname='public' AND tablename=:t"), {"t": table}).all()
    normalize = lambda s: "".join((s or "").replace("::text", "").split()).replace("(", "").replace(")", "")
    expected = normalize("tenant_id=current_setting('app.tenant_id',true)")
    if len(policies) != 1 or policies[0][0] != "ALL" or list(policies[0][1]) != [role] or any(normalize(s) != expected for s in policies[0][2:]):
        raise RuntimeError("Corporate visits: unexpected RLS policy")
    return {"gate": "PASS", "table": table}
