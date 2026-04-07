# Extrai NOTION_DATABASE_ID a partir do URL da base Notion (ou de 32 hex).
# Uso:  .\scripts\notion-id-from-url.ps1 "https://www.notion.so/..."
#       .\scripts\notion-id-from-url.ps1 "a1b2c3d4e5f6478990abcdef12345678"

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$UrlOrId
)

function ConvertTo-NotionUuid([string]$thirtyTwoHex) {
    $h = $thirtyTwoHex.ToLower()
    if ($h.Length -ne 32) { throw "Esperados 32 caracteres hex; obtidos $($h.Length)." }
    return ($h.Substring(0, 8) + '-' + $h.Substring(8, 4) + '-' + $h.Substring(12, 4) + '-' + $h.Substring(16, 4) + '-' + $h.Substring(20, 12))
}

$uuidRegex = '[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}'
$m = [regex]::Match($UrlOrId, $uuidRegex)
if ($m.Success) {
    $id = $m.Value.ToLower()
}
else {
    $m2 = [regex]::Match($UrlOrId, '[a-fA-F0-9]{32}')
    if (-not $m2.Success) {
        Write-Error "Nao encontrei UUID nem 32 hex. Cola o URL completo da base (pagina full page) ou os 32 caracteres."
        exit 1
    }
    $id = ConvertTo-NotionUuid $m2.Value
}

Write-Host "NOTION_DATABASE_ID=$id"
Write-Host ""
Write-Host "Copia o valor (depois do =) para a variavel n8n NOTION_DATABASE_ID."
