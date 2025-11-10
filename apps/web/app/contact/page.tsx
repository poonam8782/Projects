import { Metadata } from 'next';
import ContactPageClient from './ContactPageClient';

export const metadata: Metadata = {
  title: 'Contact Us - Neura | Get in Touch',
  description: 'Have questions about Neura? Get in touch with our team or join our waitlist for early access to new features.',
  openGraph: {
    title: 'Contact Us - Neura | Get in Touch',
    description: 'Have questions about Neura? Get in touch with our team or join our waitlist for early access to new features.',
    type: 'website',
    url: 'https://yoursite.com/contact',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Contact Us - Neura | Get in Touch',
    description: 'Have questions about Neura? Get in touch with our team or join our waitlist for early access to new features.',
  },
};

export default function ContactPage() {
  return <ContactPageClient />;
}
