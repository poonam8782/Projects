"use client";

import React, { FormEvent, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Button, Input, Label } from "@neura/ui";
import { cn } from "@/lib/utils";
import { Linkedin, Instagram } from "lucide-react";
import { toast } from "sonner";

interface FooterProps {
  className?: string;
}

export default function Footer({ className }: FooterProps) {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);

  const handleNewsletterSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = email.trim();
    if (!trimmed) {
      toast.error("Please enter your email address");
      return;
    }
    const emailRegex = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
    if (!emailRegex.test(trimmed)) {
      toast.error("Please enter a valid email address");
      return;
    }
    try {
      setLoading(true);
      await new Promise((res) => setTimeout(res, 1000));
      toast.success("Thanks for subscribing! We'll keep you updated.");
      setEmail("");
      // TODO: Integrate with newsletter API (e.g., Mailchimp, ConvertKit, or custom endpoint)
    } catch {
      toast.error("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <footer
      className={cn("relative z-10 bg-secondary text-secondary-foreground px-6 py-16 md:py-24", className)}
    >
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-12 md:gap-8">
          {/* Column 1: Logo + Tagline */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.6 }}
          >
            <div className="text-4xl md:text-5xl font-black mb-4">Neura</div>
            <p className="text-sm text-muted-foreground max-w-xs">
              Crafting intelligent solutions that turn your wildest tech dreams into reality.
            </p>
          </motion.div>

          {/* Column 2: Company & Legal (merged) */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            <div className="grid grid-cols-1 gap-8">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wider mb-4">Company</h3>
                <div>
                  {[{ label: "Blog", href: "/blog" }, { label: "Contact us", href: "/contact" }].map((l) => (
                    <Link
                      key={l.label}
                      href={{ pathname: l.href }}
                      className="block text-sm text-muted-foreground hover:text-primary transition-colors mb-2"
                    >
                      {l.label}
                    </Link>
                  ))}
                </div>
              </div>
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wider mb-4">Legal</h3>
                <div>
                  {[{ label: "Terms & Conditions", href: "/terms" }, { label: "Privacy Policy", href: "/privacy" }].map((l) => (
                    <Link
                      key={l.label}
                      href={{ pathname: l.href }}
                      className="block text-sm text-muted-foreground hover:text-primary transition-colors mb-2"
                    >
                      {l.label}
                    </Link>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>

          {/* Column 4: Newsletter */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <h3 className="text-sm font-semibold uppercase tracking-wider mb-4">Stay Updated</h3>
            <p className="text-sm text-muted-foreground mb-4">Get the latest updates and news.</p>
            <form onSubmit={handleNewsletterSubmit} noValidate>
              <Label htmlFor="newsletter-email" className="sr-only">
                Email
              </Label>
              <Input
                id="newsletter-email"
                type="email"
                placeholder="Enter your email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mb-3"
                disabled={loading}
              />
              <Button
                type="submit"
                variant="default"
                shape="pill"
                className="w-full"
                disabled={loading}
              >
                {loading ? "Subscribing..." : "Submit"}
              </Button>
            </form>
          </motion.div>
        </div>

        <div className="border-t border-border my-8" />

        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="flex items-center space-x-4"
          >
            {/* TODO: Replace with actual social media URLs */}
            <a
              href="https://linkedin.com"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="LinkedIn"
              className="text-muted-foreground hover:text-primary transition-colors"
            >
              <Linkedin className="w-5 h-5" />
            </a>
            <a
              href="https://instagram.com"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Instagram"
              className="text-muted-foreground hover:text-primary transition-colors"
            >
              <Instagram className="w-5 h-5" />
            </a>
          </motion.div>
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.6, delay: 0.5 }}
          >
            <p className="text-sm text-muted-foreground">© {new Date().getFullYear()} Neura. All rights reserved.</p>
          </motion.div>
        </div>
      </div>
    </footer>
  );
}
