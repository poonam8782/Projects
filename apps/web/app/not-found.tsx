"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { Button } from "@neura/ui";

export default function NotFound() {
  const reduceMotion = useReducedMotion();
  const ease = [0.22, 0.9, 0.36, 1] as const;

  return (
    <main
      className="min-h-screen flex flex-col items-center justify-center px-6 py-20 relative overflow-hidden"
      style={{ background: "var(--landing-gradient)" }}
    >
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease }}
        className="text-center max-w-2xl"
      >
        <h1 className="text-9xl md:text-[12rem] font-black text-landing-dark mb-4 leading-none">404</h1>
        <h2 className="text-3xl md:text-4xl font-bold text-landing-dark mb-4">Oops! Page Not Found</h2>
        <p className="text-lg text-landing-muted mb-8 max-w-md mx-auto">
          It seems you&apos;ve wandered off the map. Go back to the homepage.
        </p>
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.7, delay: 0.2, ease }}
        >
          <Button
            asChild
            size="lg"
            variant="default"
            shape="pill"
            className="shadow-landing-card hover:shadow-landing-hover"
          >
            <Link href={{ pathname: "/" }}>Home page</Link>
          </Button>
        </motion.div>
      </motion.div>

      <div className="absolute bottom-8 left-0 right-0 pointer-events-none" aria-hidden="true">
        <div className="marquee-viewport overflow-hidden">
          <div
            className={`marquee-track ${reduceMotion ? "marquee-paused" : ""}`}
            role="presentation"
          >
            <span className="marquee-item">NOT FOUND PAGE NOT FOUND PAGE NOT FOUND PAGE</span>
            <span className="marquee-item" aria-hidden="true">NOT FOUND PAGE NOT FOUND PAGE NOT FOUND PAGE</span>
          </div>
        </div>
      </div>

      <style jsx>{`
        .marquee-viewport {
          width: 100%;
        }

        .marquee-track {
          display: flex;
          gap: 4rem;
          align-items: center;
          width: max-content;
          animation: marquee 18s linear infinite;
        }

        .marquee-paused {
          animation-play-state: paused;
        }

        .marquee-item {
          font-weight: 900;
          font-size: 3.5rem;
          line-height: 1;
          color: rgba(0,0,0,0.05);
          white-space: nowrap;
          padding-right: 4rem;
        }

        @keyframes marquee {
          from {
            transform: translateX(0);
          }
          to {
            transform: translateX(-50%);
          }
        }

        @media (min-width: 768px) {
          .marquee-item {
            font-size: 5rem;
          }
        }

        @media (prefers-reduced-motion: reduce) {
          .marquee-track {
            animation: none;
          }
        }
      `}</style>
    </main>
  );
}
