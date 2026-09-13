/* Task status as the person sees it (pt-BR, plain words). Lawyer and citizen read "pronta" differently. */
import { m } from "./i18n";

export type ChipTone = "ok" | "pending" | "neutral" | "danger";
export function statusInfo(status: string, forCitizen: boolean): { label: string; tone: ChipTone } {
  switch (status) {
    case "assinada": case "concluida": return { label: m.panel.status.understood, tone: "ok" };
    case "pronta": return { label: forCitizen ? m.panel.status.readyCitizen : m.panel.status.readyLawyer, tone: "neutral" };
    case "falhou": return { label: m.panel.status.failed, tone: "danger" };
    default: return { label: m.panel.status.preparing, tone: "pending" };
  }
}
export const isReady = (status: string) => status === "pronta" || status === "assinada" || status === "concluida";
export const isSettled = (status: string) => isReady(status) || status === "falhou";
