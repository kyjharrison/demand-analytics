from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass


BC_SCOPE = "https://api.businesscentral.dynamics.com/.default"


@dataclass(frozen=True)
class BCAuthConfig:
    tenant_id: str
    client_id: str
    environment: str
    company_name: str | None
    key_vault_name: str | None
    key_vault_secret_name: str | None
    key_vault_secret_version: str | None
    client_secret: str | None
    scope: str = BC_SCOPE


def env_first(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return None


def load_bc_auth_config() -> BCAuthConfig:
    tenant_id = env_first("BC_TENANT_ID", "AZURE_TENANT_ID")
    client_id = env_first("BC_CLIENT_ID", "AZURE_CLIENT_ID")
    environment = env_first("BC_ENVIRONMENT", "BC_ENV", "BC_API_ENVIRONMENT", "BC_SERVER_ENVIRONMENT")
    company_name = env_first("BC_COMPANY_NAME", "BC_COMPANY")
    client_secret = env_first("BC_CLIENT_SECRET", "AZURE_CLIENT_SECRET")
    key_vault_name = env_first("BC_KEYVAULT_NAME", "BC_KEY_VAULT_NAME", "AZURE_KEYVAULT_NAME")
    key_vault_secret_name = env_first("BC_CLIENT_SECRET_NAME", "BC_KEYVAULT_SECRET_NAME")
    key_vault_secret_version = env_first("BC_CLIENT_SECRET_VERSION", "BC_KEYVAULT_SECRET_VERSION")

    missing = []
    if not tenant_id:
        missing.append("BC_TENANT_ID")
    if not client_id:
        missing.append("BC_CLIENT_ID")
    if not environment:
        missing.append("BC_ENVIRONMENT")
    if missing:
        raise RuntimeError(
            "Missing required Business Central auth settings: " + ", ".join(missing)
        )

    if not client_secret and (not key_vault_name or not key_vault_secret_name):
        raise RuntimeError(
            "Set BC_CLIENT_SECRET directly. Azure Key Vault is optional and only used as a fallback when "
            "BC_KEYVAULT_NAME and BC_CLIENT_SECRET_NAME are also set."
        )

    return BCAuthConfig(
        tenant_id=tenant_id,
        client_id=client_id,
        environment=environment,
        company_name=company_name,
        key_vault_name=key_vault_name,
        key_vault_secret_name=key_vault_secret_name,
        key_vault_secret_version=key_vault_secret_version,
        client_secret=client_secret,
    )


def get_key_vault_secret(
    vault_name: str,
    secret_name: str,
    *,
    secret_version: str | None = None,
) -> str:
    command = [
        "az",
        "keyvault",
        "secret",
        "show",
        "--vault-name",
        vault_name,
        "--name",
        secret_name,
        "--query",
        "value",
        "-o",
        "tsv",
    ]
    if secret_version:
        command.extend(["--version", secret_version])

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "unknown Azure CLI error"
        raise RuntimeError(
            "Unable to read client secret from Key Vault via Azure CLI. "
            "Make sure the current Azure login has Key Vault secret read access. "
            f"Details: {stderr}"
        )

    secret_value = completed.stdout.strip()
    if not secret_value:
        raise RuntimeError(
            f"Key Vault secret '{secret_name}' in vault '{vault_name}' returned an empty value."
        )
    return secret_value


def resolve_bc_client_secret(config: BCAuthConfig) -> str:
    if config.client_secret:
        return config.client_secret
    if not config.key_vault_name or not config.key_vault_secret_name:
        raise RuntimeError("Business Central client secret configuration is incomplete.")
    return get_key_vault_secret(
        config.key_vault_name,
        config.key_vault_secret_name,
        secret_version=config.key_vault_secret_version,
    )


def get_secret_source(config: BCAuthConfig) -> str:
    if config.client_secret:
        return "environment-variable"
    return "azure-key-vault"


def acquire_bc_access_token(config: BCAuthConfig) -> str:
    client_secret = resolve_bc_client_secret(config)
    token_url = f"https://login.microsoftonline.com/{config.tenant_id}/oauth2/v2.0/token"
    body = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": config.client_id,
            "client_secret": client_secret,
            "scope": config.scope,
        }
    ).encode("utf-8")

    request = urllib.request.Request(token_url, data=body, method="POST")
    request.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_text = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Business Central token request failed: {exc.code} - {error_text}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Business Central token request failed: {exc.reason}") from exc

    access_token = payload.get("access_token")
    if not access_token:
        raise RuntimeError(f"Token response did not include an access_token: {payload}")
    return access_token.strip()


def build_bc_headers(access_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }


def raise_bc_api_error(exc: Exception, config: BCAuthConfig, url: str) -> None:
    if isinstance(exc, urllib.error.HTTPError):
        error_text = exc.read().decode("utf-8", errors="replace")
        if exc.code == 401:
            raise RuntimeError(
                "Business Central API returned 401 Unauthorized. "
                f"The app registration {config.client_id} can get a token, but Business Central still needs this app "
                "added under Microsoft Entra Applications with Access = API and the required permission sets."
            ) from exc
        raise RuntimeError(
            f"Business Central API call failed: {exc.code} - {error_text} (URL: {url})"
        ) from exc

    if isinstance(exc, urllib.error.URLError):
        raise RuntimeError(
            f"Business Central API call failed: {exc.reason} (URL: {url})"
        ) from exc

    raise exc


def build_bc_api_base_url(config: BCAuthConfig, api_path: str = "api/v2.0") -> str:
    return f"https://api.businesscentral.dynamics.com/v2.0/{config.tenant_id}/{config.environment}/{api_path}"


def build_bc_odata_base_url(config: BCAuthConfig) -> str:
    if not config.company_name:
        raise RuntimeError("BC_COMPANY_NAME is required to build an OData company URL.")
    company_segment = config.company_name.replace("'", "''")
    return (
        f"https://api.businesscentral.dynamics.com/v2.0/"
        f"{config.tenant_id}/{config.environment}/ODataV4/Company('{company_segment}')"
    )


def get_bc_connection() -> tuple[BCAuthConfig, dict[str, str]]:
    config = load_bc_auth_config()
    access_token = acquire_bc_access_token(config)
    return config, build_bc_headers(access_token)


if __name__ == "__main__":
    config, headers = get_bc_connection()
    print(
        json.dumps(
            {
                "tenant_id": config.tenant_id,
                "environment": config.environment,
                "company_name": config.company_name,
                "secret_source": get_secret_source(config),
                "key_vault_name": config.key_vault_name,
                "key_vault_secret_name": config.key_vault_secret_name,
                "authorization_header_present": "Authorization" in headers,
            },
            indent=2,
        )
    )
