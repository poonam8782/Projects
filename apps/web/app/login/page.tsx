"use client";

import React, { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/auth-context";
import Link from "next/link";

export default function Login(): JSX.Element {
  const { signIn } = useAuth();
  const router = useRouter();
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [strength, setStrength] = useState({ score: 0, label: '', color: '' });

  const checkPasswordStrength = (value: string) => {
    let score = 0;
    let label = '';
    let color = '';

    if (value.length > 0) score = 1;
    if (value.length >= 8) score++;
    if (/[A-Z]/.test(value) && /[a-z]/.test(value)) score++;
    if (/[0-9]/.test(value)) score++;
    if (/[^A-Za-z0-9]/.test(value)) score++;

    score = Math.min(score, 4);

    if (value.length === 0) {
      score = 0;
    } else if (score === 1) {
      label = 'Weak';
      color = 'bg-neo-main';
    } else if (score === 2) {
      label = 'Medium';
      color = 'bg-neo-purple';
    } else if (score === 3) {
      label = 'Strong';
      color = 'bg-neo-blue';
    } else if (score >= 4) {
      label = 'Very Strong';
      color = 'bg-neo-accent';
      score = 4;
    }

    setStrength({ score, label, color });
  };

  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newPassword = e.target.value;
    setPassword(newPassword);
    checkPasswordStrength(newPassword);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (!email || !password) {
        setError('Please enter both email and password');
        return;
      }

      const emailRegex = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
      if (!emailRegex.test(email)) {
        setError('Please enter a valid email address');
        return;
      }

      const { error: signInError } = await signIn(email, password);
      
      if (signInError) {
        setError(signInError.message || 'Invalid email or password');
        return;
      }

      // Successfully logged in, redirect to dashboard
      router.push('/dashboard');
    } catch (err) {
      setError('An unexpected error occurred. Please try again.');
      console.error('Login error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="font-body bg-neo-bg min-h-screen">
      <style jsx global>{`
        body { 
          background-color: #FFFAE5 !important; 
          color: #0f0f0f; 
        }
        ::selection { 
          background-color: #0f0f0f; 
          color: #A3FF00; 
        }
        ::-webkit-scrollbar { 
          width: 16px; 
        }
        ::-webkit-scrollbar-track { 
          background: #FFFAE5; 
          border-left: 3px solid #0f0f0f; 
        }
        ::-webkit-scrollbar-thumb { 
          background: #0f0f0f; 
          border: 3px solid #FFFAE5; 
        }
        ::-webkit-scrollbar-thumb:hover { 
          background: #FF4D00; 
        }
      `}</style>

      <nav className="sticky top-0 left-0 w-full flex justify-between items-center p-4 md:p-6 z-50 bg-neo-black text-neo-bg border-b-4 border-neo-accent shadow-neo">
        <div className="flex items-center gap-12">
          <Link href="/" className="font-heavy text-3xl tracking-tighter hover:text-neo-accent transition-colors">
            NEURA.
          </Link>
        </div>
        <div className="flex items-center gap-6">
          <Link href="/signup" className="font-body font-bold hover:text-neo-main transition-colors">
            Don't have an account?
          </Link>
          <Link 
            href="/signup" 
            className="border-2 border-neo-accent bg-neo-accent text-neo-black px-6 py-2 font-heavy hover:bg-neo-black hover:text-neo-accent transition-all duration-300"
          >
            Sign Up
          </Link>
        </div>
      </nav>

      <section className="flex items-center justify-center py-20 md:py-32 px-4">
        <div className="w-full max-w-md">
          <div className="bg-neo-white border-4 border-black shadow-neo p-8 md:p-12">
            <h1 className="font-heavy text-4xl uppercase text-black mb-8 text-center">Sign In</h1>
            
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label htmlFor="email" className="block font-heavy text-sm uppercase text-black mb-2">
                  Email
                </label>
                <input 
                  type="email" 
                  id="email" 
                  name="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full p-3 border-4 border-black bg-neo-bg font-body text-lg focus:outline-none focus:ring-4 focus:ring-neo-accent focus:border-neo-accent" 
                  required 
                  disabled={loading}
                />
              </div>
              
              <div>
                <div className="flex justify-between items-baseline mb-2">
                  <label htmlFor="password" className="block font-heavy text-sm uppercase text-black">
                    Password
                  </label>
                  <Link 
                    href="/forgot-password" 
                    className="font-body font-bold text-sm text-neo-blue hover:text-neo-main transition-colors"
                  >
                    Forgot password?
                  </Link>
                </div>
                <input 
                  type="password" 
                  id="password" 
                  name="password" 
                  className="w-full p-3 border-4 border-black bg-neo-bg font-body text-lg focus:outline-none focus:ring-4 focus:ring-neo-accent focus:border-neo-accent" 
                  required 
                  value={password}
                  onChange={handlePasswordChange}
                  disabled={loading}
                />
                {password.length > 0 && (
                  <div className="mt-2">
                    <div className="flex gap-1 w-full h-2 border-2 border-black p-0.5 bg-neo-bg/50">
                      <div className={`w-1/4 h-full transition-colors ${strength.score >= 1 ? strength.color : ''}`}></div>
                      <div className={`w-1/4 h-full transition-colors ${strength.score >= 2 ? strength.color : ''}`}></div>
                      <div className={`w-1/4 h-full transition-colors ${strength.score >= 3 ? strength.color : ''}`}></div>
                      <div className={`w-1/4 h-full transition-colors ${strength.score >= 4 ? strength.color : ''}`}></div>
                    </div>
                    <p className={`font-mono text-sm font-bold text-right mt-1 ${
                      strength.score === 1 ? 'text-neo-main' :
                      strength.score === 2 ? 'text-neo-purple' :
                      strength.score === 3 ? 'text-neo-blue' :
                      strength.score === 4 ? 'text-neo-accent' : ''
                    }`}>
                      {strength.label}
                    </p>
                  </div>
                )}
              </div>

              {error && (
                <div className="text-sm border-4 border-neo-main/50 rounded-none p-3 text-neo-main bg-neo-main/10 font-mono">
                  {error}
                </div>
              )}

              <button 
                type="submit" 
                disabled={loading}
                className="w-full border-4 border-black bg-neo-main text-white font-heavy text-xl px-8 py-4 shadow-neo hover:shadow-neo-active hover:-translate-y-1 hover:-translate-x-1 active:translate-y-0 active:translate-x-0 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:hover:translate-x-0"
              >
                {loading ? 'Signing in...' : 'Sign In'}
              </button>

              <div className="relative flex items-center justify-center my-8">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t-2 border-black/20"></div>
                </div>
                <div className="relative bg-neo-white px-4">
                  <span className="font-mono text-sm uppercase text-gray-600">OR</span>
                </div>
              </div>

              <button 
                type="button" 
                disabled
                className="w-full flex items-center justify-center gap-3 border-4 border-black bg-neo-white text-black font-heavy text-lg px-8 py-3 shadow-neo opacity-50 cursor-not-allowed"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                </svg>
                Continue with Google (Coming Soon)
              </button>
              <button 
                type="button" 
                disabled
                className="w-full flex items-center justify-center gap-3 border-4 border-black bg-neo-black text-white font-heavy text-lg px-8 py-3 shadow-neo opacity-50 cursor-not-allowed"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                </svg>
                Continue with GitHub (Coming Soon)
              </button>
            </form>
          </div>

          <p className="font-mono text-center text-gray-600 mt-6 text-sm">
            By signing in, you agree to our{' '}
            <Link href="/terms" className="font-bold text-black hover:text-neo-main">
              Terms
            </Link>{' '}
            and{' '}
            <Link href="/privacy" className="font-bold text-black hover:text-neo-main">
              Privacy Policy
            </Link>
            .
          </p>
        </div>
      </section>
    </main>
  );
}
