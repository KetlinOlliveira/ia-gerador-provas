import { Download } from "lucide-react";
import { useState } from "react";

import { api } from "@/api/cliente";
import type { FormatoExportacao, VersaoExportacao } from "@/api/tipos";
import { useFecharAoClicarFora } from "@/hooks/use-utilitarios";

import { Button } from "./ui-button";

export const OPCOES_EXPORTACAO: { formato: FormatoExportacao; versao: VersaoExportacao; rotulo: string }[] = [
  { formato: "pdf", versao: "aluno", rotulo: "PDF para o aluno" },
  { formato: "pdf", versao: "professor", rotulo: "PDF com gabarito" },
  { formato: "docx", versao: "aluno", rotulo: "Word para o aluno" },
  { formato: "docx", versao: "professor", rotulo: "Word com gabarito" },
  { formato: "md", versao: "professor", rotulo: "Markdown com gabarito" },
];

/** Botão de download da lista de provas, com a escolha de formato e versão. */
export function MenuExportar({ provaId, titulo, disponivel }: { provaId: string; titulo: string; disponivel: boolean }) {
  const [aberto, setAberto] = useState(false);
  const ref = useFecharAoClicarFora<HTMLDivElement>(aberto, () => setAberto(false));

  return (
    <div className="exam-menu" ref={ref}>
      <Button
        variant="icon"
        onClick={() => setAberto(!aberto)}
        disabled={!disponivel}
        aria-label={`Baixar ${titulo}`}
        aria-expanded={aberto}
        title={disponivel ? "Baixar" : "Disponível quando a prova estiver pronta"}
      >
        <Download size={15} />
      </Button>
      {aberto && (
        <div className="exam-menu-popover" role="menu">
          {OPCOES_EXPORTACAO.map((opcao) => (
            <a
              key={`${opcao.formato}-${opcao.versao}`}
              role="menuitem"
              className="ui-button ui-button--ghost"
              href={api.urlExportacao(provaId, opcao.formato, opcao.versao)}
              download
              onClick={() => setAberto(false)}
            >
              {opcao.rotulo}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
