"use client";

import React, { useEffect, useRef, useState, useMemo, useCallback } from "react";
import Link from "next/link";
import { motion, useReducedMotion, useMotionValue, useSpring, useTransform, MotionValue, useScroll, useAnimation, AnimatePresence, useInView } from "framer-motion";
import { Zap, Rocket, Sparkles, Code, Brain, Shield, ChevronRight, ArrowUpRight, Star, Cpu, Layers } from "lucide-react";
import { Button } from "@neura/ui";
import { cn } from "@/lib/utils";
import TopNav from "@/components/TopNav";
import Footer from "@/components/Footer";
import { pricingPlans } from "@/lib/pricing";

// Premium color palette
const colors = {
  primary: "#ff8800",
  secondary: "#ff6600",
  accent: "#ff4400",
  glow: "#ffaa00",
  dark: "#0a0a0a",
  darker: "#050505",
};

// Ultra-smooth spring configurations for 240fps feel
const smoothSpring = {
  type: "spring",
  stiffness: 200,
  damping: 30,
  mass: 0.8,
};

const silkySpring = {
  type: "spring",
  stiffness: 150,
  damping: 25,
  mass: 0.5,
};

// Premium Liquid Gradient Background
const LiquidGradient = () => {
  const time = useMotionValue(0);
  
  useEffect(() => {
    const interval = setInterval(() => {
      time.set(time.get() + 0.01);
    }, 16); // 60fps base for smooth gradient
    return () => clearInterval(interval);
  }, []);

  const gradientX = useTransform(time, (t) => Math.sin(t) * 50 + 50);
  const gradientY = useTransform(time, (t) => Math.cos(t * 0.7) * 50 + 50);

  return (
    <motion.div 
      className="fixed inset-0 opacity-30"
      style={{
        background: `radial-gradient(circle at ${gradientX}% ${gradientY}%, ${colors.glow}22 0%, transparent 50%), 
                     radial-gradient(circle at ${gradientY}% ${gradientX}%, ${colors.primary}22 0%, transparent 50%),
                     linear-gradient(180deg, ${colors.dark} 0%, ${colors.darker} 100%)`,
      }}
    />
  );
};

// Premium Glow Orb
const GlowOrb = ({ delay = 0, size = 400, color = colors.primary }) => {
  return (
    <motion.div
      className="absolute pointer-events-none"
      initial={{ opacity: 0 }}
      animate={{
        opacity: [0.3, 0.6, 0.3],
        scale: [1, 1.2, 1],
      }}
      transition={{
        duration: 8,
        delay,
        repeat: Infinity,
        ease: "easeInOut",
      }}
      style={{
        width: size,
        height: size,
        background: `radial-gradient(circle, ${color}44 0%, transparent 70%)`,
        filter: "blur(40px)",
      }}
    />
  );
};

// Smooth Parallax Mouse Effect
const useMouseParallax = (factor = 1) => {
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  
  const springConfig = { damping: 25, stiffness: 150, mass: 0.5 };
  const x = useSpring(mouseX, springConfig);
  const y = useSpring(mouseY, springConfig);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const rect = document.body.getBoundingClientRect();
      const centerX = window.innerWidth / 2;
      const centerY = window.innerHeight / 2;
      const moveX = (e.clientX - centerX) / centerX;
      const moveY = (e.clientY - centerY) / centerY;
      
      mouseX.set(moveX * factor);
      mouseY.set(moveY * factor);
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, [factor]);

  return { x, y };
};

// Premium Glass Card with Depth
const GlassCard = ({ children, className, delay = 0 }: { 
  children: React.ReactNode; 
  className?: string;
  delay?: number;
}) => {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });
  const { x, y } = useMouseParallax(10);

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 40, rotateX: -15 }}
      animate={isInView ? { 
        opacity: 1, 
        y: 0, 
        rotateX: 0,
      } : {}}
      transition={{
        ...smoothSpring,
        delay,
      }}
      style={{
        x,
        y,
      }}
      whileHover={{
        scale: 1.02,
        transition: silkySpring,
      }}
      className={cn(
        "relative group",
        className
      )}
    >
      {/* Premium glass effect layers */}
      <div className="absolute inset-0 bg-gradient-to-br from-white/[0.08] to-white/[0.02] rounded-3xl" />
      <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/[0.03] to-transparent rounded-3xl" />
      <div className="absolute inset-0 rounded-3xl shadow-2xl shadow-black/20" />
      
      {/* Animated border gradient */}
      <div className="absolute inset-0 rounded-3xl">
        <div className="absolute inset-0 rounded-3xl p-[1px]">
          <motion.div
            className="absolute inset-0 rounded-3xl opacity-50"
            style={{
              background: `conic-gradient(from 0deg, transparent, ${colors.primary}, transparent, ${colors.secondary}, transparent)`,
            }}
            animate={{
              rotate: 360,
            }}
            transition={{
              duration: 20,
              repeat: Infinity,
              ease: "linear",
            }}
          />
        </div>
      </div>

      {/* Content */}
      <div className="relative backdrop-blur-xl bg-black/40 border border-white/[0.08] rounded-3xl p-8 overflow-hidden">
        {/* Subtle inner glow */}
        <motion.div
          className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-700"
          style={{
            background: `radial-gradient(circle at 50% 50%, ${colors.primary}11 0%, transparent 70%)`,
          }}
        />
        {children}
      </div>
    </motion.div>
  );
};

// Premium Text Reveal Animation
const TextReveal = ({ text, className, delay = 0 }: { 
  text: string; 
  className?: string;
  delay?: number;
}) => {
  const words = text.split(" ");
  
  return (
    <span className={className}>
      {words.map((word, i) => (
        <motion.span
          key={i}
          className="inline-block mr-[0.25em]"
          initial={{ opacity: 0, y: 20, filter: "blur(10px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{
            ...silkySpring,
            delay: delay + i * 0.03,
          }}
        >
          {word}
        </motion.span>
      ))}
    </span>
  );
};

// Premium Magnetic Button
const MagneticButton = ({ children, className, href }: {
  children: React.ReactNode;
  className?: string;
  href: string;
}) => {
  const ref = useRef<HTMLDivElement>(null);
  const [isHovered, setIsHovered] = useState(false);
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  
  const springX = useSpring(x, { stiffness: 150, damping: 15, mass: 0.1 });
  const springY = useSpring(y, { stiffness: 150, damping: 15, mass: 0.1 });

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!ref.current || !isHovered) return;
    const rect = ref.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    x.set((e.clientX - centerX) * 0.2);
    y.set((e.clientY - centerY) * 0.2);
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    x.set(0);
    y.set(0);
  };

  return (
    <Link href={href}>
      <motion.div
        ref={ref}
        onMouseMove={handleMouseMove}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={handleMouseLeave}
        style={{ x: springX, y: springY }}
        className="relative inline-block"
      >
        <motion.div
          className={cn(
            "relative px-8 py-4 rounded-full font-medium overflow-hidden",
            className
          )}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.98 }}
          transition={silkySpring}
        >
          {/* Premium gradient background */}
          <motion.div
            className="absolute inset-0"
            style={{
              background: `linear-gradient(135deg, ${colors.primary} 0%, ${colors.secondary} 50%, ${colors.accent} 100%)`,
              backgroundSize: "200% 200%",
            }}
            animate={isHovered ? {
              backgroundPosition: ["0% 0%", "100% 100%"],
            } : {}}
            transition={{ duration: 0.5 }}
          />
          
          {/* Shimmer effect */}
          <motion.div
            className="absolute inset-0 opacity-0"
            animate={isHovered ? {
              opacity: [0, 1, 0],
              x: ["-100%", "100%"],
            } : {}}
            transition={{ duration: 0.6 }}
            style={{
              background: "linear-gradient(105deg, transparent 40%, rgba(255,255,255,0.7) 50%, transparent 60%)",
            }}
          />
          
          <span className="relative z-10 flex items-center text-white">
            {children}
          </span>
        </motion.div>
      </motion.div>
    </Link>
  );
};

// Premium Feature Card
const PremiumFeatureCard = ({ icon: Icon, title, description, delay = 0 }) => {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-50px" });
  
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 50, scale: 0.9 }}
      animate={isInView ? { 
        opacity: 1, 
        y: 0, 
        scale: 1 
      } : {}}
      transition={{
        ...smoothSpring,
        delay,
      }}
    >
      <GlassCard>
        <motion.div
          className="relative z-10"
          whileHover={{ y: -5 }}
          transition={silkySpring}
        >
          {/* Premium icon container */}
          <motion.div
            className="mb-6 inline-block"
            whileHover={{ 
              rotate: [0, -10, 10, -10, 0],
              scale: 1.1,
            }}
            transition={{ duration: 0.5 }}
          >
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-br from-[#ff8800] to-[#ff4400] rounded-2xl blur-xl opacity-60" />
              <div className="relative bg-gradient-to-br from-[#ff8800] to-[#ff6600] p-4 rounded-2xl">
                <Icon className="w-6 h-6 text-white" />
              </div>
            </div>
          </motion.div>
          
          <h3 className="text-xl font-semibold text-white mb-3">
            <TextReveal text={title} delay={delay + 0.1} />
          </h3>
          <p className="text-gray-400 leading-relaxed">{description}</p>
        </motion.div>
      </GlassCard>
    </motion.div>
  );
};

// Premium Hero Section
const HeroSection = () => {
  const { x: mouseX, y: mouseY } = useMouseParallax(20);
  const heroRef = useRef(null);
  const isInView = useInView(heroRef, { once: true });

  return (
    <section ref={heroRef} className="relative min-h-screen flex items-center justify-center px-6 py-20 overflow-hidden">
      {/* Animated background orbs */}
      <motion.div style={{ x: mouseX, y: mouseY }} className="absolute inset-0">
        <GlowOrb delay={0} size={600} color={colors.primary} />
        <GlowOrb delay={2} size={400} color={colors.secondary} />
        <GlowOrb delay={4} size={500} color={colors.accent} />
      </motion.div>

      <div className="relative z-10 max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          {/* Left: Premium content */}
          <motion.div
            initial={{ opacity: 0, x: -60 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{
              ...smoothSpring,
              delay: 0.2,
            }}
          >
            <motion.h1 
              className="text-5xl md:text-7xl font-bold mb-8"
              initial={{ opacity: 0, y: 30 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{
                ...smoothSpring,
                delay: 0.3,
              }}
            >
              <span className="block text-white mb-2">
                <TextReveal text="Transform" delay={0.4} />
              </span>
              <span className="block text-white mb-2">
                <TextReveal text="Documents Into" delay={0.5} />
              </span>
              <motion.span 
                className="block bg-gradient-to-r from-[#ff8800] via-[#ff6600] to-[#ff4400] bg-clip-text text-transparent"
                animate={{
                  backgroundPosition: ["0% 50%", "100% 50%", "0% 50%"],
                }}
                transition={{
                  duration: 5,
                  repeat: Infinity,
                  ease: "linear",
                }}
                style={{
                  backgroundSize: "200% auto",
                }}
              >
                <TextReveal text="Structured Learning" delay={0.6} />
              </motion.span>
            </motion.h1>
            
            <motion.p 
              className="text-lg md:text-xl text-gray-400 mb-10 leading-relaxed"
              initial={{ opacity: 0 }}
              animate={isInView ? { opacity: 1 } : {}}
              transition={{
                ...smoothSpring,
                delay: 0.7,
              }}
            >
              AI-powered notes, mindmaps, flashcards, and intelligent chat — 
              all from your documents with enterprise-grade quality.
            </motion.p>
            
            <motion.div 
              className="flex flex-wrap gap-4"
              initial={{ opacity: 0, y: 20 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{
                ...smoothSpring,
                delay: 0.9,
              }}
            >
              <MagneticButton href="/signup" className="bg-gradient-to-r from-[#ff8800] to-[#ff6600]">
                <Sparkles className="mr-2 w-5 h-5" />
                Get Started Free
                <ArrowUpRight className="ml-2 w-5 h-5" />
              </MagneticButton>
              
              <MagneticButton href="#features" className="bg-white/10 backdrop-blur-sm border border-white/20">
                Learn More
                <ChevronRight className="ml-2 w-5 h-5" />
              </MagneticButton>
            </motion.div>
          </motion.div>

          {/* Right: Premium 3D Visual */}
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={isInView ? { opacity: 1, scale: 1 } : {}}
            transition={{
              ...smoothSpring,
              delay: 0.5,
            }}
            className="relative h-[500px] flex items-center justify-center"
          >
            <motion.div
              style={{ x: mouseX, y: mouseY }}
              className="relative w-full h-full"
            >
              {/* Premium glass sphere */}
              <motion.div
                className="absolute inset-0 flex items-center justify-center"
                animate={{
                  rotateY: [0, 360],
                }}
                transition={{
                  duration: 20,
                  repeat: Infinity,
                  ease: "linear",
                }}
              >
                <div className="relative w-80 h-80">
                  {/* Outer glow */}
                  <motion.div
                    className="absolute inset-0 rounded-full"
                    style={{
                      background: `radial-gradient(circle, ${colors.primary}44 0%, transparent 70%)`,
                      filter: "blur(30px)",
                    }}
                    animate={{
                      scale: [1, 1.2, 1],
                    }}
                    transition={{
                      duration: 4,
                      repeat: Infinity,
                      ease: "easeInOut",
                    }}
                  />
                  
                  {/* Glass sphere */}
                  <div className="absolute inset-0 rounded-full bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-md border border-white/20 overflow-hidden">
                    {/* Inner rotating gradient */}
                    <motion.div
                      className="absolute inset-0"
                      style={{
                        background: `conic-gradient(from 0deg, ${colors.primary}44, ${colors.secondary}44, ${colors.accent}44, ${colors.primary}44)`,
                      }}
                      animate={{
                        rotate: [0, 360],
                      }}
                      transition={{
                        duration: 10,
                        repeat: Infinity,
                        ease: "linear",
                      }}
                    />
                    
                    {/* Center icon */}
                    <motion.div
                      className="absolute inset-0 flex items-center justify-center"
                      animate={{
                        scale: [1, 1.1, 1],
                      }}
                      transition={{
                        duration: 3,
                        repeat: Infinity,
                        ease: "easeInOut",
                      }}
                    >
                      <Brain className="w-24 h-24 text-white/80" />
                    </motion.div>
                  </div>
                  
                  {/* Orbiting particles */}
                  {[...Array(8)].map((_, i) => (
                    <motion.div
                      key={i}
                      className="absolute w-2 h-2 bg-gradient-to-br from-[#ff8800] to-[#ff6600] rounded-full"
                      style={{
                        top: "50%",
                        left: "50%",
                        boxShadow: `0 0 20px ${colors.primary}`,
                      }}
                      animate={{
                        x: [
                          Math.cos((i * Math.PI * 2) / 8) * 180,
                          Math.cos(((i * Math.PI * 2) / 8) + Math.PI * 2) * 180,
                        ],
                        y: [
                          Math.sin((i * Math.PI * 2) / 8) * 180,
                          Math.sin(((i * Math.PI * 2) / 8) + Math.PI * 2) * 180,
                        ],
                      }}
                      transition={{
                        duration: 10 + i * 0.5,
                        repeat: Infinity,
                        ease: "linear",
                      }}
                    />
                  ))}
                </div>
              </motion.div>
            </motion.div>
          </motion.div>
        </div>
      </div>
    </section>
  );
};

// Main Component
export default function Home() {
  const prefersReducedMotion = useReducedMotion();

  return (
    <main className="min-h-screen relative overflow-x-hidden bg-gradient-to-b from-[#0a0a0a] to-[#050505]">
      <LiquidGradient />
      <TopNav />
      <HeroSection />

      {/* Features Section */}
      <section id="features" className="relative z-10 max-w-7xl mx-auto px-6 py-24">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={smoothSpring}
          className="text-center mb-16"
        >
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">
            <TextReveal text="Powerful Features for Modern Learning" />
          </h2>
          <p className="text-gray-400 max-w-2xl mx-auto text-lg">
            Everything you need to transform your documents into actionable knowledge
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <PremiumFeatureCard
            icon={Sparkles}
            title="AI-Powered Notes"
            description="Generate structured notes automatically from your documents with advanced AI that learns your style."
            delay={0}
          />
          <PremiumFeatureCard
            icon={Zap}
            title="Smart Flashcards"
            description="Create flashcards with spaced repetition and adaptive learning algorithms for maximum retention."
            delay={0.1}
          />
          <PremiumFeatureCard
            icon={Rocket}
            title="Visual Mindmaps"
            description="Transform complex topics into beautiful, interactive visual mindmaps with AI-powered connections."
            delay={0.2}
          />
          <PremiumFeatureCard
            icon={Code}
            title="Code Intelligence"
            description="Analyze and understand code snippets with syntax highlighting and AI explanations."
            delay={0.3}
          />
          <PremiumFeatureCard
            icon={Shield}
            title="Secure & Private"
            description="Your data is encrypted end-to-end with enterprise-grade security standards."
            delay={0.4}
          />
          <PremiumFeatureCard
            icon={Cpu}
            title="Realtime Sync"
            description="Access your knowledge base anywhere with instant cloud synchronization."
            delay={0.5}
          />
        </div>
      </section>

      {/* Premium Pricing Section */}
      <section id="pricing" className="relative z-10 max-w-7xl mx-auto px-6 py-24">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={smoothSpring}
          className="text-center mb-16"
        >
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">
            <TextReveal text="Choose Your Plan" />
          </h2>
          <p className="text-gray-400 max-w-2xl mx-auto text-lg">
            Start free, upgrade anytime. No credit card required.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {pricingPlans.map((plan, index) => (
            <motion.div
              key={plan.name}
              initial={{ opacity: 0, y: 50 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{
                ...smoothSpring,
                delay: index * 0.1,
              }}
              className="relative"
            >
              {plan.highlighted && (
                <motion.div
                  className="absolute -top-4 left-1/2 -translate-x-1/2 bg-gradient-to-r from-[#ff8800] to-[#ff6600] text-white px-6 py-2 rounded-full text-sm font-semibold z-10"
                  animate={{
                    y: [-2, 2, -2],
                  }}
                  transition={{
                    duration: 3,
                    repeat: Infinity,
                    ease: "easeInOut",
                  }}
                >
                  MOST POPULAR
                </motion.div>
              )}
              <GlassCard delay={index * 0.1}>
                <div className="relative z-10">
                  <h3 className="text-2xl font-bold text-white mb-2">{plan.name}</h3>
                  <div className="mb-6">
                    <span className="text-4xl font-bold text-white">{plan.price}</span>
                    <span className="text-gray-400">/{plan.period}</span>
                  </div>
                  <p className="text-[#ff8800] font-semibold mb-8">{plan.credits}</p>
                  <ul className="space-y-4 mb-8">
                    {plan.features.map((feature, i) => (
                      <motion.li
                        key={i}
                        className="flex items-center text-gray-300"
                        initial={{ opacity: 0, x: -20 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                        transition={{
                          ...silkySpring,
                          delay: index * 0.1 + i * 0.05,
                        }}
                      >
                        <Star className="mr-3 text-[#ff8800] flex-shrink-0" size={16} />
                        {feature}
                      </motion.li>
                    ))}
                  </ul>
                  <MagneticButton 
                    href={plan.ctaHref}
                    className={plan.highlighted ? "" : "bg-white/10 backdrop-blur-sm border border-white/20"}
                  >
                    {plan.ctaText}
                  </MagneticButton>
                </div>
              </GlassCard>
            </motion.div>
          ))}
        </div>
      </section>

      <Footer />
    </main>
  );
}