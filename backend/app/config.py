from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_key: str = ""
    # Hybrid LLM configuration (floor-plan parse_architecture_prompt uses OpenAI
    # structured JSON + maket_deliverable only; Ollama is not wired there yet.)
    use_local_llm: bool = False  # USE_LOCAL_LLM
    ollama_url: str = "http://localhost:11434"  # OLLAMA_URL
    ollama_model: str = "phi3"  # OLLAMA_MODEL
    openai_model: str = "gpt-4o-mini"  # OPENAI_MODEL
    openai_api_key: str = "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"  # OPENAI_API_KEY

    class Config:
        env_file = ".env"


settings = Settings()
