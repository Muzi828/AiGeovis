from __future__ import annotations

from fastapi import FastAPI


def register_routers(app: FastAPI) -> None:
    from api.health import router as health_router
    from api.models_api import router as models_router
    from api.data_api import router as data_router
    from api.parse_api import router as parse_router
    from api.results_api import router as results_router
    from api.geocode_api import router as geocode_router
    from api.matrix_api import router as matrix_router
    from api.demo_api import router as demo_router

    for r in (
        health_router,
        models_router,
        data_router,
        parse_router,
        results_router,
        geocode_router,
        matrix_router,
        demo_router,
    ):
        app.include_router(r)
