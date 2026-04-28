import type { SignIn } from '@/lib/api/generated/types.gen';

import { MetadataRow } from './MetadataRow';

interface MetadataTableProps {
  signin: SignIn;
}

interface Group {
  eyebrow: string;
  rows: Array<{
    label: string;
    value: string | number | boolean | null | undefined;
    mono?: boolean;
    copy?: boolean;
    flag?: boolean;
  }>;
}

const FLAG_KEYS = new Set([
  'risk_level_during_sign_in',
  'risk_level_aggregated',
  'risk_state',
  'device.is_compliant',
  'ca_status',
]);

function flagged(key: string): boolean {
  return FLAG_KEYS.has(key);
}

function buildGroups(signin: SignIn): Group[] {
  const device = signin.deviceDetail ?? null;
  const location = signin.location ?? null;
  const status = signin.status ?? null;
  return [
    {
      eyebrow: 'Identity',
      rows: [
        { label: 'id', value: signin.id, mono: true, copy: true },
        {
          label: 'userPrincipalName',
          value: signin.userPrincipalName,
          copy: true,
        },
        { label: 'userId', value: signin.userId, mono: true, copy: true },
        { label: 'isInteractive', value: signin.isInteractive ?? null },
      ],
    },
    {
      eyebrow: 'Time',
      rows: [
        {
          label: 'createdDateTime',
          value: signin.createdDateTime,
          mono: true,
        },
      ],
    },
    {
      eyebrow: 'Location',
      rows: [
        { label: 'ipAddress', value: signin.ipAddress, mono: true, copy: true },
        { label: 'city', value: location?.city ?? null },
        { label: 'state', value: location?.state ?? null },
        { label: 'countryOrRegion', value: location?.countryOrRegion ?? null },
        {
          label: 'latitude',
          value: location?.geoCoordinates?.latitude ?? null,
          mono: true,
        },
        {
          label: 'longitude',
          value: location?.geoCoordinates?.longitude ?? null,
          mono: true,
        },
      ],
    },
    {
      eyebrow: 'Network',
      rows: [
        { label: 'clientAppUsed', value: signin.clientAppUsed ?? null },
        { label: 'appId', value: signin.appId ?? null, mono: true },
        { label: 'appDisplayName', value: signin.appDisplayName ?? null },
      ],
    },
    {
      eyebrow: 'Device',
      rows: [
        {
          label: 'device.id',
          value: device?.deviceId ?? null,
          mono: true,
        },
        { label: 'device.os', value: device?.operatingSystem ?? null },
        { label: 'device.browser', value: device?.browser ?? null },
        {
          label: 'device.isCompliant',
          value: device?.isCompliant ?? null,
          flag: flagged('device.is_compliant') && device?.isCompliant === false,
        },
        { label: 'device.isManaged', value: device?.isManaged ?? null },
        { label: 'device.trustType', value: device?.trustType ?? null },
      ],
    },
    {
      eyebrow: 'Auth',
      rows: [
        {
          label: 'conditionalAccessStatus',
          value: signin.conditionalAccessStatus ?? null,
          flag: flagged('ca_status') && signin.conditionalAccessStatus === 'notApplied',
        },
        {
          label: 'authenticationRequirement',
          value: signin.authenticationRequirement ?? null,
        },
        {
          label: 'authMethodsUsed',
          value: signin.authenticationMethodsUsed?.join(', ') ?? null,
        },
        {
          label: 'riskLevelDuringSignIn',
          value: signin.riskLevelDuringSignIn ?? null,
          flag: flagged('risk_level_during_sign_in') && signin.riskLevelDuringSignIn === 'high',
        },
        {
          label: 'riskLevelAggregated',
          value: signin.riskLevelAggregated ?? null,
          flag: flagged('risk_level_aggregated') && signin.riskLevelAggregated === 'high',
        },
        {
          label: 'riskState',
          value: signin.riskState ?? null,
          flag: flagged('risk_state') && signin.riskState === 'atRisk',
        },
      ],
    },
    {
      eyebrow: 'Outcome',
      rows: [
        {
          label: 'status.errorCode',
          value: status?.errorCode ?? null,
          mono: true,
        },
        {
          label: 'status.failureReason',
          value: status?.failureReason ?? null,
        },
      ],
    },
  ];
}

export function MetadataTable({ signin }: MetadataTableProps) {
  const groups = buildGroups(signin);
  return (
    <div className="overflow-hidden rounded-r-md border border-border bg-surface">
      <div className="flex items-center justify-between border-b border-border px-3.5 py-3">
        <div className="text-13 font-semibold">Sign-in metadata</div>
        <span className="mono text-11 text-fg-tertiary">graph.signIn</span>
      </div>
      <div>
        {groups.map((g, gi) => (
          <div key={g.eyebrow}>
            <div className="bg-surface-subtle px-3.5 py-1.5">
              <span className="eyebrow">{g.eyebrow}</span>
            </div>
            {g.rows.map((r, ri) => (
              <MetadataRow
                key={`${g.eyebrow}-${r.label}`}
                label={r.label}
                value={r.value}
                mono={r.mono}
                copy={r.copy}
                flag={r.flag}
                isLast={ri === g.rows.length - 1 && gi === groups.length - 1}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
