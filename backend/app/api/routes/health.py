from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(request: Request):
    settings = request.app.state.settings
    database = getattr(request.app.state, "database", None)
    database_status = "not_initialized"
    database_reason = "not_initialized"
    if database is not None:
        if database.ping():
            database_status = "ok"
            database_reason = None
        else:
            database_status = "unavailable"
            database_reason = getattr(database, "failure_reason", None) or "connection_failed"

    firebase_auth = getattr(request.app.state, "firebase_auth", None)
    auth_status = "not_initialized"
    auth_reason = "not_initialized"
    auth_missing: list[str] = []
    if firebase_auth is not None:
        if not firebase_auth.configured:
            auth_status = "unconfigured"
            auth_reason = "missing_configuration"
            auth_missing = list(getattr(firebase_auth, "missing_configuration", []))
        else:
            if getattr(firebase_auth, "app", None) is not None:
                auth_status = "ok"
                auth_reason = None
            else:
                auth_status = "unavailable"
                auth_reason = getattr(firebase_auth, "failure_reason", None) or "initialization_failed"

    database_health = {
        "status": database_status,
        "name": settings.mongodb_database,
    }
    if database_reason:
        database_health["reason"] = database_reason
        if database is not None:
            database_health["configuration_state"] = getattr(database, "uri_state", "unknown")
    if database_reason == "missing_configuration" and database is not None:
        database_health["missing"] = list(getattr(database, "missing_configuration", []))

    auth_health = {"status": auth_status}
    if auth_reason:
        auth_health["reason"] = auth_reason
    if auth_missing:
        auth_health["missing"] = auth_missing

    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.version,
        "environment": settings.app_environment,
        "database": database_health,
        "ai": {
            "provider": "groq",
            "configured": bool(settings.groq_api_key),
            "model": settings.groq_model,
        },
        "auth": auth_health,
    }
