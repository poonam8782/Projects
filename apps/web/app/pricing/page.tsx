import { Metadata } from 'next';
import PricingPageClient from './PricingPageClient';

export const metadata: Metadata = {
  title: 'Pricing - Neura | Choose Your Plan',
  description: 'Choose the plan that fits your needs. Transform documents into structured learning materials with AI-powered notes, mindmaps, and flashcards.',
  openGraph: {
    title: 'Pricing - Neura | Choose Your Plan',
    description: 'Choose the plan that fits your needs. Transform documents into structured learning materials with AI-powered notes, mindmaps, and flashcards.',
    type: 'website',
    url: 'https://yoursite.com/pricing',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Pricing - Neura | Choose Your Plan',
    description: 'Choose the plan that fits your needs. Transform documents into structured learning materials with AI-powered notes, mindmaps, and flashcards.',
  },
};

export default function PricingPage() {
  return <PricingPageClient />;
}
