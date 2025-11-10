'use client';

import { useState, FormEvent, useEffect } from 'react';
import { motion, useReducedMotion, AnimatePresence } from 'framer-motion';
import {
  Button,
  Input,
  Textarea,
  Label,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from '@neura/ui';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import TopNav from '@/components/TopNav';
import Footer from '@/components/Footer';
import { Mail, MessageSquare } from 'lucide-react';

const LETTER_DELAY = 0.025;
const BOX_FADE_DURATION = 0.125;
const FADE_DELAY = 5;
const MAIN_FADE_DURATION = 0.25;
const SWAP_DELAY_IN_MS = 5500;

const Typewrite = ({ examples }: { examples: string[] }) => {
  const [exampleIndex, setExampleIndex] = useState(0);

  useEffect(() => {
    const intervalId = setInterval(() => {
      setExampleIndex((pv) => (pv + 1) % examples.length);
    }, SWAP_DELAY_IN_MS);

    return () => clearInterval(intervalId);
  }, [examples.length]);

  const currentExample = examples[exampleIndex] || "";

  return (
    <p className="mb-2.5 text-sm font-light uppercase text-gray-700">
      <span className="inline-block size-2 bg-[#ff8800]" />
      <span className="ml-3">
        EXAMPLE:{" "}
        {currentExample.split("").map((l, i) => (
          <motion.span
            initial={{
              opacity: 1,
            }}
            animate={{
              opacity: 0,
            }}
            transition={{
              delay: FADE_DELAY,
              duration: MAIN_FADE_DURATION,
              ease: "easeInOut",
            }}
            key={`${exampleIndex}-${i}`}
            className="relative"
          >
            <motion.span
              initial={{
                opacity: 0,
              }}
              animate={{
                opacity: 1,
              }}
              transition={{
                delay: i * LETTER_DELAY,
                duration: 0,
              }}
            >
              {l}
            </motion.span>
            <motion.span
              initial={{
                opacity: 0,
              }}
              animate={{
                opacity: [0, 1, 0],
              }}
              transition={{
                delay: i * LETTER_DELAY,
                times: [0, 0.1, 1],
                duration: BOX_FADE_DURATION,
                ease: "easeInOut",
              }}
              className="absolute bottom-[3px] left-[1px] right-0 top-[3px] bg-[#ff8800]"
            />
          </motion.span>
        ))}
      </span>
    </p>
  );
};

const BlockInTextCard = ({ tag, text, examples }: { tag: string; text: React.ReactNode; examples: string[] }) => {
  return (
    <div className="w-full max-w-xl space-y-6">
      <div>
        <p className="mb-1.5 text-sm font-light uppercase text-gray-600">{tag}</p>
        <hr className="border-gray-300" />
      </div>
      <p className="max-w-lg text-xl leading-relaxed text-landing-dark">{text}</p>
      <div>
        <Typewrite examples={examples} />
        <hr className="border-gray-300" />
      </div>
    </div>
  );
};

export default function ContactPageClient() {
  const prefersReducedMotion = useReducedMotion();

  // Contact form state
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  // Waitlist form state
  const [waitlistEmail, setWaitlistEmail] = useState('');
  const [waitlistLoading, setWaitlistLoading] = useState(false);

  // UI state
  const [activeTab, setActiveTab] = useState<'contact' | 'waitlist'>('contact');

  const handleContactSubmit = async (e: FormEvent) => {
    e.preventDefault();

    // Validation
    if (!name.trim()) {
      toast.error('Please enter your name');
      return;
    }

    if (!email.trim()) {
      toast.error('Please enter your email address');
      return;
    }

    const emailRegex = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
    if (!emailRegex.test(email)) {
      toast.error('Please enter a valid email address');
      return;
    }

    if (!message.trim()) {
      toast.error('Please enter a message');
      return;
    }

    if (message.trim().length < 10) {
      toast.error('Message must be at least 10 characters');
      return;
    }

    try {
      setLoading(true);

      // Check if Formspree URL is configured
      const formspreeContactUrl = process.env.NEXT_PUBLIC_FORMSPREE_CONTACT_URL;
      
      if (!formspreeContactUrl) {
        // Fallback to simulated submission if not configured
        await new Promise((res) => setTimeout(res, 1000));
        toast.success("Thanks for reaching out! We&apos;ll get back to you soon.");
        console.warn('NEXT_PUBLIC_FORMSPREE_CONTACT_URL not configured. Using simulated submission.');
      } else {
        // Real submission to Formspree
        const response = await fetch(formspreeContactUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            name,
            email,
            message,
          }),
        });

        if (!response.ok) {
          throw new Error('Failed to submit form');
        }

        toast.success("Thanks for reaching out! We&apos;ll get back to you soon.");
      }

      // Clear form fields
      setName('');
      setEmail('');
      setMessage('');
    } catch (error) {
      console.error('Error submitting contact form:', error);
      toast.error('Failed to send message. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleWaitlistSubmit = async (e: FormEvent) => {
    e.preventDefault();

    // Validation
    if (!waitlistEmail.trim()) {
      toast.error('Please enter your email address');
      return;
    }

    const emailRegex = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
    if (!emailRegex.test(waitlistEmail)) {
      toast.error('Please enter a valid email address');
      return;
    }

    try {
      setWaitlistLoading(true);

      // Check if Formspree URL is configured
      const formspreeWaitlistUrl = process.env.NEXT_PUBLIC_FORMSPREE_WAITLIST_URL;
      
      if (!formspreeWaitlistUrl) {
        // Fallback to simulated submission if not configured
        await new Promise((res) => setTimeout(res, 1000));
        toast.success("You&apos;re on the waitlist! We&apos;ll notify you about new features.");
        console.warn('NEXT_PUBLIC_FORMSPREE_WAITLIST_URL not configured. Using simulated submission.');
      } else {
        // Real submission to Formspree
        const response = await fetch(formspreeWaitlistUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            email: waitlistEmail,
          }),
        });

        if (!response.ok) {
          throw new Error('Failed to submit waitlist form');
        }

        toast.success("You&apos;re on the waitlist! We&apos;ll notify you about new features.");
      }

      // Clear email field
      setWaitlistEmail('');
    } catch (error) {
      console.error('Error submitting waitlist form:', error);
      toast.error('Failed to join waitlist. Please try again.');
    } finally {
      setWaitlistLoading(false);
    }
  };

  return (
    <main
      className="min-h-screen relative overflow-hidden"
      style={{ background: 'var(--landing-gradient)' }}
    >
      <TopNav />

      {/* Hero section */}
      <section className="relative z-10 max-w-5xl mx-auto px-6 py-20 md:py-32 text-center">
        <motion.div
          initial={prefersReducedMotion ? { opacity: 0 } : { opacity: 0, y: 30 }}
          animate={prefersReducedMotion ? { opacity: 1 } : { opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.22, 0.9, 0.36, 1] }}
        >
          <h1 className="text-hero leading-hero font-black text-landing-dark mb-6">
            Get in Touch
          </h1>
          <p className="text-lg md:text-xl text-landing-muted max-w-3xl mx-auto mb-12">
            Have questions about Neura? We&apos;d love to hear from you.
          </p>

          {/* Typewriter Card */}
          <div className="flex items-center justify-center mb-12">
            <BlockInTextCard
              tag="/ Support"
              text={
                <>
                  <strong>Have questions?</strong> We&apos;d love to help! Contact support
                  for any issue you may face.
                </>
              }
              examples={[
                "Does your product work for SMBs?",
                "Can I pause my membership without losing my data?",
                "How does seat based pricing work?",
                "What features are coming next?",
              ]}
            />
          </div>

          {/* Tab navigation */}
          <div className="flex justify-center gap-4 mb-8">
            <button
              onClick={() => setActiveTab('contact')}
              className={cn(
                'px-6 py-3 rounded-landing-pill font-medium transition-colors',
                activeTab === 'contact'
                  ? 'bg-landing-orange text-white'
                  : 'bg-landing-white text-landing-dark border border-gray-200'
              )}
            >
              Contact
            </button>
            <button
              onClick={() => setActiveTab('waitlist')}
              className={cn(
                'px-6 py-3 rounded-landing-pill font-medium transition-colors',
                activeTab === 'waitlist'
                  ? 'bg-landing-orange text-white'
                  : 'bg-landing-white text-landing-dark border border-gray-200'
              )}
            >
              Waitlist
            </button>
          </div>
        </motion.div>
      </section>

      <AnimatePresence mode="wait">
        {/* Contact form section */}
        {activeTab === 'contact' && (
          <section key="contact" className="relative z-10 max-w-2xl mx-auto px-6 py-8">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ duration: 0.3 }}
            >
              <Card className="bg-landing-white rounded-landing-lg shadow-landing-card border border-gray-100 p-8">
                <CardHeader>
                  <MessageSquare className="w-8 h-8 text-landing-orange mb-4" />
                  <CardTitle className="text-2xl font-bold text-landing-dark mb-2">
                    Send us a message
                  </CardTitle>
                  <CardDescription className="text-landing-muted">
                    Fill out the form below and we&apos;ll get back to you within 24 hours.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleContactSubmit} noValidate>
                    {/* Name field */}
                    <div className="space-y-2 mb-4">
                      <Label htmlFor="name" className="text-sm font-medium text-landing-dark">
                        Name
                      </Label>
                      <Input
                        id="name"
                        type="text"
                        placeholder="Your name"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        className="bg-white border-gray-300 text-landing-dark focus:border-landing-orange"
                        disabled={loading}
                      />
                    </div>

                    {/* Email field */}
                    <div className="space-y-2 mb-4">
                      <Label htmlFor="email" className="text-sm font-medium text-landing-dark">
                        Email
                      </Label>
                      <Input
                        id="email"
                        type="email"
                        placeholder="you@example.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="bg-white border-gray-300 text-landing-dark focus:border-landing-orange"
                        disabled={loading}
                      />
                    </div>

                    {/* Message field */}
                    <div className="space-y-2 mb-6">
                      <Label htmlFor="message" className="text-sm font-medium text-landing-dark">
                        Message
                      </Label>
                      <Textarea
                        id="message"
                        placeholder="Tell us how we can help..."
                        rows={6}
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        className="bg-white border-gray-300 text-landing-dark focus:border-landing-orange resize-none"
                        disabled={loading}
                      />
                    </div>

                    {/* Submit button */}
                    <Button
                      type="submit"
                      variant="default"
                      size="lg"
                      shape="pill"
                      className="w-full bg-landing-orange hover:bg-landing-orange/90 text-white shadow-landing-card hover:shadow-landing-hover"
                      disabled={loading}
                    >
                      {loading ? 'Sending...' : 'Send message'}
                    </Button>
                  </form>
                </CardContent>
              </Card>
            </motion.div>
          </section>
        )}

        {/* Waitlist form section */}
        {activeTab === 'waitlist' && (
          <section key="waitlist" className="relative z-10 max-w-2xl mx-auto px-6 py-8">
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
            >
              <Card className="bg-landing-white rounded-landing-lg shadow-landing-card border border-gray-100 p-8">
                <CardHeader>
                  <Mail className="w-8 h-8 text-landing-orange mb-4" />
                  <CardTitle className="text-2xl font-bold text-landing-dark mb-2">
                    Join our waitlist
                  </CardTitle>
                  <CardDescription className="text-landing-muted">
                    Be the first to know about new features, updates, and exclusive early access.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleWaitlistSubmit} noValidate>
                    {/* Email field */}
                    <div className="space-y-2 mb-6">
                      <Label htmlFor="waitlist-email" className="text-sm font-medium text-landing-dark">
                        Email
                      </Label>
                      <Input
                        id="waitlist-email"
                        type="email"
                        placeholder="you@example.com"
                        value={waitlistEmail}
                        onChange={(e) => setWaitlistEmail(e.target.value)}
                        className="bg-white border-gray-300 text-landing-dark focus:border-landing-orange"
                        disabled={waitlistLoading}
                      />
                    </div>

                    {/* Submit button */}
                    <Button
                      type="submit"
                      variant="default"
                      size="lg"
                      shape="pill"
                      className="w-full bg-landing-orange hover:bg-landing-orange/90 text-white shadow-landing-card hover:shadow-landing-hover"
                      disabled={waitlistLoading}
                    >
                      {waitlistLoading ? 'Joining...' : 'Join waitlist'}
                    </Button>

                    <p className="text-xs text-landing-muted text-center mt-4">
                      We respect your privacy. Unsubscribe at any time.
                    </p>
                  </form>
                </CardContent>
              </Card>
            </motion.div>
          </section>
        )}
      </AnimatePresence>

      <Footer />

      {/* TODO: Future enhancements
        - Add CAPTCHA or honeypot field to prevent spam
        - Add file upload for attachments (e.g., screenshots)
        - Add subject/category dropdown for better routing
        - Add live chat widget integration (Intercom, Crisp, etc.)
        - Add estimated response time indicator
        - Add FAQ section to reduce support volume
        - Add success page redirect after submission
        - Add email confirmation after submission
        - Track form submissions in analytics
      */}

      {/* TODO: Integration options
        - Formspree: Simple form backend, free tier available, just POST to their endpoint
        - Netlify Forms: Built-in form handling if deployed on Netlify, add data-netlify="true" attribute
        - Supabase function: Create a custom Edge Function to handle form submissions and store in Supabase table
        - Email service: Use SendGrid, Mailgun, or AWS SES to send emails directly
        - Waitlist table: Create a waitlist table in Supabase with columns: id, email, created_at, notified
        - Contact submissions table: Create a contact_submissions table in Supabase with columns: id, name, email, message, created_at, status
      */}
    </main>
  );
}
