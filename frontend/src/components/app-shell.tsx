import { useQuery } from "@tanstack/react-query";
import { Link, useRouterState } from "@tanstack/react-router";
import { Sparkles } from "lucide-react";
import type { ReactNode } from "react";

import { api } from "@/api/cliente";

const links = [
  { to: "/" as const, label: "Criar prova", ativoEm: (caminho: string) => caminho === "/" },
  {
    to: "/minhas-provas" as const,
    label: "Minhas provas",
    ativoEm: (caminho: string) => caminho.startsWith("/minhas-provas") || caminho.startsWith("/provas"),
  },
  { to: "/configuracoes" as const, label: "Configurações", ativoEm: (caminho: string) => caminho === "/configuracoes" },
];

function StatusDoServico() {
  const { data, isError } = useQuery({
    queryKey: ["saude"],
    queryFn: api.saude,
    refetchInterval: 30_000,
    retry: false,
  });
  const situacao = isError ? "offline" : data && !data.llm_configurado ? "sem-chave" : data ? "online" : "carregando";
  const descricao = {
    online: "API e modelo de IA disponíveis",
    "sem-chave": "API no ar, mas sem chave da Groq configurada",
    offline: "API indisponível",
    carregando: "Verificando a API",
  }[situacao];

  return (
    <div className={`workspace workspace--${situacao}`} title={descricao} aria-label={descricao}>
      <Sparkles size={17} strokeWidth={1.6} />
      <span>AI Workspace</span>
      <i />
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const caminho = useRouterState({ select: (estado) => estado.location.pathname });
  return (
    <div className="app-frame">
      <header className="site-header">
        <Link to="/" className="brand" aria-label="PROVAI, início">
          PROVAI<span className="brand-dot">.</span>
        </Link>
        <nav className="primary-nav" aria-label="Navegação principal">
          {links.map(({ to, label, ativoEm }) => (
            <Link key={to} to={to} className={`nav-link ${ativoEm(caminho) ? "nav-link--active" : ""}`}>
              {label}
            </Link>
          ))}
        </nav>
        <StatusDoServico />
      </header>
      <main>{children}</main>
    </div>
  );
}
