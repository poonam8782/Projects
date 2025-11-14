// components/NeuraLanding.tsx
"use client";

import React, { useEffect } from "react";

/* Window globals for runtime libs */
declare global {
  interface Window {
    lucide?: any;
    gsap?: any;
    ScrollTrigger?: any;
    Lenis?: any;
    confetti?: any;
  }
}

/* Helper to dynamically load external scripts */
const loadScript = (src: string, attrs: Record<string, string> = {}) =>
  new Promise<void>((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) return resolve();
    const s = document.createElement("script");
    s.src = src;
    s.async = true;
    Object.entries(attrs).forEach(([k, v]) => s.setAttribute(k, v));
    s.onload = () => resolve();
    s.onerror = () => reject(new Error(`Failed to load ${src}`));
    document.body.appendChild(s);
  });

export default function NeuraLanding(): JSX.Element {
  useEffect(() => {
    // -----------------------------
    // 1) Remove extension attributes & observe for later additions
    // -----------------------------
    const extAttrs = [
      "__processed_8904d2ca-e9b1-4f14-adc9-0c0d177d55d7__",
      "bis_register",
      "data-new-gr-c-s-check-loaded",
      "data-gr-ext-installed",
    ];

    const removeExtAttrs = () => {
      [document.documentElement, document.body].forEach((el) => {
        if (!el) return;
        extAttrs.forEach((a) => {
          try {
            if ((el as Element).hasAttribute && (el as Element).hasAttribute(a)) {
              (el as Element).removeAttribute(a);
            }
          } catch {
            // ignore
          }
        });
      });
    };

    removeExtAttrs();

    const mo = new MutationObserver((mutations) => {
      let removed = false;
      for (const m of mutations) {
        if (m.type === "attributes") {
          const target = m.target as Element;
          extAttrs.forEach((a) => {
            if (target.hasAttribute && target.hasAttribute(a)) {
              target.removeAttribute(a);
              removed = true;
            }
          });
        }
      }
      if (removed) removeExtAttrs();
    });

    mo.observe(document.documentElement, { attributes: true, subtree: true });
    mo.observe(document.body, { attributes: true, subtree: true });

    // -----------------------------
    // 2) Load Lucide + runtime libs after mount
    // -----------------------------
    loadScript("https://unpkg.com/lucide@latest")
      .then(() => {
        if (window.lucide && typeof window.lucide.createIcons === "function") {
          window.lucide.createIcons();
        }
      })
      .catch(() => { /* ignore */ });

    Promise.all([
      loadScript("https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"),
      loadScript("https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/ScrollTrigger.min.js"),
      loadScript("https://cdn.jsdelivr.net/npm/lenis@1.0.29/dist/lenis.min.js"),
      loadScript("https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"),
    ])
      .then(() => {
        const gsap = (window as any).gsap;
        const ScrollTrigger = (window as any).ScrollTrigger;

        try {
          if (gsap && ScrollTrigger) gsap.registerPlugin(ScrollTrigger);

          // Preloader timeline
          const tlLoader = gsap.timeline();
          tlLoader.to(".loader-bar", {
            height: "100%",
            duration: 0.8,
            stagger: 0.1,
            ease: "power4.inOut",
          })
            .to("#loader h1", { opacity: 0, duration: 0.2 })
            .to("#loader", { y: "-100%", duration: 0.8, ease: "power4.inOut" }, "-=0.2")
            .from(".hero-text", {
              y: 200,
              opacity: 0,
              rotate: 5,
              stagger: 0.1,
              duration: 1,
              ease: "power3.out",
            }, "-=0.5")
            .from([".hero-sub", ".hero-sub-cta", ".hero-sub-proof"], {
              y: 50,
              opacity: 0,
              stagger: 0.1,
              duration: 0.8,
              ease: "power3.out",
            }, "-=0.5");

          // Lenis smooth scroll
          if ((window as any).Lenis) {
            const lenis = new (window as any).Lenis({
              duration: 1.2,
              easing: (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
              direction: "vertical",
              gestureDirection: "vertical",
              smooth: true,
              mouseMultiplier: 1,
              smoothTouch: false,
              touchMultiplier: 2,
            });
            function raf(time: number) {
              lenis.raf(time);
              requestAnimationFrame(raf);
            }
            requestAnimationFrame(raf);
          }

          // Floating parallax
          gsap.to(".float-anim", {
            y: -100,
            scrollTrigger: { trigger: "body", start: "top top", end: "bottom top", scrub: 1 },
          });
          gsap.to(".float-anim-reverse", {
            y: 150,
            rotate: 45,
            scrollTrigger: { trigger: "body", start: "top top", end: "bottom top", scrub: 1.5 },
          });

          // Manifesto reveal
          document.querySelectorAll<HTMLElement>(".manifesto-text").forEach((text) => {
            gsap.to(text, {
              opacity: 1,
              scrollTrigger: { trigger: text, start: "top 80%", end: "top 40%", scrub: true },
            });
          });

          // Stats card hover
          document.querySelectorAll<HTMLElement>(".stats-card").forEach((card) => {
            const onMove = (e: MouseEvent) => {
              const rect = card.getBoundingClientRect();
              const x = e.clientX - rect.left;
              const y = e.clientY - rect.top;
              gsap.to(card, { x: (x - rect.width / 2) / 5, y: (y - rect.height / 2) / 5, duration: 0.3, ease: "power2.out" });
            };
            const onLeave = () => gsap.to(card, { x: 0, y: 0, duration: 0.5, ease: "elastic.out(1, 0.5)" });
            card.addEventListener("mousemove", onMove);
            card.addEventListener("mouseleave", onLeave);
          });

          // Stagger entries
          gsap.from(".service-card", { y: 100, opacity: 0, rotate: 5, stagger: 0.1, duration: 0.8, ease: "back.out(1.7)", scrollTrigger: { trigger: ".service-card", start: "top 85%" } });
          gsap.from(".pricing-card", { y: 100, opacity: 0, stagger: 0.1, duration: 0.8, ease: "back.out(1.7)", scrollTrigger: { trigger: ".pricing-card", start: "top 85%" } });
          gsap.from(".testimonial-card", { y: 100, opacity: 0, stagger: 0.1, duration: 0.8, ease: "back.out(1.7)", scrollTrigger: { trigger: ".testimonial-card", start: "top 85%" } });

          // Cursor logic
          const cursor = document.getElementById("cursor");
          document.addEventListener("mousemove", (e) => {
            if (cursor) {
              cursor.style.left = e.clientX + "px";
              cursor.style.top = e.clientY + "px";
            }
          });

          const links = document.querySelectorAll<HTMLElement>("a, button, .service-card, .pricing-card, .testimonial-card");
          links.forEach((link) => {
            link.addEventListener("mouseenter", () => {
              if (!cursor) return;
              cursor.style.width = "60px";
              cursor.style.height = "60px";
              cursor.style.backgroundColor = "#A3FF00";
              cursor.style.mixBlendMode = "exclusion";
            });
            link.addEventListener("mouseleave", () => {
              if (!cursor) return;
              cursor.style.width = "24px";
              cursor.style.height = "24px";
              cursor.style.backgroundColor = "#0f0f0f";
              cursor.style.mixBlendMode = "difference";
            });
          });

          // Confetti button
          const dangerBtn = document.getElementById("danger-btn");
          if (dangerBtn) {
            dangerBtn.addEventListener("click", (ev) => {
              ev.preventDefault();
              gsap.to("body", { x: -10, duration: 0.1, yoyo: true, repeat: 5 });

              const duration = 2000;
              const end = Date.now() + duration;
              (function frame() {
                if (window.confetti) {
                  window.confetti({ particleCount: 5, angle: 60, spread: 55, origin: { x: 0 }, colors: ["#FF4D00", "#A3FF00", "#9D00FF"] });
                  window.confetti({ particleCount: 5, angle: 120, spread: 55, origin: { x: 1 }, colors: ["#FF4D00", "#A3FF00", "#9D00FF"] });
                }
                if (Date.now() < end) requestAnimationFrame(frame);
              })();

              const href = (dangerBtn as HTMLAnchorElement).getAttribute("href");
              setTimeout(() => { if (href) window.location.href = href; }, 1000);
            });
          }
        } catch (e) {
          // ignore animation init errors
        }
      })
      .catch((err) => {
        // ignore script load errors
      });

    // cleanup on unmount
    return () => {
      mo.disconnect();
      // scripts and listeners will be cleaned up on page unload; if needed we could remove listeners here
    };
  }, []);

  // Root uses suppressHydrationWarning to mute benign extension-caused warnings
  return (
    <div suppressHydrationWarning className="font-body">
      {/* Grain Overlay */}
      <div className="grain" />

      {/* Custom Cursor */}
      <div id="cursor" />

      {/* Loader */}
      <div id="loader">
        <div className="flex gap-2 h-32 items-end">
          <div className="loader-bar" />
          <div className="loader-bar" />
          <div className="loader-bar" />
          <div className="loader-bar" />
          <div className="loader-bar" />
        </div>
        <h1 className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-neo-bg font-display font-bold text-6xl mix-blend-exclusion">LOADING</h1>
      </div>

      {/* Navigation */}
      <nav className="fixed top-0 left-0 w-full flex justify-between items-center p-4 md:p-8 z-50 pointer-events-none mix-blend-difference text-[#FFFAE5]">
        <div className="pointer-events-auto group cursor-none">
          <a href="/" className="font-heavy text-3xl md:text-4xl tracking-tighter hover:text-neo-accent transition-colors">NEURA.</a>
        </div>
        <div className="pointer-events-auto hidden md:flex gap-8 font-bold text-lg items-center">
          <a href="#features" className="hover:line-through decoration-4 decoration-neo-accent">Features</a>
          <a href="#pricing" className="hover:line-through decoration-4 decoration-neo-accent">Pricing</a>
          <a href="/blog" className="hover:line-through decoration-4 decoration-neo-accent">Blog</a>
          <a href="/login" className="hover:line-through decoration-4 decoration-neo-accent">Sign in</a>
          <a href="/signup" className="border-2 border-[#FFFAE5] px-6 py-2 hover:bg-[#FFFAE5] hover:text-black transition-all duration-300 shadow-none hover:shadow-[4px_4px_0px_0px_#A3FF00]">Get Started</a>
        </div>
        <div className="pointer-events-auto md:hidden border-2 border-[#FFFAE5] p-2">
          <i data-lucide="menu" className="w-6 h-6" />
        </div>
      </nav>

      <main id="smooth-wrapper">
        <div id="smooth-content">

          {/* HERO SECTION */}
          <section className="relative min-h-screen flex flex-col justify-center items-center pt-20 overflow-hidden border-b-4 border-black bg-neo-bg">
            <div className="absolute top-1/4 left-10 w-24 h-24 md:w-48 md:h-48 border-4 border-black bg-neo-main rounded-full shadow-neo float-anim opacity-80" />
            <div className="absolute bottom-1/4 right-10 w-32 h-32 md:w-64 md:h-64 border-4 border-black bg-neo-purple rotate-12 shadow-neo float-anim-reverse z-10" />
            <div className="absolute top-1/2 right-1/4 w-16 h-16 border-4 border-black bg-neo-accent shadow-neo-sm" />

            <div className="relative z-20 text-center mix-blend-normal">
              <div className="overflow-hidden">
                <h1 className="hero-text font-display font-bold text-[12vw] leading-[0.85] tracking-tighter text-black">YOUR BRAIN,</h1>
              </div>
              <div className="overflow-hidden">
                <h1 className="hero-text font-display font-bold text-[12vw] leading-[0.85] tracking-tighter text-neo-blue text-outline">BUT SMARTER.</h1>
              </div>
              <div className="overflow-hidden">
                <h1 className="hero-text font-display font-bold text-[12vw] leading-[0.85] tracking-tighter text-black">AI NOTES.</h1>
              </div>

              <p className="hero-sub mt-8 font-body text-xl md:text-2xl font-bold max-w-lg mx-auto bg-white border-4 border-black p-4 shadow-neo">
                The AI note-taking app that actually gets you. Stop searching, start knowing.
              </p>

              <div className="hero-sub-cta flex flex-col sm:flex-row gap-4 mt-8 justify-center">
                <a href="/signup" className="border-4 border-black bg-neo-main text-white font-heavy text-xl px-8 py-4 shadow-neo hover:shadow-neo-active hover:-translate-y-1 hover:-translate-x-1 active:translate-y-0 active:translate-x-0 transition-all">Get Started Free</a>
                <a href="#pricing" className="border-4 border-black bg-neo-accent text-black font-heavy text-xl px-8 py-4 shadow-neo hover:shadow-neo-active hover:-translate-y-1 hover:-translate-x-1 active:translate-y-0 active:translate-x-0 transition-all">View Pricing</a>
              </div>

              <div className="mt-16 hero-sub-proof">
                <p className="font-mono text-sm uppercase text-gray-700">TRUSTED BY TEAMS AT</p>
                <div className="flex justify-center gap-8 md:gap-12 mt-4 grayscale opacity-60 items-center">
                  <i data-lucide="box" className="w-10 h-10" />
                  <i data-lucide="aperture" className="w-10 h-10" />
                  <i data-lucide="codesandbox" className="w-10 h-10" />
                  <i data-lucide="database" className="w-10 h-10" />
                  <i data-lucide="figma" className="w-10 h-10" />
                </div>
              </div>
            </div>
          </section>

          {/* MARQUEE */}
          <div className="w-full bg-neo-accent border-b-4 border-black py-6 overflow-hidden flex items-center transform -skew-y-2 origin-left mt-[-4px] z-30 relative">
            <div className="marquee-container font-heavy text-4xl md:text-6xl text-black uppercase tracking-widest">
              <div className="marquee-content">
                /// AI-POWERED SUMMARIES /// INSTANT SEARCH /// NEVER LOSE A THOUGHT /// CONNECT YOUR IDEAS /// VOICE-TO-TEXT ///
                /// AI-POWERED SUMMARIES /// INSTANT SEARCH /// NEVER LOSE A THOUGHT /// CONNECT YOUR IDEAS /// VOICE-TO-TEXT ///
              </div>
            </div>
          </div>

          {/* PROBLEM -> SOLUTION */}
          <section id="problem" className="relative py-32 px-4 md:px-12 bg-neo-black text-neo-bg overflow-hidden">
            <div className="absolute top-0 right-0 w-1/2 h-full bg-neo-purple opacity-20 clip-polygon" />
            <div className="container mx-auto grid grid-cols-1 md:grid-cols-12 gap-12 relative z-10">
              <div className="md:col-span-6">
                <div className="sticky top-32">
                  <h2 className="font-heavy text-6xl md:text-8xl mb-6 text-neo-accent">THE<br />PROBLEM</h2>
                  <div className="w-full h-4 bg-neo-main border-2 border-white shadow-[4px_4px_0px_0px_#ffffff]" />
                </div>
              </div>

              <div className="md:col-span-6 space-y-12 text-xl md:text-3xl font-bold leading-snug">
                <p className="manifesto-text opacity-20">
                  You have 1,000 notes across 10 apps. Finding one specific thought is a nightmare. <span className="text-neo-main bg-white px-2">Your brain dump is a black hole.</span>
                </p>
                <p className="manifesto-text opacity-20">
                  Transcribing audio notes and meeting recordings is a soul-crushing manual task. Good ideas from verbal brainstorms are lost forever.
                </p>
                <p className="manifesto-text opacity-20">
                  All your notes are disconnected. You can't see the patterns, connect the dots, or build on previous knowledge. It's just a digital junk drawer.
                </p>

                <div className="grid grid-cols-2 gap-4 mt-12">
                  <div className="bg-neo-bg text-black border-4 border-white p-6 shadow-[8px_8px_0px_0px_#A3FF00] hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all cursor-none stats-card">
                    <h3 className="font-heavy text-4xl">INSTANT</h3>
                    <p className="text-sm font-mono uppercase mt-2">Search Across All Notes</p>
                  </div>
                  <div className="bg-neo-main text-white border-4 border-white p-6 shadow-[8px_8px_0px_0px_#9D00FF] hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all cursor-none stats-card">
                    <h3 className="font-heavy text-4xl">AUTO</h3>
                    <p className="text-sm font-mono uppercase mt-2">Transcription & Tagging</p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* FEATURES */}
          <section id="features" className="py-20 bg-neo-blue border-t-4 border-black">
            <div className="container mx-auto px-4">
              <div className="flex justify-between items-end mb-16 border-b-4 border-black pb-4">
                <h2 className="font-heavy text-5xl md:text-7xl text-white">POWERFUL FEATURES</h2>
                <i data-lucide="wrench" className="w-12 h-12 text-neo-accent stroke-[3] animate-spin-slow" />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8 auto-rows-[300px]">
                <div className="service-card bg-neo-bg border-4 border-black shadow-neo p-8 flex flex-col justify-between md:col-span-2 hover:bg-neo-accent transition-colors duration-300 group">
                  <div className="flex justify-between items-start">
                    <h3 className="font-heavy text-4xl uppercase">SMART<br />SEARCH</h3>
                    <i data-lucide="search" className="w-10 h-10 stroke-[3] group-hover:rotate-12 transition-transform duration-500" />
                  </div>
                  <p className="font-bold text-lg mt-4 border-t-2 border-black pt-4">Ask questions in plain English. Find concepts, not just keywords.</p>
                </div>

                <div className="service-card bg-neo-main border-4 border-black shadow-neo p-8 flex flex-col justify-center items-center text-center rotate-1 hover:rotate-0 transition-transform duration-300">
                  <i data-lucide="mic" className="w-20 h-20 text-black fill-white mb-4 stroke-[3]" />
                  <h3 className="font-display font-bold text-2xl text-white">VOICE-TO-TEXT<br />TRANSCRIPTION</h3>
                </div>

                <div className="service-card bg-neo-black border-4 border-black shadow-neo p-8 flex flex-col justify-between text-white hover:shadow-none hover:translate-x-[8px] hover:translate-y-[8px] transition-all">
                  <h3 className="font-heavy text-3xl text-neo-purple">AI-POWERED<br />SUMMARIES</h3>
                  <p className="text-gray-400">Get the gist of long notes and articles in seconds.</p>
                </div>

                <div className="service-card bg-white border-4 border-black shadow-neo p-8 md:col-span-2 relative group flex flex-col justify-between hover:bg-neo-purple transition-colors duration-300">
                  <div className="flex justify-between items-start">
                    <h3 className="font-heavy text-4xl uppercase text-neo-purple group-hover:text-white">KNOWLEDGE<br />GRAPH</h3>
                    <i data-lucide="git-merge" className="w-10 h-10 stroke-[3] text-neo-purple group-hover:text-white group-hover:rotate-90 transition-transform duration-500" />
                  </div>
                  <p className="font-bold text-lg mt-4 border-t-2 border-black pt-4 group-hover:text-white group-hover:border-white">Visually connect your notes and discover hidden patterns.</p>
                </div>
              </div>
            </div>
          </section>

          {/* PRICING */}
          <section id="pricing" className="py-20 bg-neo-bg border-t-4 border-black">
            <div className="container mx-auto px-4">
              <div className="flex justify-between items-end mb-16 border-b-4 border-black pb-4">
                <h2 className="font-heavy text-5xl md:text-7xl text-black">PLANS THAT MAKE SENSE</h2>
                <i data-lucide="dollar-sign" className="w-12 h-12 text-neo-main stroke-[3]" />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                <div className="pricing-card bg-white border-4 border-black shadow-neo p-8 flex flex-col hover:-translate-y-2 transition-transform">
                  <h3 className="font-heavy text-3xl uppercase text-neo-purple">Hobby</h3>
                  <p className="font-display text-5xl font-bold my-4">$0<span className="text-lg font-body">/mo</span></p>
                  <p className="font-body text-gray-700">For casual note-takers and curious minds.</p>
                  <ul className="font-body space-y-2 mt-6 mb-8 flex-grow">
                    <li className="flex items-center gap-2"><i data-lucide="check" className="w-5 h-5 text-neo-accent stroke-[3]" /> 500 AI Credits</li>
                    <li className="flex items-center gap-2"><i data-lucide="check" className="w-5 h-5 text-neo-accent stroke-[3]" /> Basic Search</li>
                    <li className="flex items-center gap-2"><i data-lucide="check" className="w-5 h-5 text-neo-accent stroke-[3]" /> 3 Integrations</li>
                  </ul>
                  <a href="/signup" className="w-full text-center border-4 border-black bg-neo-accent text-black font-heavy text-xl px-8 py-4 shadow-neo hover:shadow-neo-active hover:-translate-y-1 hover:-translate-x-1 active:translate-y-0 active:translate-x-0 transition-all">Start for Free</a>
                </div>

                <div className="pricing-card bg-neo-black text-white border-4 border-neo-accent shadow-[8px_8px_0px_0px_#A3FF00] p-8 flex flex-col relative scale-105">
                  <div className="absolute top-0 -translate-y-1/2 left-1/2 -translate-x-1/2 bg-neo-accent text-black font-heavy text-sm uppercase px-4 py-1 border-2 border-black">MOST POPULAR</div>
                  <h3 className="font-heavy text-3xl uppercase text-neo-accent">Pro</h3>
                  <p className="font-display text-5xl font-bold my-4">$10<span className="text-lg font-body">/mo</span></p>
                  <p className="font-body text-gray-300">For power users and professionals.</p>
                  <ul className="font-body space-y-2 mt-6 mb-8 flex-grow">
                    <li className="flex items-center gap-2"><i data-lucide="check" className="w-5 h-5 text-neo-accent stroke-[3]" /> 5000 AI Credits</li>
                    <li className="flex items-center gap-2"><i data-lucide="check" className="w-5 h-5 text-neo-accent stroke-[3]" /> Smart Search</li>
                    <li className="flex items-center gap-2"><i data-lucide="check" className="w-5 h-5 text-neo-accent stroke-[3]" /> Unlimited Integrations</li>
                    <li className="flex items-center gap-2"><i data-lucide="check" className="w-5 h-5 text-neo-accent stroke-[3]" /> Voice Transcription</li>
                  </ul>
                  <a href="/signup?plan=pro" className="w-full text-center border-4 border-neo-accent bg-neo-accent text-black font-heavy text-xl px-8 py-4 shadow-neo hover:shadow-neo-active hover:-translate-y-1 hover:-translate-x-1 active:translate-y-0 active:translate-x-0 transition-all">Get Started</a>
                </div>

                <div className="pricing-card bg-white border-4 border-black shadow-neo p-8 flex flex-col hover:-translate-y-2 transition-transform">
                  <h3 className="font-heavy text-3xl uppercase text-neo-main">Team</h3>
                  <p className="font-display text-5xl font-bold my-4">Custom</p>
                  <p className="font-body text-gray-700">For teams that need to collaborate.</p>
                  <ul className="font-body space-y-2 mt-6 mb-8 flex-grow">
                    <li className="flex items-center gap-2"><i data-lucide="check" className="w-5 h-5 text-neo-accent stroke-[3]" /> Unlimited AI Credits</li>
                    <li className="flex items-center gap-2"><i data-lucide="check" className="w-5 h-5 text-neo-accent stroke-[3]" /> Shared Workspaces</li>
                    <li className="flex items-center gap-2"><i data-lucide="check" className="w-5 h-5 text-neo-accent stroke-[3]" /> Priority Support</li>
                  </ul>
                  <a href="/contact" className="w-full text-center border-4 border-black bg-neo-main text-white font-heavy text-xl px-8 py-4 shadow-neo hover:shadow-neo-active hover:-translate-y-1 hover:-translate-x-1 active:translate-y-0 active:translate-x-0 transition-all">Contact Sales</a>
                </div>
              </div>
            </div>
          </section>

          {/* TESTIMONIALS */}
          <section id="testimonials" className="relative py-32 px-4 md:px-12 bg-neo-black text-neo-bg overflow-hidden">
            <div className="absolute top-0 left-0 w-1/2 h-full bg-neo-main opacity-20 clip-polygon-reverse" />
            <div className="container mx-auto relative z-10">
              <div className="text-center mb-16">
                <h2 className="font-heavy text-6xl md:text-8xl text-neo-accent">WHAT USERS SAY</h2>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                <div className="testimonial-card bg-neo-bg text-black border-4 border-white p-8 shadow-[8px_8px_0px_0px_#FFFFFF] transform hover:rotate-1 transition-transform">
                  <p className="font-body text-xl font-medium leading-snug">"Neura is the first app that feels like an extension of my brain. The smart search is actual magic."</p>
                  <div className="flex items-center mt-6">
                    <div className="w-12 h-12 bg-neo-purple border-2 border-black rounded-full" />
                    <div className="ml-4">
                      <p className="font-heavy text-lg">Sarah L.</p>
                      <p className="font-mono text-sm">Product Manager</p>
                    </div>
                  </div>
                </div>

                <div className="testimonial-card bg-neo-bg text-black border-4 border-white p-8 shadow-[8px_8px_0px_0px_#FFFFFF] transform md:mt-12 hover:-rotate-2 transition-transform">
                  <p className="font-body text-xl font-medium leading-snug">"The voice transcription saved my team hours. We dump our meeting recordings and get perfect notes."</p>
                  <div className="flex items-center mt-6">
                    <div className="w-12 h-12 bg-neo-main border-2 border-black rounded-full" />
                    <div className="ml-4">
                      <p className="font-heavy text-lg">Mike T.</p>
                      <p className="font-mono text-sm">Engineering Lead</p>
                    </div>
                  </div>
                </div>

                <div className="testimonial-card bg-neo-bg text-black border-4 border-white p-8 shadow-[8px_8px_0px_0px_#FFFFFF] transform hover:rotate-1 transition-transform">
                  <p className="font-body text-xl font-medium leading-snug">"I finally connected a random thought from 2021 with a new idea from yesterday. Mind blown."</p>
                  <div className="flex items-center mt-6">
                    <div className="w-12 h-12 bg-neo-accent border-2 border-black rounded-full" />
                    <div className="ml-4">
                      <p className="font-heavy text-lg">Alex C.</p>
                      <p className="font-mono text-sm">Writer</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* FINAL CTA */}
          <section className="py-32 bg-neo-bg flex flex-col items-center justify-center text-center overflow-hidden relative border-t-4 border-black">
            <div className="absolute inset-0 grid grid-cols-[repeat(20,1fr)] grid-rows-[repeat(20,1fr)] opacity-10 pointer-events-none" />
            <h2 className="font-display font-bold text-4xl md:text-6xl mb-12 z-10">STOP THINKING. START DOING.</h2>

            <a href="/signup" id="danger-btn" className="relative group">
              <div className="absolute inset-0 bg-black translate-x-4 translate-y-4 transition-transform group-hover:translate-x-6 group-hover:translate-y-6" />
              <div className="relative border-4 border-black bg-neo-main px-12 py-8 font-heavy text-4xl md:text-6xl text-white hover:-translate-y-2 hover:-translate-x-2 active:translate-x-2 active:translate-y-2 transition-transform duration-100 flex items-center gap-4">
                <i data-lucide="sparkles" className="w-12 h-12 stroke-[3]" />
                GET STARTED FREE
              </div>
            </a>

            <div id="confetti-container" className="absolute inset-0 pointer-events-none overflow-hidden" />
          </section>

          {/* FOOTER */}
          <footer className="bg-black text-neo-bg pt-20 pb-10 px-4 border-t-8 border-neo-accent">
            <div className="container mx-auto">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-12">
                <div>
                  <h1 className="font-heavy text-4xl text-neo-bg select-none mb-4">NEURA.</h1>
                  <div className="flex space-x-4">
                    <a href="#" className="text-neo-bg/50 hover:text-neo-accent"><i data-lucide="twitter" className="w-5 h-5" /></a>
                    <a href="#" className="text-neo-bg/50 hover:text-neo-accent"><i data-lucide="github" className="w-5 h-5" /></a>
                    <a href="#" className="text-neo-bg/50 hover:text-neo-accent"><i data-lucide="linkedin" className="w-5 h-5" /></a>
                  </div>
                </div>

                <div className="col-span-1">
                  <h3 className="font-heavy text-lg uppercase text-neo-accent mb-4">Product</h3>
                  <ul className="space-y-3 font-body">
                    <li><a href="#features" className="hover:text-neo-main">Features</a></li>
                    <li><a href="#pricing" className="hover:text-neo-main">Pricing</a></li>
                    <li><a href="/changelog" className="hover:text-neo-main">Changelog</a></li>
                    <li><a href="/integrations" className="hover:text-neo-main">Integrations</a></li>
                  </ul>
                </div>

                <div className="col-span-1">
                  <h3 className="font-heavy text-lg uppercase text-neo-accent mb-4">Company</h3>
                  <ul className="space-y-3 font-body">
                    <li><a href="/about" className="hover:text-neo-main">About</a></li>
                    <li><a href="/blog" className="hover:text-neo-main">Blog</a></li>
                    <li><a href="/careers" className="hover:text-neo-main">Careers</a></li>
                    <li><a href="/contact" className="hover:text-neo-main">Contact</a></li>
                  </ul>
                </div>

                <div className="col-span-1">
                  <h3 className="font-heavy text-lg uppercase text-neo-accent mb-4">Resources</h3>
                  <ul className="space-y-3 font-body">
                    <li><a href="/docs" className="hover:text-neo-main">Docs</a></li>
                    <li><a href="/docs/api" className="hover:text-neo-main">API Reference</a></li>
                    <li><a href="/support" className="hover:text-neo-main">Support</a></li>
                    <li><a href="https://status.notesense.com" target="_blank" className="hover:text-neo-main" rel="noreferrer">Status</a></li>
                  </ul>
                </div>

                <div className="col-span-1">
                  <h3 className="font-heavy text-lg uppercase text-neo-accent mb-4">Legal</h3>
                  <ul className="space-y-3 font-body">
                    <li><a href="/privacy" className="hover:text-neo-main">Privacy</a></li>
                    <li><a href="/terms" className="hover:text-neo-main">Terms</a></li>
                    <li><a href="/security" className="hover:text-neo-main">Security</a></li>
                  </ul>
                </div>
              </div>

              <div className="mt-20 pt-10 border-t-2 border-white/20 flex flex-col md:flex-row justify-between items-center text-sm font-mono text-white/50">
                <p>© 2025 NEURA. ALL RIGHTS RESERVED.</p>
                <p className="mt-4 md:mt-0">MADE WITH <span className="text-neo-main">♥</span> AND TOO MUCH CAFFEINE.</p>
              </div>
            </div>
          </footer>

        </div>
      </main>
    </div>
  );
}
