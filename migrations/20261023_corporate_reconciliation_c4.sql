-- PROPOSAL ONLY: explicit owner review/approval before any remote application.
-- Requires C0/C1/C2. Validated only with synthetic disposable PostgreSQL.
-- Never executed from startup/deploy. No LOGIN, credentials or broad outbox access.
BEGIN;
CREATE TABLE public.corporate_provisioning_operations (
 tenant_id varchar NOT NULL REFERENCES public.corporate_organizations(tenant_id),
 request_id varchar(36) NOT NULL,
 revision integer NOT NULL CHECK (revision > 0),
 payload json NOT NULL,
 payload_hash varchar(64) NOT NULL,
 requested_by varchar NOT NULL,
 expected_gov json NOT NULL,
 estado varchar(16) NOT NULL DEFAULT 'pending',
 request_event_uid varchar NOT NULL,
 confirmation_event_uid varchar,
 created_at timestamp NOT NULL,
 confirmed_at timestamp,
 PRIMARY KEY (tenant_id,request_id),
 CONSTRAINT uq_corporate_operation_revision UNIQUE (tenant_id,revision),
 CONSTRAINT ck_corporate_operation_state CHECK (estado IN ('pending','confirmed','needs_review')),
 CONSTRAINT ck_corporate_operation_confirmation CHECK (
  (estado IN ('pending','needs_review') AND confirmed_at IS NULL AND confirmation_event_uid IS NULL) OR
  (estado='confirmed' AND confirmed_at IS NOT NULL AND confirmation_event_uid IS NOT NULL))
);
CREATE UNIQUE INDEX uq_corporate_operation_pending
 ON public.corporate_provisioning_operations(tenant_id) WHERE estado IN ('pending','needs_review');
ALTER TABLE public.corporate_provisioning_operations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.corporate_provisioning_operations FORCE ROW LEVEL SECURITY;
-- Fail closed on every pre-existing table/index/policy: this proposal runs once.
-- A completed or uncertain prior application must be inspected, never replayed blindly.
CREATE POLICY corporate_operation_tenant ON public.corporate_provisioning_operations
 TO axs_corporate_provisioner
 USING (tenant_id=current_setting('app.tenant_id',true))
 WITH CHECK (tenant_id=current_setting('app.tenant_id',true));
-- Reject owner default ACLs that would expose the fresh journal to another role.
DO $$ BEGIN
 IF EXISTS (
  SELECT 1 FROM pg_class c, LATERAL aclexplode(coalesce(c.relacl,acldefault('r',c.relowner))) acl
  WHERE c.oid='public.corporate_provisioning_operations'::regclass
   AND acl.grantee <> c.relowner
 ) THEN RAISE EXCEPTION 'Unexpected inherited/default privileges on corporate operation journal'; END IF;
END $$;
-- These new persistent privileges require separate approval before remote use.
GRANT SELECT, INSERT ON public.corporate_provisioning_operations TO axs_corporate_provisioner;
GRANT UPDATE (estado,confirmed_at,confirmation_event_uid)
 ON public.corporate_provisioning_operations TO axs_corporate_provisioner;
-- No DELETE, payload/identity UPDATE, outbox SELECT, role membership or axs_core_app change.
COMMIT;
