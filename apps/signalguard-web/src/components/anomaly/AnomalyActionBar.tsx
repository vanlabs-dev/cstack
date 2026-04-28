'use client';

import { AlertTriangle, Check, ExternalLink } from 'lucide-react';

import { CopyButton } from '@/components/findings/CopyButton';
import { Button } from '@/components/ui/Button';

import type { AnomalyScoreDetail } from '@/lib/api/generated/types.gen';

interface AnomalyActionBarProps {
  detail: AnomalyScoreDetail;
}

function buildPowerShellSnippet(detail: AnomalyScoreDetail): string {
  const userId = detail.signin.userId;
  const signinId = detail.signin.id;
  return [
    '# Investigate this sign-in via Microsoft Graph PowerShell.',
    'Connect-MgGraph -Scopes "User.Read.All","AuditLog.Read.All"',
    `Get-MgUser -UserId '${userId}' | Format-List`,
    `Get-MgUserAuthenticationMethod -UserId '${userId}'`,
    `Get-MgAuditLogSignIn -Filter "id eq '${signinId}'" | Format-List`,
  ].join('\n');
}

function entraPortalUrl(detail: AnomalyScoreDetail): string {
  return `https://entra.microsoft.com/#view/Microsoft_AAD_IAM/UserDetailsMenuBlade/~/Profile/userId/${encodeURIComponent(detail.signin.userId)}`;
}

export function AnomalyActionBar({ detail }: AnomalyActionBarProps) {
  const snippet = buildPowerShellSnippet(detail);
  const json = JSON.stringify(detail, null, 2);
  return (
    <div className="sticky bottom-0 mt-3 flex flex-wrap items-center gap-1.5 rounded-r-md border border-border bg-surface p-2.5">
      <a
        href={entraPortalUrl(detail)}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex h-7 items-center gap-1.5 rounded-r border border-border bg-surface px-2.5 text-13 font-medium transition-colors hover:bg-surface-hover hover:border-border-strong"
      >
        <ExternalLink size={12} strokeWidth={1.6} aria-hidden />
        Open in Entra portal
      </a>
      <Button
        variant="ghost"
        size="default"
        title="Mark known-good lands in 5b"
        aria-label="Mark known-good"
      >
        <Check size={12} aria-hidden />
        Mark known-good
      </Button>
      <Button
        variant="ghost"
        size="default"
        title="Escalate flow lands in 5b"
        aria-label="Escalate"
      >
        <AlertTriangle size={12} aria-hidden />
        Escalate
      </Button>
      <CopyButton text={json} label="Copy as JSON" className="h-7 px-2.5" />
      <CopyButton text={snippet} label="Copy PowerShell snippet" className="h-7 px-2.5" />
    </div>
  );
}
