# APE 2026 Frontend

Production-grade web interface for **APE 2026 - Autonomous Prediction Engine**.

Financial analysis with zero hallucination guarantee.

---

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- npm or yarn
- APE 2026 Backend API running on `localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.local.example .env.local
# Edit .env.local with your API URL

# Run development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 📦 Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | Next.js 14 (App Router) |
| Language | TypeScript |
| Styling | Tailwind CSS |
| UI Library | shadcn/ui |
| State | Zustand |
| HTTP Client | Axios |
| Charts | TradingView Lightweight Charts, Recharts |
| Animations | Framer Motion |
| WebSocket | Native WebSocket API |

---

## 📂 Project Structure

```
frontend/
├── app/                      # Next.js 14 App Router
│   ├── layout.tsx           # Root layout
│   ├── page.tsx             # Landing page
│   ├── login/               # Login page
│   ├── register/            # Register page
│   └── dashboard/           # Dashboard (authenticated)
│       ├── layout.tsx       # Dashboard layout (Navbar + Sidebar)
│       ├── page.tsx         # Dashboard home
│       ├── query/
│       │   └── new/         # Query builder
│       ├── history/         # Query history
│       └── facts/           # Verified facts browser
├── components/
│   ├── ui/                  # shadcn/ui components (20+)
│   ├── layout/              # Navbar, Sidebar
│   └── providers/           # Theme, Toast, WebSocket providers
├── lib/
│   ├── api.ts               # Axios client + API methods
│   ├── store.ts             # Zustand state management
│   ├── utils.ts             # Helper functions
│   └── constants.ts         # Constants (API URLs, states, etc.)
├── public/                  # Static assets
├── tailwind.config.ts       # Tailwind configuration
├── tsconfig.json            # TypeScript configuration
├── next.config.js           # Next.js configuration
└── package.json             # Dependencies
```

---

## 🎨 Features

### Week 8 Day 2 (Current) ✅
- ✅ Next.js 14 project setup
- ✅ TypeScript + Tailwind + shadcn/ui
- ✅ Authentication UI (login/register)
- ✅ Dashboard layout (Navbar + Sidebar)
- ✅ API client with interceptors
- ✅ Zustand state management
- ✅ Dark/light theme toggle
- ✅ Toast notifications

### Week 8 Day 3 (Planned) 📋
- Query Builder UI
- WebSocket real-time updates
- Live status tracking (PLAN → FETCH → VEE → GATE)
- Progress bar + pipeline visualization

### Week 8 Day 4 (Planned) 📋
- Results dashboard
- Verified Facts table (sortable, filterable)
- Debate Viewer (Bull/Bear/Neutral)
- Code Viewer (syntax highlighting)
- Export functionality (JSON/CSV)

### Week 8 Day 5 (Planned) 📋
- TradingView Lightweight Charts
- Recharts analytics
- Performance optimization (Lighthouse >90)
- Production build + Docker

---

## 🔧 Available Scripts

```bash
# Development
npm run dev          # Start dev server (localhost:3000)

# Build
npm run build        # Build for production
npm run start        # Start production server

# Linting & Formatting
npm run lint         # Run ESLint
npm run format       # Format code with Prettier
```

---

## 🔗 API Integration

### Backend Endpoints (FastAPI)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/query` | Submit analysis query |
| GET | `/status/{query_id}` | Get query execution status |
| GET | `/episodes/{episode_id}` | Get episode details + facts |
| GET | `/facts` | List verified facts (paginated) |
| GET | `/health` | Health check |
| WS | `/ws` | WebSocket for real-time updates |

### Environment Variables

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_APP_NAME=APE 2026
```

---

## 🎯 Key Pages

### Landing Page (`/`)
- Hero section with features
- Stats (0.00% hallucination, 100% temporal adherence)
- Call-to-action buttons

### Login (`/login`)
- API key authentication
- Health check validation
- Redirect to dashboard on success

### Dashboard (`/dashboard`)
- Quick actions (New Query, History, Facts)
- System status widget
- Recent activity feed

---

## 🎨 UI Components (shadcn/ui)

**Installed Components:**
- Button, Card, Input, Label, Textarea
- Badge, Progress, Skeleton
- Toast, Toaster
- (More coming in Day 3-5)

**Custom Components:**
- Navbar (theme toggle, logout)
- Sidebar (navigation, system status)
- ThemeProvider (dark/light mode)

---

## 🔐 Authentication

Currently using **API key authentication**:
1. User enters API key on login page
2. Key validated via `/health` endpoint
3. Stored in localStorage + Zustand store
4. Added to all API requests via Axios interceptor

**Demo Key:** `sk-ape-demo-12345678901234567890`

---

## 📱 Responsive Design

- Mobile-first approach
- Breakpoints: sm (640px), md (768px), lg (1024px), xl (1280px), 2xl (1400px)
- Sidebar collapses on mobile with overlay
- Responsive grid layouts

---

## 🌙 Theme

- Dark mode (default)
- Light mode
- System preference support
- Persisted in localStorage
- Smooth transitions

---

## 📊 Performance Targets

| Metric | Target |
|--------|--------|
| First Contentful Paint | <1.5s |
| Time to Interactive | <3s |
| Lighthouse Score | >90 |
| Bundle Size (gzipped) | <500KB |

---

## 🚢 Deployment

### Development
```bash
npm run dev
```

### Production (Vercel)
```bash
vercel
```

### Production (Docker)
```bash
docker build -t ape-2026-frontend .
docker run -p 3000:3000 ape-2026-frontend
```

---

## 📚 Documentation

- [Next.js Docs](https://nextjs.org/docs)
- [shadcn/ui Components](https://ui.shadcn.com)
- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [Zustand Docs](https://zustand-demo.pmnd.rs/)

---

## 🐛 Troubleshooting

### API Connection Failed
- Ensure backend is running on `localhost:8000`
- Check `.env.local` has correct `NEXT_PUBLIC_API_URL`
- Verify CORS settings on backend

### Build Errors
- Delete `node_modules` and `.next` directories
- Run `npm install` again
- Check Node.js version (18+)

### Theme Not Working
- Clear localStorage
- Hard refresh browser (Ctrl+Shift+R)

---

## 📄 License

MIT

---

## 🤝 Contributing

This is a production project for APE 2026. Follow the established patterns and conventions.

---

**Version:** 1.0.0 (Week 8 Day 2)
**Last Updated:** 2026-02-08
**Status:** ✅ Base Infrastructure Complete
