from fastapi import APIRouter

from app.api.routes import forecast, health, overpass, tram_graph

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(forecast.router)
api_router.include_router(tram_graph.router)
api_router.include_router(overpass.router)
