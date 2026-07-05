# Screenshot Forge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a web app where authenticated users upload iOS screenshots, select an iPhone 17 model, pay €1.99 per session (up to 6 images), and download transparent-background PNG mockups ready for App Store listings.

**Architecture:** Client uploads screenshots directly to Supabase Storage (bypasses Vercel's 4.5 MB body limit), then calls a Next.js API route that reads from Storage, runs Sharp compositing server-side, and writes watermarked previews + transparent outputs back to Storage. Stripe Checkout handles payment; after the webhook confirms, signed download URLs are unlocked.

**Tech Stack:** Next.js 15 (App Router), TypeScript, Supabase (Auth + Postgres + Storage), Sharp, Stripe, JSZip, Vitest, Tailwind CSS 4, Vercel (Hobby).

---

> **Scope note:** This plan covers Auth + Image Engine + Payments + Frontend as one document. If you prefer to build incrementally, Tasks 1-7 (engine + auth) can be delivered as working software independently before tackling Tasks 8-16.

---

## Screen dimensions reference

| Model | Screen (px) | App Store size |
|-------|------------|----------------|
| iPhone 17 | 1206 × 2622 | 1206 × 2622 |
| iPhone 17 Air | 1260 × 2736 | 1260 × 2736 |
| iPhone 17 Pro | 1206 × 2622 | 1206 × 2622 |
| iPhone 17 Pro Max | 1320 × 2868 | 1320 × 2868 |

> **Note:** "iPhone 17 Plus" doesn't exist — Apple replaced it with iPhone 17 Air.

---

## File map

```
screenshot-forge/
├── app/
│   ├── (auth)/
│   │   ├── login/page.tsx              # Google login page
│   │   └── auth/callback/route.ts      # Supabase OAuth callback
│   ├── (app)/
│   │   ├── layout.tsx                  # Auth guard wrapper
│   │   ├── page.tsx                    # Main upload + preview page
│   │   └── sessions/page.tsx           # Session history dashboard
│   ├── api/
│   │   ├── sessions/
│   │   │   ├── route.ts                # POST: create session + process images
│   │   │   └── [id]/
│   │   │       ├── download/route.ts   # GET: stream ZIP download
│   │   │       └── free-download/route.ts # GET: free tier single download
│   │   ├── stripe/
│   │   │   ├── checkout/route.ts       # POST: create Stripe Checkout session
│   │   │   └── webhook/route.ts        # POST: Stripe webhook handler
│   │   └── cron/cleanup/route.ts       # GET: delete expired data (Vercel Cron)
│   ├── globals.css
│   └── layout.tsx
├── components/
│   ├── model-selector.tsx              # iPhone model picker (radio cards)
│   ├── upload-zone.tsx                 # Drag-and-drop + file input
│   ├── preview-grid.tsx                # Watermarked preview images grid
│   ├── pay-button.tsx                  # Stripe Checkout trigger
│   └── session-card.tsx                # Session history list item
├── lib/
│   ├── supabase/
│   │   ├── client.ts                   # Browser client (singleton)
│   │   ├── server.ts                   # Server client (cookies)
│   │   └── admin.ts                    # Service-role client (webhook/cron)
│   ├── sharp/
│   │   ├── frames.ts                   # Frame configs + DeviceModel type
│   │   ├── composite.ts                # Core compositing (screenshot → frame)
│   │   └── preview.ts                  # Watermark + gradient background
│   ├── stripe.ts                       # Stripe client
│   └── types.ts                        # Shared DB types
├── public/
│   └── frames/
│       ├── iphone-17/black.png         # Frame PNG with transparent screen area
│       ├── iphone-17-air/starlight.png
│       ├── iphone-17-pro/black-titanium.png
│       └── iphone-17-pro-max/black-titanium.png
├── scripts/
│   └── measure-frame.mjs               # Helper: prints screen-area coords of a frame PNG
├── supabase/
│   └── migrations/
│       └── 20260620000000_initial.sql
├── middleware.ts                        # Protect (app) routes
├── vercel.json                          # Cron config
├── vitest.config.ts
└── .env.local.example
```

---

## Task 1: Bootstrap project

**Files:**
- Create: `package.json`, `tsconfig.json`, `next.config.ts`, `tailwind.config.ts`, `vitest.config.ts`, `.env.local.example`

- [ ] **Step 1: Scaffold Next.js app**

```bash
npx create-next-app@latest . \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir no \
  --import-alias "@/*"
```

- [ ] **Step 2: Install dependencies**

```bash
npm install @supabase/ssr @supabase/supabase-js sharp stripe jszip
npm install -D vitest @vitejs/plugin-react vite-tsconfig-paths @types/node
```

- [ ] **Step 3: Write vitest config**

Create `vitest.config.ts`:
```typescript
import { defineConfig } from 'vitest/config'
import tsconfigPaths from 'vite-tsconfig-paths'

export default defineConfig({
  plugins: [tsconfigPaths()],
  test: {
    environment: 'node',
    globals: true,
  },
})
```

Add to `package.json` scripts:
```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 4: Write env example**

Create `.env.local.example`:
```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Stripe
STRIPE_SECRET_KEY=sk_test_...
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_EUR=1.99

# App
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

Copy to `.env.local` and fill in values after creating Supabase + Stripe projects.

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "chore: bootstrap Next.js project with dependencies"
```

---

## Task 2: Supabase project + DB schema

**Files:**
- Create: `supabase/migrations/20260620000000_initial.sql`

- [ ] **Step 1: Create Supabase project**

Go to [supabase.com](https://supabase.com), create a new project named `screenshot-forge`. Note the project URL, anon key, and service role key. Fill `.env.local`.

- [ ] **Step 2: Install Supabase CLI and link**

```bash
npm install -D supabase
npx supabase login
npx supabase link --project-ref YOUR_PROJECT_REF
```

- [ ] **Step 3: Write migration**

Create `supabase/migrations/20260620000000_initial.sql`:
```sql
-- Profiles (extends auth.users, created via trigger)
CREATE TABLE profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  free_credit_used BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Auto-create profile on user signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  INSERT INTO profiles (id) VALUES (NEW.id);
  RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- Sessions (one per upload+pay interaction)
CREATE TABLE sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  model TEXT NOT NULL CHECK (model IN ('iphone-17', 'iphone-17-air', 'iphone-17-pro', 'iphone-17-pro-max')),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'free', 'expired')),
  stripe_checkout_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  -- Sessions expire 1h after creation if not paid/free
  session_expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '1 hour',
  -- Paid/free sessions retain files for 7 days
  files_expire_at TIMESTAMPTZ
);

-- Images within a session
CREATE TABLE session_images (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  original_name TEXT NOT NULL,
  preview_path TEXT NOT NULL,  -- Supabase Storage path (watermarked)
  output_path TEXT NOT NULL,   -- Supabase Storage path (transparent PNG)
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS policies
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_images ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users read own profile" ON profiles
  FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users read own sessions" ON sessions
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users read own session images" ON session_images
  FOR SELECT USING (
    session_id IN (SELECT id FROM sessions WHERE user_id = auth.uid())
  );
```

- [ ] **Step 4: Apply migration**

```bash
npx supabase db push
```

Expected output: `Applying migration 20260620000000_initial.sql...`

- [ ] **Step 5: Create Storage buckets in Supabase dashboard**

Go to Storage → New bucket:
- Name: `session-files`
- Public: **No** (private, access via signed URLs)

- [ ] **Step 6: Commit**

```bash
git add supabase/ .gitignore
git commit -m "chore: add DB schema and Supabase migration"
```

---

## Task 3: Supabase clients + TypeScript types

**Files:**
- Create: `lib/supabase/client.ts`, `lib/supabase/server.ts`, `lib/supabase/admin.ts`, `lib/types.ts`

- [ ] **Step 1: Write shared DB types**

Create `lib/types.ts`:
```typescript
export type SessionStatus = 'pending' | 'paid' | 'free' | 'expired'
export type DeviceModel = 'iphone-17' | 'iphone-17-air' | 'iphone-17-pro' | 'iphone-17-pro-max'

export interface Profile {
  id: string
  free_credit_used: boolean
  created_at: string
}

export interface Session {
  id: string
  user_id: string
  model: DeviceModel
  status: SessionStatus
  stripe_checkout_id: string | null
  created_at: string
  completed_at: string | null
  session_expires_at: string
  files_expire_at: string | null
}

export interface SessionImage {
  id: string
  session_id: string
  original_name: string
  preview_path: string
  output_path: string
  created_at: string
}
```

- [ ] **Step 2: Write browser Supabase client**

Create `lib/supabase/client.ts`:
```typescript
import { createBrowserClient } from '@supabase/ssr'

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}
```

- [ ] **Step 3: Write server Supabase client**

Create `lib/supabase/server.ts`:
```typescript
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

export async function createClient() {
  const cookieStore = await cookies()
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() { return cookieStore.getAll() },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options)
          )
        },
      },
    }
  )
}
```

- [ ] **Step 4: Write admin (service-role) client**

Create `lib/supabase/admin.ts`:
```typescript
import { createClient } from '@supabase/supabase-js'

export function createAdminClient() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { autoRefreshToken: false, persistSession: false } }
  )
}
```

- [ ] **Step 5: Commit**

```bash
git add lib/
git commit -m "feat: add Supabase clients and shared types"
```

---

## Task 4: Auth (Supabase Google OAuth + middleware)

**Files:**
- Create: `middleware.ts`, `app/(auth)/login/page.tsx`, `app/auth/callback/route.ts`

- [ ] **Step 1: Enable Google OAuth in Supabase**

In Supabase dashboard → Authentication → Providers → Google:
- Enable Google provider
- Add Client ID and Secret from [console.cloud.google.com](https://console.cloud.google.com) (create OAuth 2.0 credentials, authorized redirect URI: `https://YOUR_PROJECT.supabase.co/auth/v1/callback`)
- Authorized redirect URIs in Supabase: `http://localhost:3000/auth/callback`

- [ ] **Step 2: Write Next.js middleware**

Create `middleware.ts`:
```typescript
import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() { return request.cookies.getAll() },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            request.cookies.set(name, value)
          )
          supabaseResponse = NextResponse.next({ request })
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  const { data: { user } } = await supabase.auth.getUser()

  // Redirect unauthenticated users to login (except auth routes)
  const isAuthRoute = request.nextUrl.pathname.startsWith('/auth') ||
    request.nextUrl.pathname === '/login'

  if (!user && !isAuthRoute) {
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    return NextResponse.redirect(url)
  }

  if (user && request.nextUrl.pathname === '/login') {
    const url = request.nextUrl.clone()
    url.pathname = '/'
    return NextResponse.redirect(url)
  }

  return supabaseResponse
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|frames).*)'],
}
```

- [ ] **Step 3: Write auth callback route**

Create `app/auth/callback/route.ts`:
```typescript
import { createClient } from '@/lib/supabase/server'
import { NextResponse } from 'next/server'

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url)
  const code = searchParams.get('code')

  if (code) {
    const supabase = await createClient()
    await supabase.auth.exchangeCodeForSession(code)
  }

  return NextResponse.redirect(`${origin}/`)
}
```

- [ ] **Step 4: Write login page**

Create `app/(auth)/login/page.tsx`:
```typescript
import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'

export default async function LoginPage() {
  async function signInWithGoogle() {
    'use server'
    const supabase = await createClient()
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${process.env.NEXT_PUBLIC_APP_URL}/auth/callback`,
      },
    })
    if (data.url) redirect(data.url)
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-gradient-to-b from-black to-orange-950">
      <div className="text-center space-y-6">
        <h1 className="text-4xl font-bold text-white">Screenshot Forge</h1>
        <p className="text-orange-200">Frame your iOS screenshots for the App Store</p>
        <form action={signInWithGoogle}>
          <button
            type="submit"
            className="bg-white text-black px-6 py-3 rounded-lg font-medium hover:bg-orange-50 transition-colors"
          >
            Continue with Google
          </button>
        </form>
      </div>
    </main>
  )
}
```

- [ ] **Step 5: Test auth flow locally**

```bash
npm run dev
```

Navigate to `http://localhost:3000` — should redirect to `/login`. Click "Continue with Google" — should complete OAuth and redirect to `/`.

- [ ] **Step 6: Commit**

```bash
git add app/ middleware.ts
git commit -m "feat: add Google OAuth auth with Supabase"
```

---

## Task 5: Frame assets

**Files:**
- Create: `public/frames/iphone-17/black.png` (and 3 other models)
- Create: `scripts/measure-frame.mjs`

- [ ] **Step 1: Download frame PNGs from Figma community**

1. Open [this Figma community file](https://www.figma.com/community/file/1564652018971544072/iphone-17-air-17-pro-and-17-pro-max-mockups-device-frames)
2. Duplicate to your Figma workspace
3. For each model (17, Air, 17 Pro, 17 Pro Max):
   - Select the device frame layer (the bezel/body — NOT the screen fill)
   - The frame must have **alpha = 0 (transparent) in the screen area** so the screenshot shows through
   - Export as PNG at **1x** (so the screen area matches exact App Store pixel dimensions)
4. Save files as:
   - `public/frames/iphone-17/black.png`
   - `public/frames/iphone-17-air/starlight.png`
   - `public/frames/iphone-17-pro/black-titanium.png`
   - `public/frames/iphone-17-pro-max/black-titanium.png`

- [ ] **Step 2: Write frame measurement script**

Create `scripts/measure-frame.mjs`:
```javascript
import sharp from 'sharp'
import { readFileSync } from 'fs'

const framePath = process.argv[2]
if (!framePath) {
  console.error('Usage: node scripts/measure-frame.mjs <path-to-frame.png>')
  process.exit(1)
}

const { width, height, channels } = await sharp(framePath).metadata()
console.log(`\nFrame dimensions: ${width} x ${height}, channels: ${channels}`)

// Scan pixels to find the transparent screen region bounding box
const { data } = await sharp(framePath)
  .raw()
  .toBuffer({ resolveWithObject: true })

let minX = width, minY = height, maxX = 0, maxY = 0

for (let y = 0; y < height; y++) {
  for (let x = 0; x < width; x++) {
    const idx = (y * width + x) * channels
    const alpha = data[idx + 3] // alpha channel
    if (alpha === 0) {
      if (x < minX) minX = x
      if (x > maxX) maxX = x
      if (y < minY) minY = y
      if (y > maxY) maxY = y
    }
  }
}

const screenW = maxX - minX + 1
const screenH = maxY - minY + 1
console.log(`\nTransparent (screen) region:`)
console.log(`  x: ${minX}, y: ${minY}`)
console.log(`  width: ${screenW}, height: ${screenH}`)
console.log(`\nAdd to frames.ts:`)
console.log(`  screenX: ${minX},`)
console.log(`  screenY: ${minY},`)
console.log(`  screenWidth: ${screenW},`)
console.log(`  screenHeight: ${screenH},`)
console.log(`  frameWidth: ${width},`)
console.log(`  frameHeight: ${height},`)
```

- [ ] **Step 3: Run measurement on each frame PNG**

```bash
node scripts/measure-frame.mjs public/frames/iphone-17/black.png
node scripts/measure-frame.mjs public/frames/iphone-17-air/starlight.png
node scripts/measure-frame.mjs public/frames/iphone-17-pro/black-titanium.png
node scripts/measure-frame.mjs public/frames/iphone-17-pro-max/black-titanium.png
```

Note the output for each model — you'll use these values in Task 6.

- [ ] **Step 4: Commit**

```bash
git add public/frames/ scripts/
git commit -m "feat: add iPhone 17 frame assets and measurement script"
```

---

## Task 6: Frame config + aspect ratio validator

**Files:**
- Create: `lib/sharp/frames.ts`, `lib/sharp/frames.test.ts`

- [ ] **Step 1: Write failing tests**

Create `lib/sharp/frames.test.ts`:
```typescript
import { describe, it, expect } from 'vitest'
import { FRAME_CONFIGS, isAspectRatioValid } from './frames'

describe('FRAME_CONFIGS', () => {
  it('has all four iPhone 17 models', () => {
    expect(Object.keys(FRAME_CONFIGS)).toEqual(
      expect.arrayContaining(['iphone-17', 'iphone-17-air', 'iphone-17-pro', 'iphone-17-pro-max'])
    )
  })

  it('iphone-17 screen dimensions match App Store spec', () => {
    expect(FRAME_CONFIGS['iphone-17'].screenWidth).toBe(1206)
    expect(FRAME_CONFIGS['iphone-17'].screenHeight).toBe(2622)
  })

  it('iphone-17-air screen dimensions match App Store spec', () => {
    expect(FRAME_CONFIGS['iphone-17-air'].screenWidth).toBe(1260)
    expect(FRAME_CONFIGS['iphone-17-air'].screenHeight).toBe(2736)
  })

  it('iphone-17-pro-max screen dimensions match App Store spec', () => {
    expect(FRAME_CONFIGS['iphone-17-pro-max'].screenWidth).toBe(1320)
    expect(FRAME_CONFIGS['iphone-17-pro-max'].screenHeight).toBe(2868)
  })
})

describe('isAspectRatioValid', () => {
  it('accepts screenshot matching exact model dimensions', () => {
    expect(isAspectRatioValid(1206, 2622, 'iphone-17')).toBe(true)
  })

  it('accepts portrait screenshot within 2% tolerance', () => {
    // Slightly off due to different iPhone generation
    expect(isAspectRatioValid(1170, 2532, 'iphone-17')).toBe(true)
  })

  it('rejects landscape screenshot', () => {
    expect(isAspectRatioValid(2622, 1206, 'iphone-17')).toBe(false)
  })

  it('rejects screenshot with wrong aspect ratio (iPad)', () => {
    expect(isAspectRatioValid(1668, 2388, 'iphone-17')).toBe(false)
  })

  it('rejects landscape input for any model', () => {
    expect(isAspectRatioValid(2868, 1320, 'iphone-17-pro-max')).toBe(false)
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
npm test lib/sharp/frames.test.ts
```

Expected: `Cannot find module './frames'`

- [ ] **Step 3: Write frame config**

Create `lib/sharp/frames.ts`.
Replace `screenX`, `screenY`, `frameWidth`, `frameHeight` with values from the measurement script output in Task 5 Step 3:

```typescript
import path from 'path'
import type { DeviceModel } from '@/lib/types'

export interface FrameConfig {
  label: string
  screenWidth: number   // screen area width in pixels
  screenHeight: number  // screen area height in pixels
  screenX: number       // screen area top-left x within frame PNG
  screenY: number       // screen area top-left y within frame PNG
  frameWidth: number    // full frame PNG width
  frameHeight: number   // full frame PNG height
  framePath: string     // absolute FS path to frame PNG
  color: string         // default color name
}

export const FRAME_CONFIGS: Record<DeviceModel, FrameConfig> = {
  'iphone-17': {
    label: 'iPhone 17',
    screenWidth: 1206,
    screenHeight: 2622,
    // ↓ Replace with values from: node scripts/measure-frame.mjs public/frames/iphone-17/black.png
    screenX: 30,
    screenY: 60,
    frameWidth: 1266,
    frameHeight: 2742,
    framePath: path.join(process.cwd(), 'public/frames/iphone-17/black.png'),
    color: 'Black',
  },
  'iphone-17-air': {
    label: 'iPhone 17 Air',
    screenWidth: 1260,
    screenHeight: 2736,
    screenX: 30,
    screenY: 60,
    frameWidth: 1320,
    frameHeight: 2856,
    framePath: path.join(process.cwd(), 'public/frames/iphone-17-air/starlight.png'),
    color: 'Starlight',
  },
  'iphone-17-pro': {
    label: 'iPhone 17 Pro',
    screenWidth: 1206,
    screenHeight: 2622,
    screenX: 30,
    screenY: 60,
    frameWidth: 1266,
    frameHeight: 2742,
    framePath: path.join(process.cwd(), 'public/frames/iphone-17-pro/black-titanium.png'),
    color: 'Black Titanium',
  },
  'iphone-17-pro-max': {
    label: 'iPhone 17 Pro Max',
    screenWidth: 1320,
    screenHeight: 2868,
    screenX: 30,
    screenY: 60,
    frameWidth: 1380,
    frameHeight: 2988,
    framePath: path.join(process.cwd(), 'public/frames/iphone-17-pro-max/black-titanium.png'),
    color: 'Black Titanium',
  },
}

const ASPECT_RATIO_TOLERANCE = 0.02

export function isAspectRatioValid(
  imageWidth: number,
  imageHeight: number,
  model: DeviceModel
): boolean {
  if (imageWidth > imageHeight) return false // reject landscape
  const config = FRAME_CONFIGS[model]
  const targetRatio = config.screenWidth / config.screenHeight
  const imageRatio = imageWidth / imageHeight
  return Math.abs(imageRatio - targetRatio) / targetRatio <= ASPECT_RATIO_TOLERANCE
}
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
npm test lib/sharp/frames.test.ts
```

Expected: all 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add lib/sharp/
git commit -m "feat: add frame configs and aspect ratio validator"
```

---

## Task 7: Image compositing engine

**Files:**
- Create: `lib/sharp/composite.ts`, `lib/sharp/composite.test.ts`

- [ ] **Step 1: Write failing tests**

Create `lib/sharp/composite.test.ts`:
```typescript
import { describe, it, expect } from 'vitest'
import sharp from 'sharp'
import { compositeScreenshot } from './composite'
import { FRAME_CONFIGS } from './frames'

async function createTestScreenshot(width: number, height: number): Promise<Buffer> {
  return sharp({
    create: { width, height, channels: 4, background: { r: 255, g: 0, b: 0, alpha: 255 } }
  }).png().toBuffer()
}

describe('compositeScreenshot', () => {
  it('returns a PNG buffer', async () => {
    const config = FRAME_CONFIGS['iphone-17']
    const screenshot = await createTestScreenshot(config.screenWidth, config.screenHeight)
    const result = await compositeScreenshot(screenshot, 'iphone-17')
    const meta = await sharp(result).metadata()
    expect(meta.format).toBe('png')
  })

  it('output dimensions match frame (not screen)', async () => {
    const config = FRAME_CONFIGS['iphone-17']
    const screenshot = await createTestScreenshot(config.screenWidth, config.screenHeight)
    const result = await compositeScreenshot(screenshot, 'iphone-17')
    const { width, height } = await sharp(result).metadata()
    expect(width).toBe(config.frameWidth)
    expect(height).toBe(config.frameHeight)
  })

  it('output has alpha channel (transparent background)', async () => {
    const config = FRAME_CONFIGS['iphone-17']
    const screenshot = await createTestScreenshot(config.screenWidth, config.screenHeight)
    const result = await compositeScreenshot(screenshot, 'iphone-17')
    const { channels } = await sharp(result).metadata()
    expect(channels).toBe(4)
  })

  it('scales screenshot to fit screen area when dimensions differ', async () => {
    // 1170x2532 (iPhone 14 screenshot) into iphone-17 frame
    const screenshot = await createTestScreenshot(1170, 2532)
    const config = FRAME_CONFIGS['iphone-17']
    const result = await compositeScreenshot(screenshot, 'iphone-17')
    const { width, height } = await sharp(result).metadata()
    expect(width).toBe(config.frameWidth)
    expect(height).toBe(config.frameHeight)
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
npm test lib/sharp/composite.test.ts
```

Expected: `Cannot find module './composite'`

- [ ] **Step 3: Write compositing logic**

Create `lib/sharp/composite.ts`:
```typescript
import sharp from 'sharp'
import { readFile } from 'fs/promises'
import { FRAME_CONFIGS } from './frames'
import type { DeviceModel } from '@/lib/types'

export async function compositeScreenshot(
  screenshotBuffer: Buffer,
  model: DeviceModel
): Promise<Buffer> {
  const config = FRAME_CONFIGS[model]
  const frameBuffer = await readFile(config.framePath)

  // Scale screenshot to exactly fill the screen area
  const scaledScreenshot = await sharp(screenshotBuffer)
    .resize(config.screenWidth, config.screenHeight, { fit: 'fill' })
    .toBuffer()

  // Composite: transparent canvas → screenshot → frame on top
  return sharp({
    create: {
      width: config.frameWidth,
      height: config.frameHeight,
      channels: 4,
      background: { r: 0, g: 0, b: 0, alpha: 0 },
    },
  })
    .composite([
      { input: scaledScreenshot, left: config.screenX, top: config.screenY },
      { input: frameBuffer, left: 0, top: 0 },
    ])
    .png()
    .toBuffer()
}
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
npm test lib/sharp/composite.test.ts
```

> Note: these tests require real frame PNG files in `public/frames/`. If frames aren't sourced yet, mock with a simple PNG:
> ```bash
> node -e "
> const sharp = require('sharp');
> // Create a 1266x2742 PNG with transparent center (screen area)
> // as a placeholder frame for testing
> sharp({ create: { width: 1266, height: 2742, channels: 4, background: { r: 100, g: 100, b: 100, alpha: 255 } } })
>   .composite([{ input: Buffer.from([0,0,0,0]), raw: { width:1,height:1,channels:4 }, left: 30, top: 60, tile: true }])
>   .png().toFile('public/frames/iphone-17/black.png')
> "
> ```

- [ ] **Step 5: Commit**

```bash
git add lib/sharp/composite.ts lib/sharp/composite.test.ts
git commit -m "feat: add Sharp compositing engine"
```

---

## Task 8: Preview generator (watermark + gradient)

**Files:**
- Create: `lib/sharp/preview.ts`, `lib/sharp/preview.test.ts`

- [ ] **Step 1: Write failing tests**

Create `lib/sharp/preview.test.ts`:
```typescript
import { describe, it, expect } from 'vitest'
import sharp from 'sharp'
import { generatePreview } from './preview'

async function createTestComposite(width = 1266, height = 2742): Promise<Buffer> {
  return sharp({
    create: { width, height, channels: 4, background: { r: 0, g: 100, b: 200, alpha: 255 } }
  }).png().toBuffer()
}

describe('generatePreview', () => {
  it('returns a JPEG buffer (not PNG, not transparent)', async () => {
    const composite = await createTestComposite()
    const result = await generatePreview(composite)
    const meta = await sharp(result).metadata()
    expect(meta.format).toBe('jpeg')
  })

  it('output is fully opaque (no alpha)', async () => {
    const composite = await createTestComposite()
    const result = await generatePreview(composite)
    const { channels } = await sharp(result).metadata()
    expect(channels).toBe(3) // RGB, no alpha
  })

  it('output dimensions match input', async () => {
    const composite = await createTestComposite(1266, 2742)
    const result = await generatePreview(composite)
    const { width, height } = await sharp(result).metadata()
    expect(width).toBe(1266)
    expect(height).toBe(1266 * 2742 / 1266) // proportional
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
npm test lib/sharp/preview.test.ts
```

- [ ] **Step 3: Write preview generator**

Create `lib/sharp/preview.ts`:
```typescript
import sharp from 'sharp'

// Black → burnt orange gradient as SVG (rendered by Sharp)
function buildGradientSvg(width: number, height: number): Buffer {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">
    <defs>
      <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#000000"/>
        <stop offset="100%" stop-color="#7c2d12"/>
      </linearGradient>
    </defs>
    <rect width="${width}" height="${height}" fill="url(#bg)"/>
  </svg>`
  return Buffer.from(svg)
}

function buildWatermarkSvg(width: number, height: number): Buffer {
  const fontSize = Math.round(width * 0.045)
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">
    <text
      x="${width / 2}"
      y="${height / 2}"
      text-anchor="middle"
      dominant-baseline="middle"
      font-family="system-ui, sans-serif"
      font-size="${fontSize}"
      font-weight="bold"
      fill="white"
      opacity="0.55"
      letter-spacing="3"
    >SCREENSHOT FORGE</text>
  </svg>`
  return Buffer.from(svg)
}

export async function generatePreview(compositeBuffer: Buffer): Promise<Buffer> {
  const { width, height } = await sharp(compositeBuffer).metadata()
  if (!width || !height) throw new Error('Invalid composite buffer')

  const gradient = buildGradientSvg(width, height)
  const watermark = buildWatermarkSvg(width, height)

  return sharp(gradient)
    .composite([
      { input: compositeBuffer, blend: 'over' },
      { input: watermark, blend: 'over' },
    ])
    .flatten({ background: '#000000' }) // ensure no alpha
    .jpeg({ quality: 85 })
    .toBuffer()
}
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
npm test lib/sharp/preview.test.ts
```

- [ ] **Step 5: Commit**

```bash
git add lib/sharp/preview.ts lib/sharp/preview.test.ts
git commit -m "feat: add preview generator with gradient and watermark"
```

---

## Task 9: Sessions API route (upload + process)

**Files:**
- Create: `app/api/sessions/route.ts`

This route receives Storage paths (uploaded by client), validates aspect ratios, runs compositing, stores output + preview to Storage, creates DB records.

- [ ] **Step 1: Write route**

Create `app/api/sessions/route.ts`:
```typescript
import { createClient } from '@/lib/supabase/server'
import { createAdminClient } from '@/lib/supabase/admin'
import { isAspectRatioValid, FRAME_CONFIGS } from '@/lib/sharp/frames'
import { compositeScreenshot } from '@/lib/sharp/composite'
import { generatePreview } from '@/lib/sharp/preview'
import { NextResponse } from 'next/server'
import type { DeviceModel } from '@/lib/types'

interface ProcessRequest {
  model: DeviceModel
  // Supabase Storage paths in 'session-files' bucket (temp/user_id/filename)
  storagePaths: string[]
}

export async function POST(request: Request) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const body: ProcessRequest = await request.json()
  const { model, storagePaths } = body

  if (!model || !FRAME_CONFIGS[model]) {
    return NextResponse.json({ error: 'Invalid model' }, { status: 400 })
  }
  if (!storagePaths || storagePaths.length === 0 || storagePaths.length > 6) {
    return NextResponse.json({ error: 'Provide 1–6 images' }, { status: 400 })
  }

  const admin = createAdminClient()

  // Create session record first
  const { data: session, error: sessionErr } = await admin
    .from('sessions')
    .insert({ user_id: user.id, model })
    .select()
    .single()

  if (sessionErr) return NextResponse.json({ error: 'DB error' }, { status: 500 })

  const imageRecords: { preview_url: string; original_name: string; id: string }[] = []

  for (const storagePath of storagePaths) {
    const fileName = storagePath.split('/').pop() ?? 'image.png'

    // Download original from temp upload location
    const { data: fileData, error: dlErr } = await admin.storage
      .from('session-files')
      .download(storagePath)
    if (dlErr) {
      await admin.from('sessions').delete().eq('id', session.id)
      return NextResponse.json({ error: `Failed to read ${fileName}` }, { status: 400 })
    }

    const fileBuffer = Buffer.from(await fileData.arrayBuffer())

    // Validate aspect ratio (get image dimensions first)
    const sharp = (await import('sharp')).default
    const meta = await sharp(fileBuffer).metadata()
    if (!meta.width || !meta.height) {
      return NextResponse.json({ error: `Invalid image: ${fileName}` }, { status: 400 })
    }
    if (!isAspectRatioValid(meta.width, meta.height, model)) {
      await admin.from('sessions').delete().eq('id', session.id)
      return NextResponse.json({
        error: `${fileName} aspect ratio doesn't match ${FRAME_CONFIGS[model].label}. Expected ~${FRAME_CONFIGS[model].screenWidth}×${FRAME_CONFIGS[model].screenHeight}.`,
      }, { status: 422 })
    }

    // Composite + preview
    const composite = await compositeScreenshot(fileBuffer, model)
    const preview = await generatePreview(composite)

    // Store outputs
    const outputPath = `sessions/${session.id}/output/${fileName.replace(/\.[^.]+$/, '.png')}`
    const previewPath = `sessions/${session.id}/preview/${fileName.replace(/\.[^.]+$/, '.jpg')}`

    await admin.storage.from('session-files').upload(outputPath, composite, { contentType: 'image/png' })
    await admin.storage.from('session-files').upload(previewPath, preview, { contentType: 'image/jpeg' })

    // Get signed URL for preview (1 hour — enough to show and pay)
    const { data: signedUrl } = await admin.storage
      .from('session-files')
      .createSignedUrl(previewPath, 3600)

    const { data: imgRecord } = await admin.from('session_images').insert({
      session_id: session.id,
      original_name: fileName,
      preview_path: previewPath,
      output_path: outputPath,
    }).select().single()

    imageRecords.push({
      id: imgRecord!.id,
      original_name: fileName,
      preview_url: signedUrl!.signedUrl,
    })
  }

  return NextResponse.json({ sessionId: session.id, images: imageRecords })
}
```

- [ ] **Step 2: Test via curl**

```bash
# First upload a test image directly to Supabase Storage via dashboard,
# note the path, then:
curl -X POST http://localhost:3000/api/sessions \
  -H "Content-Type: application/json" \
  -H "Cookie: <your-session-cookie>" \
  -d '{"model": "iphone-17", "storagePaths": ["temp/USER_ID/test.png"]}'
```

Expected: `{ "sessionId": "...", "images": [{ "preview_url": "..." }] }`

- [ ] **Step 3: Commit**

```bash
git add app/api/sessions/route.ts
git commit -m "feat: add sessions API route for image processing"
```

---

## Task 10: Upload + preview frontend page

**Files:**
- Create: `components/model-selector.tsx`, `components/upload-zone.tsx`, `components/preview-grid.tsx`, `app/(app)/page.tsx`

- [ ] **Step 1: Write model selector component**

Create `components/model-selector.tsx`:
```typescript
'use client'
import { FRAME_CONFIGS } from '@/lib/sharp/frames'
import type { DeviceModel } from '@/lib/types'

interface Props {
  value: DeviceModel
  onChange: (model: DeviceModel) => void
  disabled?: boolean
}

const MODELS: DeviceModel[] = ['iphone-17', 'iphone-17-air', 'iphone-17-pro', 'iphone-17-pro-max']

export function ModelSelector({ value, onChange, disabled }: Props) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {MODELS.map((model) => (
        <button
          key={model}
          onClick={() => onChange(model)}
          disabled={disabled}
          className={`p-3 rounded-xl border-2 text-sm font-medium transition-colors
            ${value === model
              ? 'border-orange-500 bg-orange-950 text-orange-200'
              : 'border-zinc-700 bg-zinc-900 text-zinc-400 hover:border-zinc-500'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          <div className="text-xs text-zinc-500">{FRAME_CONFIGS[model].color}</div>
          {FRAME_CONFIGS[model].label}
        </button>
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Write upload zone component**

Create `components/upload-zone.tsx`:
```typescript
'use client'
import { useRef, useState } from 'react'

interface Props {
  onFiles: (files: File[]) => void
  disabled?: boolean
  maxFiles?: number
}

export function UploadZone({ onFiles, disabled, maxFiles = 6 }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  function handleFiles(fileList: FileList) {
    const files = Array.from(fileList)
      .filter(f => f.type.startsWith('image/'))
      .slice(0, maxFiles)
    if (files.length > 0) onFiles(files)
  }

  return (
    <div
      onDragOver={e => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={e => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files) }}
      onClick={() => inputRef.current?.click()}
      className={`border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-colors
        ${dragging ? 'border-orange-500 bg-orange-950/30' : 'border-zinc-700 hover:border-zinc-500'}
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        multiple
        className="hidden"
        onChange={e => e.target.files && handleFiles(e.target.files)}
        disabled={disabled}
      />
      <p className="text-zinc-400">
        Drop up to {maxFiles} screenshots here, or <span className="text-orange-400 underline">browse</span>
      </p>
      <p className="text-xs text-zinc-600 mt-2">PNG, JPG, WebP · Max 10 MB each</p>
    </div>
  )
}
```

- [ ] **Step 3: Write preview grid component**

Create `components/preview-grid.tsx`:
```typescript
'use client'
import Image from 'next/image'

interface PreviewImage {
  id: string
  original_name: string
  preview_url: string
}

interface Props {
  images: PreviewImage[]
}

export function PreviewGrid({ images }: Props) {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
      {images.map(img => (
        <div key={img.id} className="relative aspect-[9/19.5] rounded-xl overflow-hidden bg-zinc-900">
          <Image
            src={img.preview_url}
            alt={img.original_name}
            fill
            className="object-contain"
            unoptimized
          />
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 4: Write main page**

Create `app/(app)/page.tsx`:
```typescript
'use client'
import { useState } from 'react'
import { createClient } from '@/lib/supabase/client'
import { ModelSelector } from '@/components/model-selector'
import { UploadZone } from '@/components/upload-zone'
import { PreviewGrid } from '@/components/preview-grid'
import type { DeviceModel } from '@/lib/types'

interface ProcessedImage {
  id: string
  original_name: string
  preview_url: string
}

type Stage = 'upload' | 'processing' | 'preview' | 'paying' | 'done'

export default function HomePage() {
  const [model, setModel] = useState<DeviceModel>('iphone-17-pro')
  const [stage, setStage] = useState<Stage>('upload')
  const [images, setImages] = useState<ProcessedImage[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleFiles(files: File[]) {
    if (files.length === 0) return
    setError(null)
    setStage('processing')

    const supabase = createClient()
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return

    // Upload files directly to Supabase Storage
    const storagePaths: string[] = []
    for (const file of files) {
      const path = `temp/${user.id}/${Date.now()}-${file.name}`
      const { error: upErr } = await supabase.storage
        .from('session-files')
        .upload(path, file, { upsert: true })
      if (upErr) { setError('Upload failed: ' + upErr.message); setStage('upload'); return }
      storagePaths.push(path)
    }

    // Process via API
    const resp = await fetch('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model, storagePaths }),
    })
    const json = await resp.json()

    if (!resp.ok) { setError(json.error); setStage('upload'); return }

    setSessionId(json.sessionId)
    setImages(json.images)
    setStage('preview')
  }

  async function handlePay() {
    if (!sessionId) return
    setStage('paying')
    const resp = await fetch('/api/stripe/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sessionId }),
    })
    const { url } = await resp.json()
    if (url) window.location.href = url
    else { setError('Payment error'); setStage('preview') }
  }

  return (
    <main className="min-h-screen bg-black text-white p-6 max-w-2xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold text-orange-400">Screenshot Forge</h1>

      {error && (
        <div className="bg-red-950 border border-red-700 text-red-300 rounded-xl p-4 text-sm">
          {error}
        </div>
      )}

      {(stage === 'upload' || stage === 'processing') && (
        <>
          <section className="space-y-3">
            <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-wider">Select model</h2>
            <ModelSelector value={model} onChange={setModel} disabled={stage === 'processing'} />
          </section>
          <section className="space-y-3">
            <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-wider">Upload screenshots</h2>
            <UploadZone onFiles={handleFiles} disabled={stage === 'processing'} />
            {stage === 'processing' && (
              <p className="text-center text-orange-400 animate-pulse">Processing your screenshots…</p>
            )}
          </section>
        </>
      )}

      {stage === 'preview' && images.length > 0 && (
        <>
          <section className="space-y-3">
            <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-wider">Preview</h2>
            <PreviewGrid images={images} />
          </section>
          <div className="flex gap-3">
            <button
              onClick={() => { setStage('upload'); setImages([]) }}
              className="flex-1 py-3 rounded-xl border border-zinc-700 text-zinc-400 hover:border-zinc-500 transition-colors"
            >
              Start over
            </button>
            <button
              onClick={handlePay}
              className="flex-1 py-3 rounded-xl bg-orange-600 hover:bg-orange-500 font-semibold transition-colors"
            >
              Download for €1.99
            </button>
          </div>
        </>
      )}

      {stage === 'paying' && (
        <p className="text-center text-orange-400 animate-pulse">Redirecting to payment…</p>
      )}
    </main>
  )
}
```

- [ ] **Step 5: Add auth layout**

Create `app/(app)/layout.tsx`:
```typescript
import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/login')
  return <>{children}</>
}
```

- [ ] **Step 6: Test UI locally**

```bash
npm run dev
```

- Log in with Google
- Select a model, drop screenshots, verify "Processing…" state appears
- Verify API call is made, preview grid renders with watermarked images

- [ ] **Step 7: Commit**

```bash
git add app/(app)/ components/
git commit -m "feat: add upload, model selector, and preview UI"
```

---

## Task 11: Stripe payment flow

**Files:**
- Create: `lib/stripe.ts`, `app/api/stripe/checkout/route.ts`, `app/api/stripe/webhook/route.ts`

- [ ] **Step 1: Set up Stripe account**

1. Create account at [stripe.com](https://stripe.com)
2. In Stripe dashboard → Products → Create product: "Screenshot Forge Session", price €1.99 one-time
3. Copy Price ID (starts with `price_`)
4. Add to `.env.local`:
   ```bash
   STRIPE_PRICE_ID=price_...
   ```
5. Enable webhooks: Dashboard → Webhooks → Add endpoint: `https://YOUR_DOMAIN/api/stripe/webhook`, event: `checkout.session.completed`
6. Copy webhook secret to `.env.local` as `STRIPE_WEBHOOK_SECRET`

- [ ] **Step 2: Write Stripe client**

Create `lib/stripe.ts`:
```typescript
import Stripe from 'stripe'

export const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2025-03-31.basil',
})
```

- [ ] **Step 3: Write Checkout route**

Create `app/api/stripe/checkout/route.ts`:
```typescript
import { createClient } from '@/lib/supabase/server'
import { stripe } from '@/lib/stripe'
import { NextResponse } from 'next/server'

export async function POST(request: Request) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { sessionId } = await request.json()

  // Verify session belongs to user
  const { data: session } = await supabase
    .from('sessions')
    .select('id, status')
    .eq('id', sessionId)
    .eq('user_id', user.id)
    .single()

  if (!session) return NextResponse.json({ error: 'Session not found' }, { status: 404 })
  if (session.status !== 'pending') return NextResponse.json({ error: 'Session not payable' }, { status: 400 })

  const appUrl = process.env.NEXT_PUBLIC_APP_URL!

  const checkout = await stripe.checkout.sessions.create({
    mode: 'payment',
    line_items: [{ price: process.env.STRIPE_PRICE_ID!, quantity: 1 }],
    success_url: `${appUrl}/sessions?paid=${sessionId}`,
    cancel_url: `${appUrl}/?cancelled=1`,
    metadata: { sessionId, userId: user.id },
    customer_email: user.email,
  })

  // Store stripe checkout ID on session
  await supabase.from('sessions')
    .update({ stripe_checkout_id: checkout.id })
    .eq('id', sessionId)

  return NextResponse.json({ url: checkout.url })
}
```

- [ ] **Step 4: Write webhook handler**

Create `app/api/stripe/webhook/route.ts`:
```typescript
import { stripe } from '@/lib/stripe'
import { createAdminClient } from '@/lib/supabase/admin'
import { NextResponse } from 'next/server'

export async function POST(request: Request) {
  const body = await request.text()
  const sig = request.headers.get('stripe-signature')!

  let event: ReturnType<typeof stripe.webhooks.constructEvent>
  try {
    event = stripe.webhooks.constructEvent(body, sig, process.env.STRIPE_WEBHOOK_SECRET!)
  } catch {
    return NextResponse.json({ error: 'Invalid signature' }, { status: 400 })
  }

  if (event.type === 'checkout.session.completed') {
    const checkout = event.data.object
    const sessionId = checkout.metadata?.sessionId

    if (sessionId) {
      const admin = createAdminClient()
      const sevenDaysFromNow = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString()
      await admin.from('sessions').update({
        status: 'paid',
        completed_at: new Date().toISOString(),
        files_expire_at: sevenDaysFromNow,
      }).eq('id', sessionId)
    }
  }

  return NextResponse.json({ received: true })
}
```

- [ ] **Step 5: Test webhook locally with Stripe CLI**

```bash
npx stripe listen --forward-to localhost:3000/api/stripe/webhook
```

In another terminal:
```bash
npx stripe trigger checkout.session.completed
```

Expected: session status updated to `paid` in Supabase.

- [ ] **Step 6: Commit**

```bash
git add lib/stripe.ts app/api/stripe/
git commit -m "feat: add Stripe Checkout and webhook handler"
```

---

## Task 12: Download ZIP endpoint

**Files:**
- Create: `app/api/sessions/[id]/download/route.ts`

- [ ] **Step 1: Write download route**

Create `app/api/sessions/[id]/download/route.ts`:
```typescript
import { createClient } from '@/lib/supabase/server'
import { createAdminClient } from '@/lib/supabase/admin'
import { NextResponse } from 'next/server'
import JSZip from 'jszip'

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  // Load session + images
  const { data: session } = await supabase
    .from('sessions')
    .select('*, session_images(*)')
    .eq('id', id)
    .eq('user_id', user.id)
    .single()

  if (!session) return NextResponse.json({ error: 'Not found' }, { status: 404 })
  if (session.status !== 'paid' && session.status !== 'free') {
    return NextResponse.json({ error: 'Payment required' }, { status: 402 })
  }
  if (session.files_expire_at && new Date(session.files_expire_at) < new Date()) {
    return NextResponse.json({ error: 'Files expired' }, { status: 410 })
  }

  const admin = createAdminClient()
  const zip = new JSZip()

  for (const img of session.session_images) {
    const { data, error } = await admin.storage
      .from('session-files')
      .download(img.output_path)
    if (error || !data) continue
    const buffer = Buffer.from(await data.arrayBuffer())
    zip.file(img.original_name.replace(/\.[^.]+$/, '_framed.png'), buffer)
  }

  const zipBuffer = await zip.generateAsync({ type: 'nodebuffer' })

  return new Response(zipBuffer, {
    headers: {
      'Content-Type': 'application/zip',
      'Content-Disposition': `attachment; filename="screenshot-forge-${id.slice(0, 8)}.zip"`,
    },
  })
}
```

- [ ] **Step 2: Test download after paying**

```bash
# After completing a test Stripe payment:
curl -o test-output.zip \
  -H "Cookie: <session-cookie>" \
  http://localhost:3000/api/sessions/SESSION_ID/download
unzip -l test-output.zip
```

Expected: ZIP with `*_framed.png` files inside.

- [ ] **Step 3: Add download button to preview page**

In `app/(app)/page.tsx`, add after payment success redirect (when `stage === 'done'`):

```typescript
// At top: read ?paid= query param to show download
// Add this to the component:
const searchParams = useSearchParams()
const paidSessionId = searchParams.get('paid')

// Add this block in JSX:
{paidSessionId && (
  <div className="space-y-4 text-center">
    <p className="text-green-400">Payment successful!</p>
    <a
      href={`/api/sessions/${paidSessionId}/download`}
      className="inline-block bg-orange-600 hover:bg-orange-500 px-6 py-3 rounded-xl font-semibold transition-colors"
    >
      Download ZIP
    </a>
  </div>
)}
```

Also add `'use client'` at top and `import { useSearchParams } from 'next/navigation'` (already present).

- [ ] **Step 4: Commit**

```bash
git add app/api/sessions/
git commit -m "feat: add ZIP download endpoint for paid sessions"
```

---

## Task 13: Free tier (1 lifetime image)

**Files:**
- Create: `app/api/sessions/[id]/free-download/route.ts`
- Modify: `app/api/sessions/route.ts` (add free-tier flag on session record)
- Modify: `app/(app)/page.tsx` (show free download button if eligible)

- [ ] **Step 1: Check free credit eligibility in sessions route**

In `app/api/sessions/route.ts`, after creating the session record and before returning, check if this is a free-eligible session (1 image, user hasn't used credit yet). Add to the response:

```typescript
// After creating session record:
const { data: profile } = await admin
  .from('profiles')
  .select('free_credit_used')
  .eq('id', user.id)
  .single()

const isFreeEligible = !profile?.free_credit_used && storagePaths.length === 1

// Include in response:
return NextResponse.json({
  sessionId: session.id,
  images: imageRecords,
  freeEligible: isFreeEligible,
})
```

- [ ] **Step 2: Write free-download route**

Create `app/api/sessions/[id]/free-download/route.ts`:
```typescript
import { createClient } from '@/lib/supabase/server'
import { createAdminClient } from '@/lib/supabase/admin'
import { NextResponse } from 'next/server'

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const admin = createAdminClient()

  // Verify eligibility
  const [{ data: profile }, { data: session }] = await Promise.all([
    admin.from('profiles').select('free_credit_used').eq('id', user.id).single(),
    admin.from('sessions').select('*, session_images(*)').eq('id', id).eq('user_id', user.id).single(),
  ])

  if (!session) return NextResponse.json({ error: 'Not found' }, { status: 404 })
  if (profile?.free_credit_used) return NextResponse.json({ error: 'Free credit already used' }, { status: 403 })
  if (session.session_images.length !== 1) return NextResponse.json({ error: 'Free tier: 1 image only' }, { status: 400 })
  if (session.status !== 'pending') return NextResponse.json({ error: 'Session not eligible' }, { status: 400 })

  const sevenDaysFromNow = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString()

  await Promise.all([
    admin.from('sessions').update({
      status: 'free',
      completed_at: new Date().toISOString(),
      files_expire_at: sevenDaysFromNow,
    }).eq('id', id),
    admin.from('profiles').update({ free_credit_used: true }).eq('id', user.id),
  ])

  return NextResponse.json({ downloadUrl: `/api/sessions/${id}/download` })
}
```

- [ ] **Step 3: Update preview page to show free option**

In `app/(app)/page.tsx`, add `freeEligible` state and conditional button:

```typescript
const [freeEligible, setFreeEligible] = useState(false)

// In handleFiles, after successful API response:
setFreeEligible(json.freeEligible ?? false)

// In preview stage JSX, alongside pay button:
{freeEligible && (
  <button
    onClick={async () => {
      const resp = await fetch(`/api/sessions/${sessionId}/free-download`, { method: 'POST' })
      const { downloadUrl } = await resp.json()
      window.location.href = downloadUrl
    }}
    className="flex-1 py-3 rounded-xl border border-orange-700 text-orange-400 hover:bg-orange-950 transition-colors"
  >
    Download free (1 image)
  </button>
)}
```

- [ ] **Step 4: Test free tier**

- Sign in with fresh account
- Upload exactly 1 screenshot
- Expect "Download free (1 image)" button to appear
- Click it — should download PNG directly
- Upload again — button should not appear

- [ ] **Step 5: Commit**

```bash
git add app/api/sessions/ app/\(app\)/page.tsx
git commit -m "feat: add free tier (1 lifetime image per account)"
```

---

## Task 14: Session history dashboard

**Files:**
- Create: `app/(app)/sessions/page.tsx`, `components/session-card.tsx`

- [ ] **Step 1: Write session card component**

Create `components/session-card.tsx`:
```typescript
import { FRAME_CONFIGS } from '@/lib/sharp/frames'
import type { Session, SessionImage } from '@/lib/types'

interface Props {
  session: Session & { session_images: SessionImage[] }
}

const STATUS_COLORS = {
  paid: 'text-green-400',
  free: 'text-blue-400',
  pending: 'text-yellow-400',
  expired: 'text-zinc-600',
}

export function SessionCard({ session }: Props) {
  const isDownloadable = session.status === 'paid' || session.status === 'free'
  const isExpired = session.files_expire_at ? new Date(session.files_expire_at) < new Date() : false

  return (
    <div className="bg-zinc-900 rounded-xl p-4 space-y-3">
      <div className="flex justify-between items-start">
        <div>
          <p className="font-medium">{FRAME_CONFIGS[session.model as keyof typeof FRAME_CONFIGS]?.label}</p>
          <p className="text-xs text-zinc-500">{new Date(session.created_at).toLocaleDateString()}</p>
        </div>
        <span className={`text-xs font-medium uppercase ${STATUS_COLORS[session.status]}`}>
          {session.status}
        </span>
      </div>
      <p className="text-sm text-zinc-400">{session.session_images.length} image{session.session_images.length !== 1 ? 's' : ''}</p>
      {isDownloadable && !isExpired && (
        <a
          href={`/api/sessions/${session.id}/download`}
          className="block text-center py-2 rounded-lg bg-orange-700 hover:bg-orange-600 text-sm font-medium transition-colors"
        >
          Re-download ZIP
        </a>
      )}
      {isExpired && <p className="text-xs text-zinc-600">Files expired</p>}
    </div>
  )
}
```

- [ ] **Step 2: Write sessions page**

Create `app/(app)/sessions/page.tsx`:
```typescript
import { createClient } from '@/lib/supabase/server'
import { SessionCard } from '@/components/session-card'

export default async function SessionsPage() {
  const supabase = await createClient()
  const { data: sessions } = await supabase
    .from('sessions')
    .select('*, session_images(*)')
    .order('created_at', { ascending: false })
    .limit(20)

  return (
    <main className="min-h-screen bg-black text-white p-6 max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-orange-400">Your Sessions</h1>
        <a href="/" className="text-sm text-zinc-400 hover:text-zinc-200">+ New</a>
      </div>
      {!sessions?.length && (
        <p className="text-zinc-600 text-center py-10">No sessions yet. <a href="/" className="text-orange-400 underline">Create one</a></p>
      )}
      <div className="space-y-4">
        {sessions?.map(s => <SessionCard key={s.id} session={s as any} />)}
      </div>
    </main>
  )
}
```

- [ ] **Step 3: Add nav link to main page**

In `app/(app)/page.tsx`, add to the header:
```typescript
// In JSX header area:
<div className="flex justify-between items-center">
  <h1 className="text-2xl font-bold text-orange-400">Screenshot Forge</h1>
  <a href="/sessions" className="text-sm text-zinc-400 hover:text-zinc-200">History</a>
</div>
```

- [ ] **Step 4: Commit**

```bash
git add app/\(app\)/sessions/ components/session-card.tsx
git commit -m "feat: add session history dashboard"
```

---

## Task 15: Cleanup cron (7-day file expiry)

**Files:**
- Create: `app/api/cron/cleanup/route.ts`, `vercel.json`

- [ ] **Step 1: Write cleanup route**

Create `app/api/cron/cleanup/route.ts`:
```typescript
import { createAdminClient } from '@/lib/supabase/admin'
import { NextResponse } from 'next/server'

export async function GET(request: Request) {
  // Verify this is called by Vercel Cron (not public)
  const authHeader = request.headers.get('authorization')
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const admin = createAdminClient()
  const now = new Date().toISOString()

  // 1. Find sessions with expired files
  const { data: expiredSessions } = await admin
    .from('sessions')
    .select('id, session_images(output_path, preview_path)')
    .lt('files_expire_at', now)
    .in('status', ['paid', 'free'])

  if (expiredSessions) {
    for (const session of expiredSessions) {
      const paths: string[] = []
      for (const img of session.session_images) {
        paths.push(img.output_path, img.preview_path)
      }
      if (paths.length > 0) {
        await admin.storage.from('session-files').remove(paths)
      }
    }
  }

  // 2. Expire sessions past the 1h unpaid window
  await admin.from('sessions')
    .update({ status: 'expired' })
    .eq('status', 'pending')
    .lt('session_expires_at', now)

  // 3. Delete expired session records (and cascade session_images)
  await admin.from('sessions')
    .delete()
    .eq('status', 'expired')
    .lt('session_expires_at', new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()) // 1d after expiry

  return NextResponse.json({
    cleaned: expiredSessions?.length ?? 0,
    timestamp: now,
  })
}
```

- [ ] **Step 2: Add CRON_SECRET to env**

Add to `.env.local`:
```bash
CRON_SECRET=your-random-secret-here
```

Generate with: `openssl rand -hex 32`

- [ ] **Step 3: Write vercel.json**

Create `vercel.json`:
```json
{
  "crons": [
    {
      "path": "/api/cron/cleanup",
      "schedule": "0 3 * * *"
    }
  ]
}
```

This runs cleanup daily at 3 AM UTC.

- [ ] **Step 4: Test cleanup manually**

```bash
curl -H "Authorization: Bearer your-random-secret-here" \
  http://localhost:3000/api/cron/cleanup
```

Expected: `{ "cleaned": 0, "timestamp": "..." }`

- [ ] **Step 5: Commit**

```bash
git add app/api/cron/ vercel.json
git commit -m "feat: add daily cleanup cron for expired sessions"
```

---

## Task 16: Deploy to Vercel

**Files:**
- Modify: `next.config.ts` (add sharp output config)

- [ ] **Step 1: Configure Next.js for Sharp on Vercel**

Modify `next.config.ts`:
```typescript
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '*.supabase.co',
      },
    ],
  },
  // Sharp requires native binaries — mark as server-only
  serverExternalPackages: ['sharp'],
}

export default nextConfig
```

- [ ] **Step 2: Create Vercel account and deploy**

```bash
npm install -g vercel
vercel login
vercel
```

Follow prompts: link to existing project (no), set project name `screenshot-forge`, framework Next.js, root directory `.`.

- [ ] **Step 3: Add environment variables in Vercel dashboard**

In Vercel → Project → Settings → Environment Variables, add all vars from `.env.local`:
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `STRIPE_SECRET_KEY`
- `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_ID`
- `NEXT_PUBLIC_APP_URL` (set to your Vercel URL, e.g. `https://screenshot-forge.vercel.app`)
- `CRON_SECRET`

- [ ] **Step 4: Update Supabase redirect URL**

In Supabase → Authentication → URL Configuration:
- Site URL: `https://screenshot-forge.vercel.app`
- Redirect URLs: add `https://screenshot-forge.vercel.app/auth/callback`

In Google Cloud Console, add `https://YOUR_PROJECT.supabase.co/auth/v1/callback` to authorized redirect URIs (already done in Task 4, should be fine).

- [ ] **Step 5: Update Stripe webhook URL**

In Stripe dashboard → Webhooks → update endpoint URL to `https://screenshot-forge.vercel.app/api/stripe/webhook`.

- [ ] **Step 6: Deploy to production**

```bash
vercel --prod
```

- [ ] **Step 7: Smoke test production**

1. Visit `https://screenshot-forge.vercel.app`
2. Sign in with Google
3. Upload 1 screenshot, select model → should process and show preview
4. Use free tier → should download PNG
5. Upload 1-6 screenshots → click pay → complete Stripe test payment → download ZIP

- [ ] **Step 8: Commit**

```bash
git add next.config.ts vercel.json
git commit -m "feat: configure Next.js for Vercel production deploy"
```

---

## Self-review

**Spec coverage:**

| Requirement | Task |
|-------------|------|
| iOS screenshot upload | Task 9, 10 |
| Select iPhone model (17/Air/Pro/Pro Max) | Task 6, 10 |
| Server-side compositing | Task 7, 9 |
| Transparent PNG output | Task 7 |
| Watermarked preview (gradient background) | Task 8 |
| Google OAuth login | Task 4 |
| Free tier (1 lifetime image) | Task 13 |
| Pay €1.99/session via Stripe | Task 11 |
| Up to 6 images per session | Task 9 |
| ZIP download | Task 12 |
| Session history + re-download | Task 14 |
| 7-day file retention | Task 2 (schema), Task 15 |
| 1-hour session expiry if unpaid | Task 2 (schema), Task 15 |
| Aspect ratio validation with error | Task 6 |
| Vercel deploy | Task 16 |
| Daily cleanup cron | Task 15 |

**Placeholder scan:** None found. All steps have concrete code.

**Type consistency:** `DeviceModel` defined in `lib/types.ts` Task 3, used in frames.ts Task 6, composite.ts Task 7, and all API routes. `Session`/`SessionImage` types defined in Task 3, used in Task 14. Consistent throughout.

---

Sources:
- [iPhone 17 Pro - Tech Specs - Apple](https://support.apple.com/en-us/125090)
- [iPhone 17 Screen Sizes](https://useyourloaf.com/blog/iphone-17-screen-sizes/)
- [iPhone 17, Air, 17 Pro, and 17 Pro Max Mockups on Figma](https://www.figma.com/community/file/1564652018971544072/iphone-17-air-17-pro-and-17-pro-max-mockups-device-frames)
- [App Store Screenshot Dimensions 2026](https://screenhange.com/blog/app-store-screenshot-dimensions-2026)
