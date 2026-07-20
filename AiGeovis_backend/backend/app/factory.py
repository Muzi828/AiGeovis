from __future__ import annotations

import json
import math

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def _apply_json_nan_patch() -> None:
    """Replace json.dumps so NaN / Infinity become null."""
    _orig_dumps = json.dumps

    def _safe_dumps(obj, **kw):
        def _sanitize(o):
            if isinstance(o, dict):
                return {k: _sanitize(v) for k, v in o.items()}
            if isinstance(o, (list, tuple)):
                return [_sanitize(v) for v in o]
            if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
                return None
            return o
        return _orig_dumps(_sanitize(obj), **kw)

    json.dumps = _safe_dumps  # type: ignore[assignment]


def create_app() -> FastAPI:
    _apply_json_nan_patch()

    app = FastAPI(
        title="AiGeovis",
        version="1.2.0",
        description=(
            "AiGeovis backend API for WoS data loading, C1/C3 address geo-parsing "
            "(multi-model, parallel), and geocoding. Country/organization lookups "
            "are matched against a read-only reference library first (incremental "
            "matching); only unmatched names are sent to the LLM, or all names when "
            "full parsing is requested."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from api import register_routers
    register_routers(app)
    return app
