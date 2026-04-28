import { redirect } from 'next/navigation';

interface SettingsRedirectProps {
  searchParams: Promise<{ tenant?: string | string[] }>;
}

export default async function SettingsRedirect({ searchParams }: SettingsRedirectProps) {
  const params = await searchParams;
  const tenant = Array.isArray(params.tenant) ? params.tenant[0] : params.tenant;
  redirect(`/dashboard/settings/general${tenant ? `?tenant=${tenant}` : ''}`);
}
