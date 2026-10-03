import type { QueryClient } from "@tanstack/react-query";
import {
  createRootRouteWithContext,
  HeadContent,
  Link,
  Outlet,
  useRouter,
  type ErrorComponentProps,
} from "@tanstack/react-router";

import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui-button";

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  head: () => ({ meta: [{ title: "PROVAI" }] }),
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootComponent() {
  return (
    <>
      {/* React 19 leva <title> e <meta> para o <head> sozinho. */}
      <HeadContent />
      <AppShell>
        <Outlet />
      </AppShell>
    </>
  );
}

function NotFoundComponent() {
  return (
    <div className="status-page">
      <span className="sparkle-mark">✧</span>
      <h1>404</h1>
      <h2>Página não encontrada</h2>
      <p>A página que você procura não existe ou foi movida.</p>
      <Link to="/" className="ui-button ui-button--primary status-page-action">
        Voltar ao início
      </Link>
    </div>
  );
}

function ErrorComponent({ error, reset }: ErrorComponentProps) {
  const router = useRouter();
  console.error(error);
  return (
    <div className="status-page">
      <span className="sparkle-mark">✧</span>
      <h2>Esta página não carregou</h2>
      <p>Algo deu errado. Tente de novo ou volte ao início.</p>
      <div className="status-page-actions">
        <Button
          variant="primary"
          className="status-page-action"
          onClick={() => {
            void router.invalidate();
            reset();
          }}
        >
          Tentar novamente
        </Button>
        <Link to="/" className="ui-button ui-button--outline status-page-action">
          Voltar ao início
        </Link>
      </div>
    </div>
  );
}
