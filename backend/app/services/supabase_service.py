from supabase import ClientOptions, create_client

from app.config.settings import settings


settings.validate_backend_config()

client_options = ClientOptions(
    postgrest_client_timeout=settings.SUPABASE_POSTGREST_TIMEOUT_SECONDS,
    function_client_timeout=settings.SUPABASE_POSTGREST_TIMEOUT_SECONDS
)

supabase = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_ROLE_KEY,
    options=client_options
)

auth_supabase = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_ANON_KEY,
    options=client_options
)
