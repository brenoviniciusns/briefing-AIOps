import os
from functools import lru_cache


@lru_cache
def get_adls_connection_string() -> str:
    direct = os.environ.get("ADLS_CONNECTION_STRING", "").strip()
    if direct:
        return direct
    return os.environ.get("AzureWebJobsStorage", "").strip()


@lru_cache
def storage_account_name() -> str:
    return os.environ.get("STORAGE_ACCOUNT_NAME", "").strip()


@lru_cache
def storage_account_key() -> str:
    return os.environ.get("STORAGE_ACCOUNT_KEY", "").strip()


@lru_cache
def container_raw() -> str:
    return os.environ.get("ADLS_CONTAINER_RAW", "raw").strip()


@lru_cache
def container_processed() -> str:
    return os.environ.get("ADLS_CONTAINER_PROCESSED", "processed").strip()


@lru_cache
def container_reports() -> str:
    return os.environ.get("ADLS_CONTAINER_REPORTS", "reports").strip()


@lru_cache
def delta_table_relative_path() -> str:
    return os.environ.get("DELTA_TABLE_PATH", "articles").strip().strip("/")


@lru_cache
def openai_api_key() -> str:
    return os.environ.get("OPENAI_API_KEY", "").strip()


@lru_cache
def openai_endpoint() -> str:
    return os.environ.get("OPENAI_ENDPOINT", "").strip().rstrip("/")


@lru_cache
def openai_deployment() -> str:
    return os.environ.get("OPENAI_DEPLOYMENT_NAME", "gpt-4o").strip()


def max_articles_per_run() -> int:
    """Limite de artigos por execução de /process.

    Cada artigo dispara chamadas ao Azure OpenAI (resumo). O pedido HTTP síncrono
    passa pelo proxy do App Service, que corta por volta de **230 s** (504 Gateway
    Timeout) — independentemente de host.json (ex.: 10 min) ou do timeout do cliente.
    Ajusta MAX_ARTICLES_PER_RUN nas App Settings (ex.: 25–40) conforme latência do modelo.
    Para lotes maiores, usar padrão assíncrono (fila / Durable Functions).
    """
    try:
        return max(1, int(os.environ.get("MAX_ARTICLES_PER_RUN", "35")))
    except ValueError:
        return 35


def use_managed_identity_data_plane() -> bool:
    return os.environ.get("USE_MANAGED_IDENTITY_DATA_PLANE", "").lower() in ("1", "true", "yes")


def delta_storage_options() -> dict:
    """Opções para deltalake: account_key ou token Azure AD / MI (sem account_key nas settings)."""
    name = storage_account_name()
    if not name:
        raise RuntimeError("STORAGE_ACCOUNT_NAME é obrigatório para Delta/ABFSS.")
    key = storage_account_key()
    if key:
        return {
            "account_name": name,
            "account_key": key,
        }
    from azure.identity import DefaultAzureCredential

    cred = DefaultAzureCredential()
    token = cred.get_token("https://storage.azure.com/.default")
    return {
        "azure_storage_account_name": name,
        "azure_storage_token": token.token,
    }


def delta_table_uri() -> str:
    name = storage_account_name()
    container = container_processed()
    rel = delta_table_relative_path()
    return f"abfss://{container}@{name}.dfs.core.windows.net/{rel}"
