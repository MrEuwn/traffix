"""Central API router registry for Traffix backend."""

from fastapi import APIRouter

from app.routes.bottlenecks import router as bottlenecks_router
from app.routes.cameras import router as cameras_router
from app.routes.intersections import router as intersections_router
from app.routes.model_eval import router as model_eval_router
from app.routes.predictions import router as predictions_router
from app.routes.recommendations import router as recommendations_router
from app.routes.segments import router as segments_router
from app.routes.signals import router as signals_router
from app.routes.simulation import router as simulation_router
from app.routes.system import v1_router as system_router
from app.routes.weather import router as weather_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(system_router)
api_router.include_router(intersections_router)
api_router.include_router(predictions_router)
api_router.include_router(simulation_router)
api_router.include_router(recommendations_router)
api_router.include_router(weather_router)
api_router.include_router(cameras_router)

# v4 analytics routers (docs/SCHEMA-v4.md §3.1).
api_router.include_router(bottlenecks_router)
api_router.include_router(segments_router)
api_router.include_router(signals_router)
api_router.include_router(model_eval_router)
