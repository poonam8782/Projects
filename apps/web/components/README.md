# Components

Application-specific components for the Neura frontend. These components are distinct from the shared UI components in `@neura/ui` and contain business logic specific to the Neura application.

## Directory Structure

- `/FileUploader.tsx` - Drag-and-drop file upload component with validation and progress tracking
- `/DocumentChat.tsx` - RAG chat interface with SSE streaming and provenance panel
- `/Flashcards.tsx` - Flashcard practice component with 3D flip animation and SM-2 spaced repetition
- Future components will be added in subsequent sprints:
  - `/MindmapViewer.tsx` (Sprint 4) - SVG mindmap renderer with zoom/pan and fullscreen support

## Component Guidelines

### When to create components here vs. in `@neura/ui`

- **Use `components/`** for: Application-specific logic, API integration, state management, business rules
- **Use `@neura/ui`** for: Reusable UI primitives, design system components, generic utilities

### Styling conventions

- All components must follow the strict black & white monochrome theme
- Use Tailwind utility classes with custom tokens: `bg-black-ui`, `bg-surface-ui`, `text-text-ui`, `text-muted-ui`, `border-border-ui`
- Import shadcn components from `@neura/ui`: `Button`, `Card`, `Input`, `Label`, `Dialog`
- Use `cn()` utility from `@/lib/utils` for conditional className composition

### Animation guidelines

- Use Framer Motion for complex animations (available via `@neura/ui` dependency)
- Keep animations subtle and fast (0.2-0.3s duration)
- Use `AnimatePresence` for enter/exit animations
- Common patterns:
  - Fade in: `initial={{ opacity: 0 }}`, `animate={{ opacity: 1 }}`
  - Slide up: `initial={{ y: 20 }}`, `animate={{ y: 0 }}`
  - Scale: `initial={{ scale: 0.95 }}`, `animate={{ scale: 1 }}`

### Accessibility requirements

- All interactive elements must be keyboard accessible
- Use semantic HTML (`button`, `label`, `input`, etc.)
- Provide `aria-label` for icon-only buttons
- Use `aria-live` for dynamic content updates (e.g., streaming chat)
- Ensure focus indicators are visible (configured globally in theme)

### Component structure template

```typescript
'use client'; // If component uses hooks or browser APIs

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Button, Card } from '@neura/ui';
import { cn } from '@/lib/utils';

interface MyComponentProps {
  // Props definition
}

export default function MyComponent({ ...props }: MyComponentProps) {
  // Component logic
  return (
    <Card className="bg-surface-ui border-border-ui">
      {/* Component UI */}
    </Card>
  );
}
```

## Testing (Sprint 7)

- Unit tests will be added using Jest and React Testing Library
- E2E tests will be added using Playwright
- Test files should be colocated: `FileUploader.test.tsx`

## Integration with backend

- API calls should use the `api.ts` service (to be created in Sprint 1 Phase 3)
- Authentication tokens are automatically included via Supabase client
- Error handling should display user-friendly messages in the UI

## References

- Shared UI components: `../../packages/ui/README.md`
- Tailwind config: `../tailwind.config.ts`
- Theme documentation: `../README.md#theme`

## DocumentChat Component

Features:

- Real-time chat interface with SSE token streaming
- Conversation history management (stateless, sent with each request)
- Provenance panel showing source chunks with similarity scores
- Message list with user/model distinction (right/left alignment)
- Auto-scroll to latest message
- Loading states during streaming
- Error handling with retry capability
- Accessibility: aria-live for streaming tokens, keyboard navigation
- Monochrome styling with smooth Framer Motion animations

Usage Example:

```typescript
import DocumentChat from '@/components/DocumentChat';

export default function ChatPage({ documentId }: { documentId: string }) {
  return (
    <div className="p-8">
      <DocumentChat 
        documentId={documentId}
        documentName="report.pdf"
      />
    </div>
  );
}
```

Component Props:

- `documentId` (required): UUID of the document to chat with
- `documentName` (optional): Document filename for display in header
- `className` (optional): Additional CSS classes

SSE Event Flow:

1. User sends message → added to conversation history
2. "provenance" event arrives → source chunks displayed in collapsible panel
3. "token" events arrive → tokens accumulated and displayed in real-time with aria-live
4. "done" event arrives → complete message added to history, streaming stops
5. "error" event arrives → error displayed with retry option

Rationale: Documenting the DocumentChat component helps developers understand its features, usage patterns, and integration points. The examples provide clear patterns for using the component in pages.

## MindmapViewer Component

Interactive SVG mindmap viewer that provides zoom, pan, center, reset, fullscreen, and download capabilities while enforcing a defense-in-depth sanitization model (server-side bleach, client-side DOMPurify).

**Integration**:

- Integrated into the dashboard via a Dialog modal.
- Users click "Generate Mindmap" on a document card to trigger backend generation.
- After generation completes, the modal opens automatically with MindmapViewer.
- Viewer fetches the SVG via signed download URL, sanitizes again with DOMPurify, and renders via `dangerouslySetInnerHTML` (safe post-sanitization).
- Node count badge displayed in viewer header; zoom/pan controls provided by `react-zoom-pan-pinch`.
- Fullscreen toggle allows immersive exploration; download button saves the SVG locally.

**Usage in Dashboard**:

```tsx
<MindmapViewer
  downloadUrl={mindmap.downloadUrl}
  documentName={mindmap.filename}
  showControls
  allowFullscreen
  className="h-[600px]"
/>
```

**State Handling**:

- Dashboard stores `{ downloadUrl, filename, nodeCount }` when generation completes.
- Dialog manages open/close state; viewer is only rendered when data is available.

**Security Model**:

- Server sanitizes SVG with strict bleach allowlist and CSS rules.
- Client re-sanitizes with DOMPurify restricting tags/attrs (`FORBID_TAGS` & `FORBID_ATTR`).
- Rendering occurs inside a controlled container using `dangerouslySetInnerHTML` after sanitization (industry standard pattern).

**Rationale**: This integration description ensures future contributors understand how the viewer attaches to the generation workflow and maintains security guarantees.

## Flashcards Component

**Flashcards Features**:

- 3D card flip animation using Framer Motion (rotateY transform with perspective)
- Question display on front, answer reveal on click/keyboard
- Quality rating buttons (1-5 scale) for SM-2 spaced repetition:
  - 1: Hard (incorrect but familiar)
  - 2: Difficult (incorrect but easy after seeing)
  - 3: Good (correct with effort)
  - 4: Easy (correct with hesitation)
  - 5: Perfect (immediate recall)
- Progress tracking: Progress bar showing reviewed/remaining count, percentage completion
- Next review schedule display: Shows interval and next review date after rating
- Session completion: Shows summary when all flashcards reviewed with restart option
- Loading states: Spinner during review submission
- Error handling: Error messages with retry capability
- Accessibility: aria-labels, keyboard navigation (Space/Enter to flip, Tab through rating buttons)
- Monochrome styling: Strict black & white theme with smooth animations

**Usage Example**:

```typescript
import Flashcards from '@/components/Flashcards';
import { FlashcardResponse } from '@/lib/types/document';

function PracticePage({ flashcards }: { flashcards: FlashcardResponse[] }) {
  const handleComplete = () => {
    console.log('Practice session complete!');
  };

  return (
    <div className="p-8">
      <Flashcards 
        flashcards={flashcards}
        onComplete={handleComplete}
      />
    </div>
  );
}
```

**Component Props**:

- `flashcards` (required): Array of FlashcardResponse objects to practice (typically fetched from API with due cards)
- `onComplete` (optional): Callback invoked when all flashcards are reviewed
- `onReviewComplete` (optional): Callback invoked after each review with flashcard and quality rating
- `className` (optional): Additional CSS classes

**Interaction Flow**:

1. Component displays first flashcard showing question (front side)
2. User clicks card or presses Space/Enter to flip and reveal answer (back side)
3. User selects quality rating (1-5) based on recall difficulty
4. Component calls `/flashcards/review` API with flashcard_id and quality
5. Backend updates SM-2 schedule (efactor, repetitions, interval, next_review) and returns next due flashcard
6. Component shows success toast with interval message ("Review again in 6 days")
7. Component displays next flashcard from response, resets to question side
8. Repeat until no more due flashcards (next_flashcard is null)
9. Show completion screen with session summary and restart option

**SM-2 Integration**:

- Quality ratings (1-5) map to SM-2 algorithm's quality scale (0-5, but 0 is rarely used in practice)
- Backend calculates updated efactor, repetitions, interval, and next_review based on quality
- Component displays the interval message from backend ("Review again in X days")
- Progress tracking shows how many cards remain in the current session
- The component doesn't manage SM-2 logic - it delegates to the backend API

**3D Flip Animation Details**:

- Container has `perspective: 1000px` for 3D depth effect
- Card wrapper has `transformStyle: 'preserve-3d'` to enable 3D transforms on children
- Front and back sides are absolutely positioned with `backface-visibility: hidden`
- Back side is pre-rotated 180deg so it appears when card flips
- Framer Motion animates `rotateY` from 0deg (question) to 180deg (answer)
- Smooth 0.6s easeInOut transition creates realistic flip effect

**Rationale**: Documenting the Flashcards component helps developers understand its features, SM-2 integration, and interaction flow. The examples provide clear patterns for using the component in practice pages. The 3D flip animation documentation explains the implementation approach.

## Footer Component

Purpose: Dark landing page footer providing logo/wordmark, navigation links, newsletter subscription form, social icons, and copyright.

Features:
- Dark gradient/background (`bg-landing-footer`, #111214) matching landing aesthetic
- Large wordmark "Neura" with hero subtitle tagline reused for brand consistency
- 3-column responsive layout (Logo+Tagline / Company & Legal / Newsletter) → 1-column on mobile
- Newsletter form with email validation (regex) and toast feedback (success/error)
- Placeholder submission (1s simulated delay) with TODO for API integration (Mailchimp/ConvertKit)
- Social icons (LinkedIn, Instagram) with hover color transition to `landing-orange`
- Copyright line with dynamic year
- Scroll-triggered staggered animations using Framer Motion (`whileInView`, `viewport={{ once: true }}`)
- Accessible semantic `<footer>` element, hidden label via `sr-only`, `aria-label` on icons

Props:
- `className?: string` for optional style overrides

Usage:
```tsx
import Footer from '@/components/Footer';

export default function LandingPage() {
  return (
    <main>
      {/* ... other landing sections ... */}
      <Footer />
    </main>
  );
}
```

Form Handling:
- Validates non-empty and RFC-lite pattern `/^[^@\s]+@[^@\s]+\.[^@\s]+$/`
- Uses `toast.error()` for invalid input; `toast.success()` on simulated success
- Loading state disables input and button; clears email after success
- TODO comments for integrating real newsletter endpoint & replacing placeholder social URLs

Navigation Links:
- Company: Blog (placeholder), Contact us (`/contact`)
- Legal: Terms & Conditions (`/terms`), Privacy Policy (`/privacy`)
- Some routes may not exist yet; safe to leave placeholders (Next.js handles 404)

Social Links:
- LinkedIn & Instagram icons from lucide-react (placeholder URLs) with accessible labels
- TODO: Replace with actual property-defined URLs when available

Accessibility:
- Semantic structure, focusable elements, hidden label for newsletter email, descriptive link labels
- All animations are non-blocking and respect user navigation

Responsive Behavior:
- Mobile: Single column stacking, full-width newsletter form
- Desktop: 3 columns with balanced spacing (`gap-12 md:gap-8`)
- Bottom bar stacks vertically on mobile, horizontal alignment on desktop

Integration Notes:
- Added directly in `page.tsx` (not `layout.tsx`) to scope footer to marketing/landing pages only
- Shares `landing-*` tokens for colors, radii, and shadows with TopNav, FeatureCard, PricingCard, UseCasePanel

## 404 Not Found Page

Purpose: Custom error page rendered for unknown routes, maintaining brand consistency and providing a clear return path.

Features:
- Gradient background (`var(--landing-gradient)`) matching hero section
- Large numeric display "404" with bold typography for immediate recognition
- Headline "Oops! Page Not Found" and explanatory subtitle
- CTA button returning users to home (`/`) using shared Button component (pill shape, animated)
- Decorative repeating low-opacity text banner at bottom for subtle visual interest
- Entrance animations: page content fade + slide, button scale-in, background text delayed fade

Location: `app/not-found.tsx` (auto-routed by Next.js for 404 responses)

Usage: Automatically rendered; no manual import necessary.

Accessibility:
- Proper heading hierarchy (`h1` for code, `h2` for message)
- Clear actionable button; keyboard accessible
- Decorative text marked by low contrast and not interactive

Responsive Behavior:
- Scales typography (`text-9xl` → `md:text-[12rem]`, repeating banner `text-6xl` → `md:text-8xl`)
- Maintains centered layout on all breakpoints

Integration Checklist (Landing Page):
- Components used: TopNav, Hero, Brand Strip, Audience Headline, Feature Grid, Use Case Panels, Pricing, Hero Image, Footer
- Motion: Framer Motion across all sections with `viewport={{ once: true }}` where scroll-triggered
- Reduced Motion: Hero, Cards, Panels, and page-level interactions respect user preference flags
- Design Tokens: Consistent `landing-*` colors, radii (`rounded-landing-*`), shadows (`shadow-landing-card`, `hover`), sizing
- Spacing: Section wrappers align on `px-6 py-16 md:py-24` pattern
- Accessibility: Semantic elements, ARIA labels for icons, focusable links/buttons, consistent heading hierarchy

## Marketing Pages

### /pricing Page

**Purpose**: Dedicated pricing page for SEO and shareability

**Route**: `/pricing`

**Features**:
- Reuses all three PricingCard components from homepage (Free, Basic, Pro)
- Same gradient background as homepage for visual consistency (`var(--landing-gradient)`)
- Hero section with headline and value proposition
- Bottom CTA section encouraging signup
- Includes TopNav and Footer components
- Scroll-triggered animations with reduced motion support

**SEO**: Custom metadata with title, description, OG tags, Twitter card

**Content Strategy**:
- Hero explains value proposition ("Transform documents into structured learning materials...")
- Pricing cards show clear differentiation between plans
- All CTAs point to `/signup`
- Shareable URL for marketing campaigns

**Relationship to Homepage**: Homepage has pricing section at `/#pricing` (anchor link), this page provides standalone URL for SEO and marketing purposes

**Future Enhancements** (TODO comments in file):
- Add annual billing toggle (switch between monthly/yearly pricing with discount)
- Add "Most Popular" badge to highlighted card
- Add comparison table showing feature differences
- Add testimonials or social proof
- Add FAQ accordion section
- Add JSON-LD structured data for rich snippets in search results
- Consider A/B testing different pricing tiers or copy

### /contact Page

**Purpose**: Contact form and waitlist signup for user engagement

**Route**: `/contact`

**Features**:
- Tab navigation to toggle between contact form and waitlist form
- Contact form: Name, email, message fields with validation
- Waitlist form: Email field with validation
- Placeholder submission with TODO for API integration
- Toast notifications for success/error feedback
- Same gradient background as homepage
- Includes TopNav and Footer components
- Tab animations with reduced motion support

**Form Validation**:
- Email regex: `/^[^@\s]+@[^@\s]+\.[^@\s]+$/` (same as login/signup)
- Name: Required, non-empty
- Message: Required, minimum 10 characters
- Loading states prevent multiple submissions

**Form Submission**:
- Placeholder submission (1s delay, success toast)
- TODO comments for API integration options:
  - **Formspree**: Simple form backend, free tier available
  - **Netlify Forms**: Built-in if deployed on Netlify (add `data-netlify="true"` attribute)
  - **Supabase function**: Custom Edge Function to handle form submissions and store in Supabase table
  - **Email service**: SendGrid, Mailgun, or AWS SES for direct email sending
- Store submissions in Supabase tables: `contact_submissions`, `waitlist`

**SEO**: Custom metadata with title, description, OG tags, Twitter card

**Accessibility**: Semantic HTML, proper labels, keyboard navigation, focus styles, `prefersReducedMotion` support

**Future Enhancements** (TODO comments in file):
- Add CAPTCHA or honeypot field to prevent spam
- Add file upload for attachments (e.g., screenshots)
- Add subject/category dropdown for better routing
- Add live chat widget integration (Intercom, Crisp, etc.)
- Add estimated response time indicator
- Add FAQ section to reduce support volume
- Add success page redirect after submission
- Add email confirmation after submission
- Track form submissions in analytics

### Integration Notes

Both marketing pages (`/pricing` and `/contact`) follow the same patterns as homepage and auth pages:
- Use the same design tokens (`landing-*` prefix for colors, radii, shadows)
- Include TopNav and Footer for consistent navigation
- Use Framer Motion for animations with `prefersReducedMotion` support
- Use toast notifications via `sonner` for user feedback
- Have proper SEO metadata for search engines and social sharing

### Navigation Flow

- **Homepage** (`/`) → TopNav links to Features, Benefits, Pricing (anchor links), Contact (page route)
- **Pricing section on homepage** (`/#pricing`) → **Dedicated pricing page** (`/pricing`) for SEO
- **Footer** links to Contact (`/contact`), Blog (`/blog`), Terms (`/terms`), Privacy (`/privacy`)
- **All CTAs on pricing page** point to Signup (`/signup`)
- **Contact page** provides two options: Contact form (for questions) and Waitlist (for early access)

### Form Submission Architecture

**Current State**: All forms use placeholder submission (newsletter in Footer, contact form, waitlist form)

**Future Integration**: Choose one of the following approaches:

**Option 1 (Formspree)**: Simple, no backend code, free tier available, POST to Formspree endpoint

**Option 2 (Netlify Forms)**: Built-in if deployed on Netlify, add `data-netlify="true"` attribute

**Option 3 (Supabase)**: Create Edge Functions for form handling, store in Supabase tables, full control and data ownership (recommended)

**Option 4 (Email service)**: Use SendGrid/Mailgun/AWS SES to send emails directly from frontend

**Recommended Approach**: Supabase Edge Functions + Supabase tables for full control and data ownership

**Database Schema (if using Supabase)**:
- `contact_submissions` table: `id`, `name`, `email`, `message`, `created_at`, `status` (pending/resolved)
- `waitlist` table: `id`, `email`, `created_at`, `notified` (boolean)
- `newsletter_subscribers` table: `id`, `email`, `created_at`, `subscribed` (boolean)

**Security Considerations**: Add rate limiting, CAPTCHA, honeypot fields to prevent spam

### Testing Checklist

**Pricing Page**:
- Verify all three pricing cards render correctly
- Test responsive layout (3-column → 1-column at 768px)
- Verify all CTAs link to `/signup`
- Test scroll-triggered animations
- Verify metadata appears in browser tab and social sharing
- Test keyboard navigation through pricing cards

**Contact Page**:
- Verify tab navigation toggles between contact and waitlist forms
- Test form validation (empty fields, invalid email, short message)
- Test form submission (loading states, success toast, field clearing)
- Verify both forms work independently
- Test responsive layout (forms stack on mobile)
- Verify metadata appears in browser tab and social sharing
- Test keyboard navigation through forms (Tab, Enter, Space)
- Verify `prefersReducedMotion` disables animations

**Both Pages**:
- Verify TopNav and Footer render correctly
- Test navigation links in TopNav and Footer
- Verify gradient background matches homepage
- Test on mobile (375px), tablet (768px), desktop (1440px)
- Verify no console errors or warnings
- Test with screen reader (VoiceOver, NVDA)
- Verify color contrast meets WCAG AA standards

