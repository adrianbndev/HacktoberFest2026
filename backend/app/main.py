"""Entrypoint FastAPI: monta bajo /api todos los routers de app/routers."""
import importlib
import pkgutil

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import routers

app = FastAPI(title="LifeOS & ReCommerce AI")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Cada Track añade su archivo en app/routers/ exportando `router`; no hace falta tocar este archivo
# (así nadie compite por editarlo en paralelo).
for module in pkgutil.iter_modules(routers.__path__):
    router = importlib.import_module(f"{routers.__name__}.{module.name}").router
    app.include_router(router, prefix="" if router.prefix.startswith("/api") else "/api")
