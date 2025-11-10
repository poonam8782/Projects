"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@neura/ui";
import { cn } from "@/lib/utils";
import { Menu, X } from "lucide-react";
import { toast } from "sonner";

interface TopNavProps {
  className?: string;
}

export default function TopNav({ className }: TopNavProps) {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        setIsScrolled(!entry?.isIntersecting);
      },
      { rootMargin: "-50px 0px 0px 0px", threshold: 0 }
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, []);

  const links = [
    { hash: "features", label: "Features" },
    { hash: "benefits", label: "Benefits" },
    { hash: "pricing", label: "Pricing" },
    { hash: "contact", label: "Contact" },
  ];

  const handlePurchase = () => {
    const url = process.env.NEXT_PUBLIC_PURCHASE_URL;
    if (url) {
      window.open(url, "_blank");
    } else {
      toast.info("Coming soon! Check back later.");
    }
  };

  return (
    <>
      {/* Sentinel used for scroll detection without affecting layout */}
      <div ref={sentinelRef} aria-hidden className="h-px w-0 pointer-events-none" />

      <nav
        className={cn(
          "sticky top-0 z-50",
          className
        )}
        role="navigation"
        aria-label="Primary"
      >
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div
            className={cn(
              "relative rounded-full border border-border/20 bg-card/80",
              "backdrop-blur-md transition-all",
              isScrolled && "backdrop-blur-lg shadow-hover"
            )}
            style={{ boxShadow: isScrolled ? undefined : "var(--shadow-nav)" }}
          >
            <div className="flex items-center justify-between px-6 py-3">
              {/* Left: Logo */}
              <Link
                href="/"
                className="text-2xl font-bold text-foreground hover:opacity-80 transition-opacity"
                aria-label="Neura Home"
              >
                Neura
              </Link>

              {/* Center: Nav links (desktop) */}
              <div className="hidden md:flex items-center space-x-8">
                {links.map((link) => {
                  const href = link.hash === "contact" ? "/contact" : { pathname: "/", hash: link.hash };
                  return (
                    <Link
                      key={link.hash}
                      href={href}
                      className="group relative text-sm font-medium text-foreground hover:text-primary transition-colors"
                    >
                      {link.label}
                      <span
                        className="pointer-events-none absolute left-0 -bottom-1 h-0.5 w-0 bg-primary transition-all duration-normal group-hover:w-full"
                        aria-hidden
                      />
                    </Link>
                  );
                })}
              </div>

              {/* Right: CTA (desktop) */}
              <div className="hidden md:block">
                <Button
                  onClick={handlePurchase}
                  variant="default"
                  shape="pill"
                  className="shadow-card hover:shadow-hover transition-shadow"
                >
                  Purchase
                </Button>
              </div>

              {/* Mobile menu toggle */}
              <button
                className="md:hidden inline-flex items-center justify-center p-2 rounded-sm text-foreground hover:bg-accent focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-ring"
                onClick={() => setIsMobileMenuOpen((v) => !v)}
                aria-label="Toggle menu"
                aria-expanded={isMobileMenuOpen}
              >
                {isMobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
              </button>
            </div>

            {/* Mobile dropdown */}
            <AnimatePresence>
              {isMobileMenuOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className="md:hidden absolute top-full left-0 right-0 mt-2 px-4"
                >
                  <div className="rounded-full border border-border/20 bg-card/90 shadow-card backdrop-blur-md">
                    <div className="p-6 space-y-4">
                      {links.map((link) => {
                        const href = link.hash === "contact" ? "/contact" : { pathname: "/", hash: link.hash };
                        return (
                          <Link
                            key={link.hash}
                            href={href}
                            className="block text-foreground hover:text-primary transition-colors text-sm font-medium"
                            onClick={() => setIsMobileMenuOpen(false)}
                          >
                            {link.label}
                          </Link>
                        );
                      })}
                      <Button
                        onClick={handlePurchase}
                        variant="default"
                        shape="pill"
                        className="w-full shadow-card hover:shadow-hover transition-shadow"
                      >
                        Purchase
                      </Button>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </nav>
    </>
  );
}
