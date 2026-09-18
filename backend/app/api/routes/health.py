from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(request: Request):
    settings = request.app.state.settings
    database = getattr(request.app.state, "database", None)
    database_status = "not_initialized"
    if database is not None:
        database_status = "ok" if database.ping() else "unavailable"

    firebase_auth = getattr(request.app.state, "firebase_auth", None)
    auth_status = "not_initialized"
    if firebase_auth is not None:
        auth_status = "ok" if firebase_auth.configured else "unconfigured"

    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.version,
        "environment": settings.app_environment,
        "database": {
            "status": database_status,
            "name": settings.mongodb_database,
        },
        "ai": {
            "provider": "groq",
            "configured": bool(settings.groq_api_key),
            "model": settings.groq_model,
        },
        "auth": {
            "status": auth_status,
        },
    }
