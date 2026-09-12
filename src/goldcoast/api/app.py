from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from goldcoast.api.deps import RunRegistry
from goldcoast.api.routes import decisions, events, media, runs, seed
from goldcoast.data import load_seed
from goldcoast.pipeline.run_store import RunStore
from goldcoast.settings import Settings, get_settings


class ApplicationCORS:
    def __init__(self, app):
        self.app = app
        self.cors = None

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        if self.cors is None:
            self.cors = CORSMiddleware(
                self.app,
                allow_origins=scope["app"].state.settings.api_cors_origins,
                allow_methods=["GET", "POST"],
                allow_headers=["Content-Type", "Last-Event-ID", "Range"],
                expose_headers=["Accept-Ranges", "Content-Range"],
            )
        await self.cors(scope, receive, send)


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        configuration = settings or get_settings()
        app.state.settings = configuration
        app.state.seed = load_seed(configuration.data_dir)
        app.state.store = RunStore(configuration.output_dir)
        app.state.registry = RunRegistry(app.state.store)
        try:
            yield
        finally:
            await app.state.registry.close()

    app = FastAPI(title="Goldcoast", lifespan=lifespan)
    app.add_middleware(ApplicationCORS)
    for router in (runs.router, events.router, decisions.router, media.router, seed.router):
        app.include_router(router)
    return app


app = create_app()
