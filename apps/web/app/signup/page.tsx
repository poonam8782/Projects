'use client';

import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
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

export default function SignupPage() {
  const { signUp } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const mapError = (message: string) => {
    const lower = message.toLowerCase();
    if (lower.includes('password')) return 'Password needs at least 8 characters';
    if (lower.includes('rate limit')) return 'Too many attempts. Please wait and try again.';
    if (lower.includes('email')) return 'Invalid email address';
    return message;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (!email || !password || !confirmPassword) {
        setError('All fields are required');
        return;
      }
      const emailRegex = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
      if (!emailRegex.test(email)) {
        setError('Enter a valid email address');
        return;
      }
      if (password.length < 8) {
        setError('Password needs at least 8 characters');
        return;
      }
      if (password !== confirmPassword) {
        setError('Passwords do not match');
        return;
      }
      const { error, sessionCreated } = await signUp(email, password);
      if (error) {
        setError(mapError(error.message));
        return;
      }
      if (sessionCreated) {
        router.push('/dashboard');
        return;
      }
      setSuccess(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen flex items-center justify-center p-8 bg-neo-bg">
      <div className="w-full max-w-md">
        <div className="flex items-center justify-center mb-8">
          <Image src="/favicon.svg" alt="Neura Logo" width={80} height={80} />
        </div>

        <Card className="w-full">
          <CardHeader className="px-8 pt-8">
            <CardTitle className="text-2xl font-semibold">Create your account</CardTitle>
            <CardDescription className="mt-1">
              Join thousands organizing their thoughts beautifully
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
                  autoComplete="new-password"
                  placeholder="Minimum 8 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                {password.length > 0 && <PasswordStrength password={password} />}
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm Password</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  autoComplete="new-password"
                  placeholder="Confirm password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </div>
              {error && (
                <div className="text-sm border border-destructive/20 rounded-md p-3 text-destructive bg-destructive/10">
                  {error}
                </div>
              )}
              {success && (
                <div className="text-sm border border-green-500/20 rounded-md p-3 text-green-600 bg-green-50 space-y-2">
                  <p>Account created! Check your email to confirm.</p>
                  <p>
                    Already confirmed?{' '}
                    <Link href="/login" className="underline hover:text-green-700">
                      Sign in now
                    </Link>
                  </p>
                </div>
              )}
              <Button
                type="submit"
                className="w-full"
                disabled={loading || success}
              >
                {loading ? 'Creating account...' : 'Create account'}
              </Button>

              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-background px-2 text-muted-foreground">
                    Or continue with
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <Button variant="outline" className="w-full">
                  <Image src="/icons/google.svg" alt="Google" width={16} height={16} className="mr-2" />
                  Google
                </Button>
                <Button variant="outline" className="w-full">
                  <Image src="/icons/github.svg" alt="GitHub" width={16} height={16} className="mr-2" />
                  GitHub
                </Button>
              </div>

              <p className="text-xs text-center text-muted-foreground">
                By continuing you agree to our{' '}
                <Link href="#" className="underline hover:text-primary">Terms</Link> and{' '}
                <Link href="#" className="underline hover:text-primary">Privacy Policy</Link>
              </p>
            </form>
          </CardContent>
          <CardFooter className="flex flex-col items-center gap-2 px-8 pb-8">
            <p className="text-sm text-muted-foreground">
              Already have an account?{' '}
              <Link href="/login" className="font-medium text-primary hover:underline">
                Sign in
              </Link>
            </p>
          </CardFooter>
        </Card>
      </div>
    </main>
  );
}

function PasswordStrength({ password }: { password: string }) {
  const getStrength = () => {
    let strength = 0;
    if (password.length >= 8) strength++;
    if (password.match(/[a-z]/) && password.match(/[A-Z]/)) strength++;
    if (password.match(/[0-9]/)) strength++;
    if (password.match(/[^a-zA-Z0-9]/)) strength++;
    return strength;
  };

  const strength = getStrength();
  const strengthLevels = ['Weak', 'Fair', 'Good', 'Strong', 'Very Strong'];
  const strengthColors = ['bg-red-500', 'bg-orange-500', 'bg-yellow-500', 'bg-green-500', 'bg-emerald-500'];
  
  const strengthText = strengthLevels[strength] || 'Weak';
  const strengthColor = strengthColors[strength] || 'bg-red-500';

  return (
    <div className="mt-2 space-y-1">
      <div className="flex gap-1 h-1">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className={`flex-1 rounded-full transition-all ${
              i < strength ? strengthColor : 'bg-muted'
            }`}
          />
        ))}
      </div>
      <p className="text-xs text-muted-foreground">
        {strengthText} password
      </p>
    </div>
  );
}