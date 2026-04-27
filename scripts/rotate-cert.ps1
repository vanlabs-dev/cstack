<#
.SYNOPSIS
    Rotate the cstack signalguard certificate on an existing app registration.

.DESCRIPTION
    Generates a new self-signed certificate in CurrentUser\My, uploads the
    public key to the existing app registration as an additional credential,
    and prints the new thumbprint. The previous certificate is left in place
    so the operator can verify the new one before removing the old.

.PARAMETER TenantId
    The Microsoft Entra tenant id (UUID).

.PARAMETER ClientId
    The application (client) id of the cstack app registration.

.PARAMETER CertSubject
    Subject for the new cert. Defaults to CN=cstack-signalguard.

.PARAMETER OldThumbprint
    Optional. If provided, the script will look up the existing cert by
    thumbprint and verify it before issuing the new one. The old cert is
    not removed automatically.

.EXAMPLE
    PS> .\rotate-cert.ps1 -TenantId <id> -ClientId <client>

.NOTES
    Prerequisites:
      - Microsoft.Graph PowerShell module
      - Caller must hold Application.ReadWrite.All in the target tenant.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $TenantId,

    [Parameter(Mandatory = $true)]
    [string] $ClientId,

    [string] $CertSubject = 'CN=cstack-signalguard',

    [string] $OldThumbprint
)

$ErrorActionPreference = 'Stop'

function Write-Status {
    param([string] $Message)
    Write-Host "[cstack] $Message"
}

if ($OldThumbprint) {
    $existing = Get-Item -Path "Cert:\CurrentUser\My\$OldThumbprint" -ErrorAction SilentlyContinue
    if (-not $existing) {
        Write-Status "warning: existing cert with thumbprint $OldThumbprint not found in CurrentUser\My"
    } else {
        Write-Status "existing cert located: $($existing.Subject) expires $($existing.NotAfter.ToString('yyyy-MM-dd'))"
    }
}

Connect-MgGraph -TenantId $TenantId -Scopes 'Application.ReadWrite.All' | Out-Null

$app = Get-MgApplication -Filter "appId eq '$ClientId'"
if (-not $app) {
    throw "no app registration with appId '$ClientId' in tenant $TenantId"
}

$certEndDate = (Get-Date).AddYears(2)
Write-Status "creating new self-signed cert valid until $($certEndDate.ToString('yyyy-MM-dd'))"
$cert = New-SelfSignedCertificate `
    -Subject $CertSubject `
    -CertStoreLocation 'Cert:\CurrentUser\My' `
    -KeyExportPolicy Exportable `
    -KeyAlgorithm RSA `
    -KeyLength 2048 `
    -HashAlgorithm SHA256 `
    -NotAfter $certEndDate `
    -KeyUsage DigitalSignature, KeyEncipherment

# Append (not replace) the new cert to existing key credentials so the old
# one keeps working until the operator removes it explicitly.
$existingKeyCredentials = $app.KeyCredentials
$newCredential = @{
    Type        = 'AsymmetricX509Cert'
    Usage       = 'Verify'
    Key         = $cert.GetRawCertData()
    DisplayName = $CertSubject
    EndDateTime = $certEndDate
}
$updatedCredentials = @($existingKeyCredentials) + $newCredential

Update-MgApplication -ApplicationId $app.Id -KeyCredentials $updatedCredentials | Out-Null

Write-Host ''
Write-Host '----- cstack rotated cert -----'
Write-Host "tenant_id          : $TenantId"
Write-Host "client_id          : $ClientId"
Write-Host "new_cert_thumbprint: $($cert.Thumbprint.ToUpper())"
Write-Host "new_cert_subject   : $CertSubject"
Write-Host "expires            : $($certEndDate.ToString('o'))"
if ($OldThumbprint) {
    Write-Host "old_cert_thumbprint: $OldThumbprint (still active; remove from cert store and app once verified)"
}
Write-Host '-------------------------------'
