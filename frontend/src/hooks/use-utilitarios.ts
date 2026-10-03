import { useEffect, useRef, useState, type RefObject } from "react";

/** O valor só muda depois de `atraso` ms parado; evita uma consulta por tecla digitada. */
export function useValorComAtraso<T>(valor: T, atraso = 300): T {
  const [atrasado, setAtrasado] = useState(valor);
  useEffect(() => {
    const temporizador = window.setTimeout(() => setAtrasado(valor), atraso);
    return () => window.clearTimeout(temporizador);
  }, [valor, atraso]);
  return atrasado;
}

/** Chama `aoFechar` em clique fora do elemento ou na tecla Esc, enquanto `ativo`. */
export function useFecharAoClicarFora<T extends HTMLElement>(
  ativo: boolean,
  aoFechar: () => void,
): RefObject<T | null> {
  const ref = useRef<T>(null);
  const aoFecharRef = useRef(aoFechar);
  aoFecharRef.current = aoFechar;

  useEffect(() => {
    if (!ativo) return;
    const clique = (evento: MouseEvent) => {
      if (ref.current && !ref.current.contains(evento.target as Node)) aoFecharRef.current();
    };
    const tecla = (evento: KeyboardEvent) => {
      if (evento.key === "Escape") aoFecharRef.current();
    };
    document.addEventListener("mousedown", clique);
    document.addEventListener("keydown", tecla);
    return () => {
      document.removeEventListener("mousedown", clique);
      document.removeEventListener("keydown", tecla);
    };
  }, [ativo]);

  return ref;
}
