# scripts

Operational PowerShell scripts that run against a Microsoft Entra tenant.
Both are written for review in Sprint 1 and exercised against a real tenant
in Sprint 7.

## Prerequisites

- Windows with PowerShell 7+ (Windows PowerShell 5.1 works for Sprint 1).
- Microsoft Graph PowerShell module:

  ```powershell
  Install-Module Microsoft.Graph -Scope CurrentUser
  ```

- Caller running the script must hold at minimum `Application.ReadWrite.All`
  and (for setup) `DelegatedPermissionGrant.ReadWrite.All` in the target
  tenant.

## setup-app-reg.ps1

Provisions an app registration for cstack signalguard, including a 2-year
self-signed certificate placed in `Cert:\CurrentUser\My`, the required Graph
permissions (`Policy.Read.All`, `AuditLog.Read.All`, `Directory.Read.All`,
`RoleManagement.Read.Directory`, `Application.Read.All`), and admin consent.

```powershell
.\setup-app-reg.ps1 -TenantId <uuid>
.\setup-app-reg.ps1 -TenantId <uuid> -AppName cstack-prod -DryRun
```

The script prints a structured registration block at the end. Paste those
values into `cstack tenant add`.

## rotate-cert.ps1

Generates a fresh self-signed certificate, uploads its public key as an
additional credential on the existing app registration, and prints the new
thumbprint. The previous certificate stays in place so the operator can
verify the new credential before removing the old one.

```powershell
.\rotate-cert.ps1 -TenantId <uuid> -ClientId <client-uuid> -OldThumbprint <hex>
```

## Consent flow

`setup-app-reg.ps1` performs admin consent inline. If consent fails (for
example, the caller lacks the privileged role), the operator can grant it
manually via the Entra portal: Enterprise applications -> the new app ->
Permissions -> Grant admin consent.

## Sprint 1 status

These scripts have been written but not executed against a tenant. They are
a review artefact for the Sprint 7 tenant validation work.
