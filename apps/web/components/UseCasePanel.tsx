"use client";

import React from "react";
import { motion } from "framer-motion";
import { Card, Badge } from "@neura/ui";
import { cn } from "@/lib/utils";
import Image from "next/image";

interface UseCasePanelProps {
  title: string;
  description?: string;
  imageSrc?: string;
  imageAlt?: string;
  badge?: string;
  badgeColor?: string;
  panelColor: string;
  className?: string;
  disableMotion?: boolean;
}

export default function UseCasePanel({
  title,
  description,
  imageSrc,
  imageAlt,
  badge,
  badgeColor = "bg-primary/20 text-primary",
  panelColor,
  className,
  disableMotion = false,
}: UseCasePanelProps) {
  const Wrapper: React.ElementType = disableMotion ? "div" : motion.div;
  const motionProps = disableMotion
    ? { }
    : {
        initial: { opacity: 0, x: -30 },
        whileInView: { opacity: 1, x: 0 },
        viewport: { once: true, margin: "-50px" },
        transition: { duration: 0.5, ease: "easeOut" },
      };

  return (
    <Wrapper {...motionProps}>
      <Card
        className={cn(
          "shadow-card hover:shadow-hover transition-shadow duration-slow",
          panelColor,
          className
        )}
      >
        <div className="p-6 flex flex-col md:flex-row items-center gap-6">
          <div className="flex-1">
            <h3 className="text-xl md:text-2xl font-bold mb-2">{title}</h3>
            {description && (
              <p className="text-muted-foreground text-sm mb-4">{description}</p>
            )}
            {badge && (
              <Badge className={cn("text-xs font-medium px-3 py-1 rounded-full", badgeColor)}>
                {badge}
              </Badge>
            )}
          </div>
          <div className="flex-shrink-0 w-full md:w-1/3">
            {imageSrc ? (
              <Image
                src={imageSrc}
                alt={imageAlt || "Illustration"}
                width={300}
                height={200}
                className="rounded-md shadow-md w-full h-auto object-cover"
                loading="lazy"
              />
            ) : (
              <div className="w-full h-[200px] rounded-md" style={{
                background: "var(--landing-gradient)",
              }} aria-hidden />
            )}
          </div>
        </div>
      </Card>
    </Wrapper>
  );
}
