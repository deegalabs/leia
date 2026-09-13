/* Task status as the person sees it (pt-BR, plain words). Lawyer and citizen read "pronta" differently.
   LeIA: review flow. "pronta" on a lawyer-owned task waits for the lawyer; "enviada" is released to the citizen;
   the public route says "revisao" while the lawyer reviews. Citizen-owned tasks skip the review. */
import { m } from "./i18n";

export type ChipTone = "ok" | "pending" | "neutral" | "danger";
export function statusInfo(status: string, forCitizen: boolean, origem?: "advogado" | "cidadao"): { label: string; tone: ChipTone } {
  switch (status) {
    case "assinada": case "concluida": return { label: m.panel.status.understood, tone: "ok" };
    case "pronta":
      if (forCitizen) return { label: m.panel.status.readyCitizen, tone: "neutral" };
      return origem === "cidadao" ? { label: m.panel.status.readyCitizenOwned, tone: "neutral" } : { label: m.panel.status.readyLawyer, tone: "pending" };
    case "enviada": return { label: forCitizen ? m.panel.status.readyCitizen : m.panel.status.released, tone: "neutral" };
    case "revisao": return { label: m.panel.status.inReview, tone: "pending" };
    case "falhou": return { label: m.panel.status.failed, tone: "danger" };
    default: return { label: m.panel.status.preparing, tone: "pending" };
  }
}
export const isReady = (status: string) => status === "pronta" || status === "enviada" || status === "assinada" || status === "concluida";
export const isSettled = (status: string) => isReady(status) || status === "falhou";
/* The lawyer still has to approve: only lawyer-owned tasks in "pronta". */
export const needsReview = (status: string, origem?: string) => status === "pronta" && origem !== "cidadao";
/* The review page has content to show (the service answers 409 before that). */
export const hasReview = (status: string) => isReady(status);
