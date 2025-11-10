from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.supabase_client import get_supabase_client
from app.services.gemini_client import init_gemini_client
from app.core.auth import SupabaseJWTMiddleware, require_user
from app.schemas import HealthResponse, AuthVerifyResponse
from app.routes.upload import router as upload_router
from app.routes.history import router as history_router
from app.routes.embed import router as embed_router
from app.routes.chat import router as chat_router
from app.routes.generate import router as generate_router
from app.routes.mindmap_data import router as mindmap_data_router
from app.routes.flashcards import router as flashcards_router
from app.routes.synthesis import router as synthesis_router
from app.routes.db import router as db_router

# Optional export router (requires WeasyPrint system dependencies)
try:
    from app.routes.export import router as export_router
    EXPORT_AVAILABLE = True
except (ImportError, OSError) as e:
    print(f"! Export functionality disabled: {e}")
    export_router = None
    EXPORT_AVAILABLE = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up Neura backend")
    try:
        supabase = get_supabase_client()
        print("✓ Supabase client initialized")
    except ValueError as e:
        print(f"! Supabase client not initialized: {e}")
    
    # Gemini client initialization for embedding generation (Sprint 2)
    try:
        init_gemini_client()
        print("✓ Gemini client initialized")
    except ValueError as e:
        print(f"⚠ Gemini API key not configured - embedding features will be unavailable")
    except Exception as e:
        print(f"! Failed to initialize Gemini client: {e}")
    
    try:
        yield
    finally:
        # Shutdown logic
        print("Shutting down Neura backend")
        # TODO: Close connections / cleanup resources


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Neura API", version="0.1.0", lifespan=lifespan)

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse)
    def health():
        return {"status": "healthy"}

    # JWT verification middleware (runs on all requests, allows public routes without token)
    app.add_middleware(SupabaseJWTMiddleware)

    @app.get("/auth/verify", response_model=AuthVerifyResponse)
    def auth_verify(user=Depends(require_user)):
        return {"sub": user["sub"], "role": user["role"], "message": "Token valid"}

    # Include routers
    app.include_router(upload_router)
    app.include_router(history_router)
    app.include_router(embed_router)
    app.include_router(chat_router)
    app.include_router(generate_router)
    app.include_router(mindmap_data_router)
    app.include_router(flashcards_router)
    app.include_router(synthesis_router)
    if EXPORT_AVAILABLE:
        app.include_router(export_router)
    app.include_router(db_router)
    # All core routers registered (upload, history, embed, chat, generate, flashcards, synthesis, export)

    return app


app = create_app()