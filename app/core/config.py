from pydantic import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # AI服务配置
    deepseek_api_key: str
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"

    # 数据库配置
    database_url: str

    # ChromaDB配置
    chroma_persist_dir: str
    #应用配置
    app_env: str = "development"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
    )