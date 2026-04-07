"""
Deployment ao nível do resource group via ARM REST (contorno a falhas do Azure CLI ao ler a resposta).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
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


def _get_token(az: list[str]) -> str:
    return subprocess.check_output(
        az + ["account", "get-access-token", "--query", "accessToken", "-o", "tsv"],
        text=True,
    ).strip()


def main() -> int:
    if len(sys.argv) < 6:
        print(
            "Uso: python deploy-resource-group-arm.py <subscription_id> <resource_group> "
            "<deployment_name> <template.json> <parameters.json>",
            file=sys.stderr,
        )
        return 2
    sub = sys.argv[1]
    rg = sys.argv[2]
    dep_name = sys.argv[3]
    template_path = sys.argv[4]
    params_path = sys.argv[5]

    az = _az_cli()
    token = _get_token(az)
    if not token:
        print("Sem token Azure CLI.", file=sys.stderr)
        return 1

    with open(template_path, encoding="utf-8") as f:
        template = json.load(f)
    with open(params_path, encoding="utf-8") as f:
        params_file = json.load(f)
    params = params_file.get("parameters") or {}

    body = {
        "properties": {
            "mode": "Incremental",
            "template": template,
            "parameters": params,
        }
    }

    url = (
        f"https://management.azure.com/subscriptions/{sub}"
        f"/resourcegroups/{rg}/providers/Microsoft.Resources/deployments/{dep_name}"
        f"?api-version=2021-04-01"
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
        with urllib.request.urlopen(req, timeout=300) as resp:
            print(resp.read().decode("utf-8", errors="replace")[:4000])
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}: {err}", file=sys.stderr)
        return 1

    # Polling do estado (GET não costuma disparar o bug do CLI)
    status_url = url
    for _ in range(120):
        time.sleep(15)
        get_req = urllib.request.Request(
            status_url,
            method="GET",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(get_req, timeout=60) as resp:
                doc = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            print(f"Poll HTTP {e.code}", file=sys.stderr)
            continue
        state = doc.get("properties", {}).get("provisioningState")
        err = doc.get("properties", {}).get("error")
        print(f"provisioningState={state}", file=sys.stderr)
        if err:
            print(json.dumps(err, indent=2), file=sys.stderr)
        if state in ("Succeeded", "Failed", "Canceled"):
            return 0 if state == "Succeeded" else 1
    print("Timeout a aguardar deployment.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
