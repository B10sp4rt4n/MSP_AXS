"""Offline operator CLI. Run only against an isolated restoration destination."""
import argparse
import json
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['quarantine', 'reconcile', 'release'])
    parser.add_argument('--incident', required=True)
    parser.add_argument('--actor', default='')
    parser.add_argument('--backup-cutoff', type=datetime.fromisoformat)
    parser.add_argument('--evidence-ref', default='')
    parser.add_argument('--occupancy-verified', action='store_true')
    parser.add_argument('--admin-id')
    parser.add_argument('--tenant-id')
    args = parser.parse_args()
    # Never load an implicit .env: operator supplies explicit destination connections.
    import os
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from backend.services.recovery_service import quarantine, reconcile, release, _incident
    from backend.db.core.models import RecoveryCheckpoint
    from backend.db.gov.models import RecoveryGovCheckpoint
    _incident(args.incident)
    names = ('DATABASE_CORE_URL', 'DATABASE_GOV_URL', 'DATABASE_EVENT_URL')
    if not all(os.getenv(name) for name in names):
        parser.error('All three destination database URLs must be explicit')
    if args.action == 'reconcile' and args.backup_cutoff is None:
        parser.error('--backup-cutoff with timezone required')
    engines = [create_engine(os.environ[name]) for name in names]
    try:
        RecoveryCheckpoint.__table__.create(engines[0], checkfirst=True)
        RecoveryGovCheckpoint.__table__.create(engines[1], checkfirst=True)
        with Session(engines[0]) as core, Session(engines[1]) as gov, Session(engines[2]) as event:
            if args.action == 'quarantine':
                result = quarantine(core, gov, args.incident, actor=args.actor)
            elif args.action == 'reconcile':
                result = reconcile(core, gov, event, args.incident, backup_cutoff=args.backup_cutoff)
            else:
                result = release(core, gov, event, args.incident, actor=args.actor,
                    evidence_ref=args.evidence_ref, occupancy_verified=args.occupancy_verified,
                    admin_id=args.admin_id, tenant_id=args.tenant_id)
            print(json.dumps(result, indent=2))
    finally:
        for engine in engines:
            engine.dispose()


if __name__ == '__main__':
    main()
