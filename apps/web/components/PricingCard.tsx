"use client";

import React from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Card, CardContent, CardFooter } from "@neura/ui";
import { Button } from "@neura/ui";
import { cn } from "@/lib/utils";
import { Check } from "lucide-react";

interface PricingCardProps {
  name: string;
  price: string;
  period?: string;
  credits: string;
  features: string[];
  ctaText?: string;
  ctaHref?: string;
  highlighted?: boolean;
  className?: string;
}

export default function PricingCard({
  name,
  price,
  period,
  credits,
  features,
  ctaText = "Get started",
  ctaHref = "/signup",
  highlighted = false,
  className,
}: PricingCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.6, delay: highlighted ? 0.1 : 0 }}
      className={cn(className)}
    >
      <Card
        className={cn(
          "p-6 shadow-card hover:shadow-hover transition-shadow",
          highlighted
            ? "bg-secondary text-secondary-foreground relative z-10 md:scale-105"
            : "",
        )}
      >
        <CardContent className="p-0">
          <div className="mb-4">
            <h3 className="text-2xl font-bold mb-2">{name}</h3>
            <div className="mb-1 flex items-baseline gap-2">
              <span className="text-4xl font-black">{price}</span>
              {period && <span className="text-lg font-normal opacity-80">{period}</span>}
            </div>
            <p className="text-sm opacity-80 mb-4">{credits}</p>
          </div>
          <ul className="space-y-3 mb-6">
            {features.map((feature) => (
              <li key={feature} className="flex items-start space-x-2">
                <Check
                  className="w-5 h-5 flex-shrink-0 text-primary"
                  aria-hidden="true"
                />
                <span className="text-sm">{feature}</span>
              </li>
            ))}
          </ul>
        </CardContent>
        <CardFooter className="p-0">
          <Button
            asChild
            size="lg"
            variant={highlighted ? "default" : "outline"}
            shape="pill"
            className="w-full shadow-card hover:shadow-hover transition-shadow"
          >
            <Link href={{ pathname: ctaHref }}>{ctaText}</Link>
          </Button>
        </CardFooter>
      </Card>
    </motion.div>
  );
}
