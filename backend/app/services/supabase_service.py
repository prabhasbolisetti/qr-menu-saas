from supabase import create_client

from app.config.settings import settings


settings.validate_backend_config()

supabase = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_ROLE_KEY
)

auth_supabase = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_ANON_KEY
)
