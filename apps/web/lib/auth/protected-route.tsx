'use client';

import { useEffect, type ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth/auth-context';
import { Card, CardContent } from '@neura/ui';

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
  }, [user, loading, router]);

  if (loading)
    return (
      <div className="min-h-screen flex items-center justify-center p-8 bg-black-ui">
        <Card className="bg-surface-ui border-border-ui text-text-ui w-full max-w-sm">
          <CardContent className="p-6 flex items-center gap-3">
            <span className="h-3 w-3 rounded-full bg-text-ui animate-pulse" />
            <span className="text-muted-ui">Loading...</span>
          </CardContent>
        </Card>
      </div>
    );
  if (!user) return null;
  return <>{children}</>;
}
