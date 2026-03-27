Bashira-Intelligence Frontend Implementation Plan
This plan details the architecture and implementation strategy for the high-end, intelligent Next.js frontend for Bashira-Intelligence based on the PRD and custom aesthetic instructions.

Proposed Changes

1. Global Setup and Design System
Framework: Initialize Next.js 15 (App Router) with TypeScript and Tailwind CSS.
Dependencies: Install framer-motion for UI animations, three + @react-three/fiber + @react-three/drei for 3D interactions, react-use-gesture for cursor mapping, zustand for state management, and lucide-react for premium icons.
Color Palette:
Primary: Royal Gold (#C8A96A)
Secondary: Burnt Sand (#A67C52)
Hover/Depth: Copper Bronze (#8C6239)
Backgrounds: Dark textured charcoal (#1A1A1A) / Glassmorphism dark mode (#0A0A1E)
Typography:
Headings: Custom font stack (General Sans / Canela style)
Body: Suisse Intl / Manrope style
Accent: IBM Plex Sans Arabic
[NEW] frontend/package.json
Initialize the workspace with all required dependencies.

[NEW] frontend/src/app/globals.css
Configure the CSS variables for the color palette, typography font-faces, and glassmorphism themes.

[NEW] frontend/tailwind.config.ts
Map design system colors and custom typography to Tailwind classes.

1. Splash Screen
Concept: Cinematic, dark luxury interface with slow, precise animations.
Features: A deep charcoal background featuring a thin animated gold line that forms an eye motif. The "Basir" logo and "Intelligence Platform" subtitle fade in smoothly. No fast animations.
[NEW] frontend/src/components/splash/SplashScreen.tsx
A full-screen component using Framer Motion to sequentially orchestrate the initial loading sequence.

2. Landing Page
Concept: "Autonomous Quarry System", showing a top-down quarry site where machines operate via AI interactions.
Features: Interactive WebGL layer mapped to cursor movement (AI command signal). Machines pause and highlight on hover, while gold lines display decision paths.
Other Elements:
Main company branding: "AL Tasnim".
Footer credit: "Made with Sequelstring AI".
Multi-language shifting text: Continuously fading between "Basir" and its Arabic equivalent (بصير).
Status indicator: "System Online" on top right.
CTA Button: "Enter Basir" leading to the authentication flow.
[NEW] frontend/src/app/page.tsx
Orchestrates the Landing Page, holding the top navigation, branding footer, and changing text.

[NEW] frontend/src/components/landing/QuarrySimulation.tsx
A 3D simulation built using @react-three/fiber that renders the intelligent quarry interaction logic.

1. Authentication (Login Page)
Concept: "Authentication Assembly Line".
Features:
Left panel: High-end, minimal login form.
Right panel: Horizontal 3D conveyor processing unit visualization.
Interaction Map: Conveyor starts on input focus, scanner activates on email typing, secure chamber engages on password input. Passes golden output on success.
[NEW] frontend/src/app/login/page.tsx
The login interface with state hooked up to the visual conveyor line.

[NEW] frontend/src/components/auth/AssemblyLine.tsx
Three.js horizontal conveyor sequence mapped to input interactions.

1. Main Dashboard (Query & Analytics)
Concept: "Drill Core Loop" with an intelligent query-slide mechanism.
Features:
Standard view: Product name and center query bar.
On submit: Window smoothly transits left. The right side displays the "Drill Core Loop" processing animation.
Loader logic: Minimal rotating text strings ("Processing Intelligence...", "Analyzing Operational Data...", "Generating Visual Insights...").
Result view (as per PRD): Displaying response reasoning, table data, and Next.js/Recharts generated dynamic visualizations based on user input.
[NEW] frontend/src/app/dashboard/page.tsx
Dashboard container tracking application layout states (centered vs. left-split).

[NEW] frontend/src/components/dashboard/DrillCoreLoop.tsx
Smooth, minimal WebGL drill animation loop showing continuous data extraction logic.

[NEW] frontend/src/components/dashboard/QueryBar.tsx
The central command input field that triggers the sliding layout transition.

Verification Plan
Automated Tests
Type checking (tsc --noEmit).
Ensuring npm run dev successfully compiles the application.
Linters (npm run lint).
Manual Verification
Visual inspection of the Splash Screen mounting sequence.
Testing the react-use-gesture interactivity on the landing page's Quarry Simulation.
Reviewing the Assembly Line component's reaction to keyboard typing state.
Confirming the seamless loop of the Drill Core animation and the slide-left transition on the dashboard.
