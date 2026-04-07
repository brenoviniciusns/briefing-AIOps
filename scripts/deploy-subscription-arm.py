"""
Submete um deployment à escala da subscrição via ARM REST (contorno a bugs do `az deployment sub` em alguns ambientes).
Requisitos: Azure CLI autenticado (`az login`), ficheiros main.json e parameters JSON gerados.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request


def _az_cli() -> list[str]:
    exe = shutil.which("az")
    if exe:
        return [exe]
    prog = os.environ.get("PROGRAMFILES", "C:\\Program Files")
    win = os.path.join(prog, "Microsoft SDKs", "Azure", "CLI2", "wbin", "az.cmd")
    if os.path.isfile(win):
        return [win]
    return ["az"]


def main() -> int:
    if len(sys.argv) < 5:
        print(
            "Uso: python deploy-subscription-arm.py <subscription_id> <deployment_name> <main.json> <parameters.json> [location]",
            file=sys.stderr,
        )
        return 2
    sub = sys.argv[1]
    dep_name = sys.argv[2]
    template_path = sys.argv[3]
    params_path = sys.argv[4]
    location = sys.argv[5] if len(sys.argv) > 5 else "eastus2"

    az = _az_cli()
    token = subprocess.check_output(
        az + ["account", "get-access-token", "--query", "accessToken", "-o", "tsv"],
        text=True,
        shell=False,
    ).strip()
    if not token:
        print("Sem token Azure CLI.", file=sys.stderr)
        return 1

    with open(template_path, encoding="utf-8") as f:
        template = json.load(f)
    with open(params_path, encoding="utf-8") as f:
        params_file = json.load(f)
    params = params_file.get("parameters") or {}

    body = {
        "location": location,
        "properties": {
            "mode": "Incremental",
            "template": template,
            "parameters": params,
        },
    }

    url = (
        f"https://management.azure.com/subscriptions/{sub}"
        f"/providers/Microsoft.Resources/deployments/{dep_name}?api-version=2021-04-01"
    )
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="PUT",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            out = resp.read().decode("utf-8", errors="replace")
            print(out[:8000])
            if len(out) > 8000:
                print("\n... (truncado)")
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}: {err}", file=sys.stderr)
        return 1
    print(
        "\nAcompanhar: az deployment sub show --name "
        f"{dep_name} --query properties.provisioningState -o tsv",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
