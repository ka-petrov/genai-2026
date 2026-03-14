import {
  createRootRoute,
  Outlet,
  useRouter,
} from "@tanstack/react-router";

function RootErrorBoundary() {
  const router = useRouter();

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-base text-fg p-6">
      <div className="max-w-md text-center space-y-4">
        <div className="w-14 h-14 mx-auto rounded-2xl bg-status-error-subtle flex items-center justify-center">
          <svg
            className="w-7 h-7 text-status-error-text"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
            />
          </svg>
        </div>
        <h1 className="text-xl font-bold">Something went wrong</h1>
        <p className="text-sm text-fg-muted">
          An unexpected error occurred. You can try refreshing the page or going
          back to the home screen.
        </p>
        <div className="flex items-center justify-center gap-3 pt-2">
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 rounded-lg bg-surface-raised border border-border-default text-sm font-medium hover:bg-surface-overlay transition-colors cursor-pointer"
          >
            Refresh
          </button>
          <button
            onClick={() => router.navigate({ to: "/" })}
            className="px-4 py-2 rounded-lg bg-accent text-fg text-sm font-medium hover:bg-accent-hover transition-colors cursor-pointer"
          >
            Go Home
          </button>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRoute({
  component: () => <Outlet />,
  errorComponent: RootErrorBoundary,
});
