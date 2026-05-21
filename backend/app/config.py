from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_key: str = ""
    # Hybrid LLM configuration (floor-plan parse_architecture_prompt uses OpenAI
    # structured JSON + maket_deliverable only; Ollama is not wired there yet.)
    use_local_llm: bool = False  # USE_LOCAL_LLM
    ollama_url: str = "http://localhost:11434"  # OLLAMA_URL
    ollama_model: str = "phi3"  # OLLAMA_MODEL
    openai_model: str = "gpt-4o-mini"  # OPENAI_MODEL
    openai_api_key: str = ""  # OPENAI_API_KEY — set in Railway / .env, never commit

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
