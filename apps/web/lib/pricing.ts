/**
 * Centralized pricing plan definitions for Neura
 * Used across homepage and /pricing page to maintain consistency
 */

export interface PricingPlan {
  name: string;
  price: string;
  period: string;
  credits: string;
  features: string[];
  ctaText?: string; // Optional: defaults to "Get started" in PricingCard
  ctaHref: string;
  highlighted: boolean;
}

export const pricingPlans: PricingPlan[] = [
  {
    name: 'Free',
    price: '$0.00',
    period: '/month',
    credits: '250 credits/month',
    features: [
      'Essential features',
      'Basic support options',
      'Community resources',
      'Email support',
    ],
    ctaText: 'Get started',
    ctaHref: '/signup',
    highlighted: false,
  },
  {
    name: 'Basic',
    price: '$24.99',
    period: '/month',
    credits: '1000 credits/month',
    features: [
      'All essential features',
      'Priority support',
      'Advanced AI models',
      'Export capabilities',
      'Team collaboration',
    ],
    ctaText: 'Get started',
    ctaHref: '/signup',
    highlighted: true,
  },
  {
    name: 'Pro',
    price: '$49.00',
    period: '/month',
    credits: 'Unlimited credits/month',
    features: [
      'Everything in Basic',
      'Unlimited credits',
      'Premium AI models',
      'Priority support 24/7',
      'Custom integrations',
      'Advanced analytics',
    ],
    ctaText: 'Get started',
    ctaHref: '/signup',
    highlighted: false,
  },
];
