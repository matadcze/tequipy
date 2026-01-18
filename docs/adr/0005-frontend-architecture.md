# ADR-0005: Frontend Architecture with Next.js App Router

## Status

Accepted

## Context

We need to establish a frontend architecture pattern that:

- Provides excellent developer experience with modern React features
- Supports both server-side rendering (SSR) and client-side interactivity
- Enables clear separation of concerns (UI, state, data fetching)
- Scales well as the application grows
- Integrates seamlessly with our FastAPI backend

The frontend will handle user authentication, profile management, dashboard views, and an LLM agent interface.

## Decision

We adopt **Next.js 16 with App Router** and organize the frontend following these patterns:

### Architecture Structure

```
frontend/src/
├── app/                    # Next.js App Router (Pages)
│   ├── layout.tsx         # Root layout with providers
│   ├── page.tsx           # Home/landing page
│   ├── (auth)/            # Auth route group
│   │   ├── login/
│   │   └── register/
│   └── (protected)/       # Protected route group
│       ├── dashboard/
│       ├── profile/
│       └── agents/
├── components/             # Reusable UI components
│   ├── common/            # Shared components (Header, Footer, Modal)
│   └── ui/                # Base UI primitives
├── contexts/              # React Context providers
│   └── AuthContext.tsx    # Authentication state
├── hooks/                 # Custom React hooks
│   └── useApi.ts          # API call utilities
├── lib/                   # Core utilities
│   ├── api/              # API client
│   ├── types/            # TypeScript definitions
│   └── utils/            # Helper functions
├── config/               # Configuration
└── styles/               # Global styles + Tailwind
```

### Key Design Decisions

1. **App Router over Pages Router**
   - File-based routing with nested layouts
   - Built-in support for React Server Components
   - Streaming and Suspense support
   - Better code splitting

2. **Client Components for Interactivity**
   - All pages use `"use client"` for authentication state access
   - AuthContext requires client-side JavaScript
   - Form handling and user interactions require client components

3. **Context API for Global State**
   - Lightweight solution for auth state
   - No external state library needed for current scope
   - Easy to test and understand

4. **Singleton API Client**
   - Centralized HTTP communication
   - Token management encapsulated
   - Type-safe API methods

5. **Custom Hooks for Reusable Logic**
   - `useApi` for async API calls with loading/error states
   - `useApiPolling` for long-running operations
   - Promotes code reuse and testability

### Component Patterns

```tsx
// Page Component Pattern
"use client";
export default function DashboardPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  // Redirect if not authenticated
  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [user, loading, router]);

  if (loading) return <Spinner />;
  if (!user) return null;

  return <DashboardContent user={user} />;
}

// Protected Route Pattern
const ProtectedRoute: FC<{ children: ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [user, loading, router]);

  if (loading) return <LoadingSpinner />;
  return user ? <>{children}</> : null;
};
```

## Consequences

### Positive

- **Modern Stack**: Latest React 19 features (React Compiler, automatic memoization)
- **Type Safety**: Strict TypeScript enforces correct API contracts
- **Developer Experience**: Fast refresh, clear file structure
- **Performance**: Automatic code splitting, optimized builds
- **Flexibility**: Can add server components later for static content

### Negative

- **Client-Heavy**: All pages are client components due to auth requirements
- **Bundle Size**: Client-side JavaScript for all pages
- **No SSR Benefits**: Cannot leverage SSR for SEO (not needed for authenticated app)
- **Context Limitations**: Deep nesting can cause unnecessary re-renders

### Neutral

- Must use `"use client"` directive explicitly
- Layout wrapping adds slight complexity
- Route groups (`(auth)`, `(protected)`) require understanding

## Alternatives Considered

### Alternative 1: Pages Router

Traditional Next.js routing with `pages/` directory.

**Rejected because**: App Router is the future direction of Next.js, provides better layouts and data fetching patterns.

### Alternative 2: Server Components with Server Actions

Use React Server Components for data fetching.

**Rejected because**: Authentication requires client-side state, making most of our pages client components anyway. Adding complexity for minimal benefit.

### Alternative 3: Redux/Zustand for State Management

External state management library.

**Rejected because**: Current scope only needs auth state. Context API is sufficient and reduces dependencies.

### Alternative 4: tRPC for Type-Safe API

End-to-end type safety with tRPC.

**Rejected because**: Requires backend changes, adds complexity. Our typed API client provides similar benefits.

## References

- [Next.js App Router Documentation](https://nextjs.org/docs/app)
- [React 19 Features](https://react.dev/blog/2024/04/25/react-19)
- [ADR-0006: API Client Design](./0006-api-client-design.md)
