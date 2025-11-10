'use client';

import { motion, useReducedMotion } from 'framer-motion';
import TopNav from '@/components/TopNav';
import Footer from '@/components/Footer';
import PricingCard from '@/components/PricingCard';
import { Button } from '@neura/ui';
import Link from 'next/link';
import { pricingPlans } from '@/lib/pricing';

export default function PricingPageClient() {
  const prefersReducedMotion = useReducedMotion();

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
            Choose the Plan That Fits Your Needs
          </h1>
          <p className="text-lg md:text-xl text-landing-muted max-w-3xl mx-auto mb-12">
            Transform documents into structured learning materials with AI-powered notes, mindmaps, flashcards, and intelligent chat. Start free, upgrade anytime.
          </p>
        </motion.div>
      </section>

      {/* Pricing cards section */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 py-16 md:py-24">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 md:gap-10">
          {pricingPlans.map((plan) => (
            <PricingCard
              key={plan.name}
              name={plan.name}
              price={plan.price}
              period={plan.period}
              credits={plan.credits}
              features={plan.features}
              ctaText={plan.ctaText}
              ctaHref={plan.ctaHref}
              highlighted={plan.highlighted}
            />
          ))}
        </div>
      </section>

      {/* CTA section */}
      <section className="relative z-10 max-w-5xl mx-auto px-6 py-16 md:py-24 text-center">
        <motion.div
          initial={prefersReducedMotion ? { opacity: 0 } : { opacity: 0, y: 30 }}
          animate={prefersReducedMotion ? { opacity: 1 } : { opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.22, 0.9, 0.36, 1] }}
        >
          <h2 className="text-h2 font-bold text-landing-dark mb-6">
            Ready to get started?
          </h2>
          <p className="text-lg text-landing-muted mb-8">
            Join thousands of users transforming their documents into structured learning materials.
          </p>
          <Link href="/signup">
            <Button
              variant="default"
              size="lg"
              shape="pill"
              className="shadow-landing-card hover:shadow-landing-hover"
            >
              Start for free →
            </Button>
          </Link>
        </motion.div>
      </section>

      <Footer />

      {/* TODO: Future enhancements
        - Add annual billing toggle (switch between monthly/yearly pricing with discount)
        - Add "Most Popular" badge to highlighted card
        - Add comparison table showing feature differences
        - Add testimonials or social proof
        - Add FAQ accordion section
        - Add JSON-LD structured data for rich snippets in search results
        - Consider A/B testing different pricing tiers or copy
      */}
    </main>
  );
}
