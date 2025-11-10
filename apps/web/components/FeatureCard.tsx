"use client";

import React from "react";
import { motion } from "framer-motion";
import { Card } from "@neura/ui";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface FeatureCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
  iconColor?: string;
  className?: string;
  disableMotion?: boolean;
}

export default function FeatureCard({ icon: Icon, title, description, iconColor = "text-primary", className, disableMotion = false }: FeatureCardProps) {
  const Wrapper: React.ElementType = disableMotion ? "div" : motion.div;
  const motionProps = disableMotion
    ? { }
    : {
        initial: { opacity: 0, y: 20 },
        whileInView: { opacity: 1, y: 0 },
        viewport: { once: true, margin: "-100px" },
        transition: { duration: 0.5, ease: "easeOut" },
      };

  return (
    <Wrapper {...motionProps}>
      <Card
        className={cn(
          "overflow-hidden shadow-card hover:shadow-hover transition-shadow duration-slow",
          className
        )}
      >
        <div className="bg-secondary p-4 rounded-t-lg flex items-center space-x-3">
          <Icon className={cn("w-6 h-6", iconColor)} aria-hidden="true" />
          <h3 className="text-primary font-semibold text-lg">{title}</h3>
        </div>
        <div className="p-4">
          <p className="text-muted-foreground text-sm leading-relaxed">{description}</p>
        </div>
      </Card>
    </Wrapper>
  );
}
