import { QueryProvider } from '@/components/system/QueryProvider';
import { ThemeProvider } from '@/components/system/ThemeProvider';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <QueryProvider>{children}</QueryProvider>
    </ThemeProvider>
  );
}
