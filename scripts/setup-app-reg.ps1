<#
.SYNOPSIS
    Provision a Microsoft Entra app registration for cstack signalguard.

.DESCRIPTION
    Creates a self-signed certificate in CurrentUser\My, registers an
    application in the target tenant with the Graph permissions cstack
    needs (read-only against policies, audit logs, directory, and roles),
    uploads the certificate public key, and grants admin consent.

    The script is intended to be run by an admin in the target tenant. It
    writes one structured output block at the end with the values the
    operator should paste into the cstack tenants.json registration.

.PARAMETER TenantId
    The Microsoft Entra tenant id (UUID) to provision in.

.PARAMETER AppName
    Display name of the app registration. Defaults to cstack-signalguard.

.PARAMETER CertSubject
    Subject line for the self-signed cert. Defaults to CN=cstack-signalguard.

.PARAMETER DryRun
    When set, the script prints the actions it would take without making
    any changes to the tenant or certificate store.

.EXAMPLE
    PS> .\setup-app-reg.ps1 -TenantId 00000000-0000-0000-0000-000000000000

.EXAMPLE
    PS> .\setup-app-reg.ps1 -TenantId <id> -AppName cstack-prod -DryRun

.NOTES
    Prerequisites:
      - PowerShell 7+ (Windows PowerShell 5.1 also works)
      - Microsoft.Graph PowerShell modules installed:
            Install-Module Microsoft.Graph -Scope CurrentUser
      - Caller must hold a role with Application.ReadWrite.All and
        DelegatedPermissionGrant.ReadWrite.All in the target tenant.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $TenantId,

    [string] $AppName = 'cstack-signalguard',

    [string] $CertSubject = 'CN=cstack-signalguard',

    [switch] $DryRun
)

$ErrorActionPreference = 'Stop'

# Permission ids and names. cstack only needs read access. Keep this list
# minimal so admin consent is easy to justify and audit.
$RequiredScopes = @(
    'Application.ReadWrite.All',
    'DelegatedPermissionGrant.ReadWrite.All'
)

# Graph permission ids (well-known, taken from the Microsoft Graph service
# principal). Listed by name + id so reviewers can verify each entry.
$GraphPermissions = @(
    @{ Name = 'Policy.Read.All';            Id = '246dd0d5-5bd0-4def-940b-0421030a5b68' }
    @{ Name = 'AuditLog.Read.All';          Id = 'b0afded3-3588-46d8-8b3d-9842eff778da' }
    @{ Name = 'Directory.Read.All';         Id = '7ab1d382-f21e-4acd-a863-ba3e13f7da61' }
    @{ Name = 'RoleManagement.Read.Directory'; Id = '483bed4a-2ad3-4361-a73b-c83ccdbdc53c' }
    @{ Name = 'Application.Read.All';       Id = '9a5d68dd-52b0-4cc2-bd40-abcf44ac3a30' }
)

function Write-Status {
    param([string] $Message)
    Write-Host "[cstack] $Message"
}

function Invoke-Action {
    param(
        [string] $Description,
        [scriptblock] $Action
    )
    if ($DryRun) {
        Write-Status "DRY RUN: would $Description"
        return $null
    }
    Write-Status $Description
    return & $Action
}

Write-Status "starting app registration for tenant $TenantId"
Write-Status "app name: $AppName"
Write-Status "cert subject: $CertSubject"
if ($DryRun) {
    Write-Status 'DRY RUN mode: no changes will be made.'
}

# Connect to Microsoft Graph with the required scopes. The interactive
# auth window opens here for the operator running the script.
Invoke-Action -Description 'connecting to Microsoft Graph' -Action {
    Connect-MgGraph -TenantId $TenantId -Scopes $RequiredScopes | Out-Null
} | Out-Null

# Self-signed certificate, 2-year validity, exportable so the rotate-cert
# script can replace it later. Lives in CurrentUser\My; the caller must
# run subsequent cstack operations as the same user.
$certEndDate = (Get-Date).AddYears(2)
$cert = Invoke-Action -Description "creating self-signed cert ($CertSubject) valid until $($certEndDate.ToString('yyyy-MM-dd'))" -Action {
    New-SelfSignedCertificate `
        -Subject $CertSubject `
        -CertStoreLocation 'Cert:\CurrentUser\My' `
        -KeyExportPolicy Exportable `
        -KeyAlgorithm RSA `
        -KeyLength 2048 `
        -HashAlgorithm SHA256 `
        -NotAfter $certEndDate `
        -KeyUsage DigitalSignature, KeyEncipherment
}

# Build the requiredResourceAccess block for Microsoft Graph.
$graphResourceId = '00000003-0000-0000-c000-000000000000'
$resourceAccess = $GraphPermissions | ForEach-Object {
    @{ Id = $_.Id; Type = 'Role' }
}

$requiredResourceAccess = @(
    @{ ResourceAppId = $graphResourceId; ResourceAccess = $resourceAccess }
)

$app = Invoke-Action -Description "creating app registration '$AppName'" -Action {
    New-MgApplication `
        -DisplayName $AppName `
        -SignInAudience 'AzureADMyOrg' `
        -RequiredResourceAccess $requiredResourceAccess
}

if (-not $DryRun) {
    # Attach the cert public key to the application.
    $certBytes = $cert.GetRawCertData()
    $keyCredentials = @(
        @{
            Type        = 'AsymmetricX509Cert'
            Usage       = 'Verify'
            Key         = $certBytes
            DisplayName = $CertSubject
            EndDateTime = $certEndDate
        }
    )
    Invoke-Action -Description 'uploading cert public key to app registration' -Action {
        Update-MgApplication -ApplicationId $app.Id -KeyCredentials $keyCredentials | Out-Null
    } | Out-Null

    # Grant admin consent: each app permission needs an OAuth2PermissionGrant
    # or, for application permissions, an AppRoleAssignment against the
    # service principal of the new application.
    $sp = Invoke-Action -Description 'creating service principal for new app' -Action {
        New-MgServicePrincipal -AppId $app.AppId
    }
    $graphSp = Get-MgServicePrincipal -Filter "appId eq '$graphResourceId'"
    foreach ($perm in $GraphPermissions) {
        Invoke-Action -Description "granting admin consent: $($perm.Name)" -Action {
            New-MgServicePrincipalAppRoleAssignment `
                -ServicePrincipalId $sp.Id `
                -PrincipalId $sp.Id `
                -ResourceId $graphSp.Id `
                -AppRoleId $perm.Id | Out-Null
        } | Out-Null
    }
}

# Final structured output. The fields below are what the operator pastes
# into the cstack tenant register flow.
Write-Host ''
Write-Host '----- cstack tenant registration block -----'
if ($DryRun) {
    Write-Host 'DRY RUN: real values not generated.'
} else {
    Write-Host "tenant_id      : $TenantId"
    Write-Host "client_id      : $($app.AppId)"
    Write-Host "cert_thumbprint: $($cert.Thumbprint.ToUpper())"
    Write-Host "cert_subject   : $CertSubject"
    Write-Host "added_at       : $((Get-Date).ToUniversalTime().ToString('o'))"
}
Write-Host '--------------------------------------------'
