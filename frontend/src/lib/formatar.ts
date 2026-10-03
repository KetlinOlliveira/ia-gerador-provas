export function formatarData(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR");
}

export function formatarDuracao(segundos: number | null): string | null {
  if (segundos === null) return null;
  if (segundos < 60) return `${Math.round(segundos)} s`;
  const minutos = Math.floor(segundos / 60);
  return `${minutos} min ${Math.round(segundos % 60)} s`;
}

export function formatarNota(nota: number): string {
  return nota.toLocaleString("pt-BR", { maximumFractionDigits: 1 });
}
