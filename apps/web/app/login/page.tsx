'use client';

import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth/auth-context';
import {
  Button,
  Input,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  Label,
} from '@neura/ui';

export default function LoginPage() {
  const { signIn } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const mapError = (message: string) => {
    const lower = message.toLowerCase();
    if (lower.includes('invalid login credentials')) return 'Invalid email or password.';
    if (lower.includes('email not confirmed')) return 'Please confirm your email before signing in.';
    if (lower.includes('rate limit')) return 'Too many attempts. Please wait and try again.';
    return message;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (!email || !password) {
        setError('Email and password are required');
        return;
      }
      const emailRegex = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
      if (!emailRegex.test(email)) {
        setError('Enter a valid email address');
        return;
      }
      const { error } = await signIn(email, password);
      if (error) {
        setError(mapError(error.message));
        return;
      }
      router.push('/dashboard');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen flex items-center justify-center p-8 bg-background">
      <Card className="w-full max-w-md">
        <CardHeader className="px-8 pt-8">
          <CardTitle className="text-2xl font-semibold">Sign In</CardTitle>
          <CardDescription className="mt-1">
            Enter your credentials to access Neura
          </CardDescription>
        </CardHeader>
        <CardContent className="px-8 py-6">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            {error && (
              <div className="text-sm border border-destructive/20 rounded-md p-3 text-destructive bg-destructive/10">
                {error}
              </div>
            )}
            <Button
              type="submit"
              className="w-full"
              disabled={loading}
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="px-8 pb-8 pt-2">
          <p className="text-sm text-muted-foreground">
            Don&apos;t have an account?{' '}
            <Link href="/signup" className="underline text-foreground hover:text-primary">
              Sign up
            </Link>
          </p>
        </CardFooter>
      </Card>
    </main>
  );
}
