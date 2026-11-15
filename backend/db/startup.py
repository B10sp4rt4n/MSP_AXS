"""Local schema bootstrap; PostgreSQL schemas are provisioned by migrations."""


def bootstrap_local_schema(base, engine):
    if engine.dialect.name != "sqlite":
        return False
    base.metadata.create_all(bind=engine)
    return True
