/* The stamp is the one part of the receipt that is not ready when the citizen finishes, so the screen has to
   name which of the three states it is in (ADR-0010). Deriving it from the missing .ots file alone is what made
   every stampless receipt promise "it arrives in a few minutes", including the ones nobody was stamping. */
import { fmt, m } from "./i18n";

export const OTS_ABSENT = "ausente";
export const OTS_PENDING = "pendente";
export const OTS_CONFIRMED = "confirmado";
export type StampState = typeof OTS_ABSENT | typeof OTS_PENDING | typeof OTS_CONFIRMED;

/* What the verification endpoint says about the stamp. Only otsPresent is guaranteed: the in-app mock
   (lib/mock.ts), which answers when no service is configured, still reports nothing else. */
export type StampSource = { otsPresent: boolean; otsState?: string | null; otsBlockHeight?: number | null; otsLastAttempt?: string | null };
export type StampTone = "ok" | "pending" | "neutral";
export type StampView = { state: StampState; tone: StampTone; chip: string; text: string; hasProof: boolean };

function stateOf(r: StampSource): StampState {
  if (r.otsState === OTS_PENDING || r.otsState === OTS_CONFIRMED) return r.otsState;
  if (r.otsState === OTS_ABSENT) return OTS_ABSENT;
  /* otsPresent === (otsState !== "ausente"), so on its own it separates no proof from some proof and never
     a calendar promise from a proof already in a block. Downgrade to the promise instead of claiming one. */
  return r.otsPresent ? OTS_PENDING : OTS_ABSENT;
}

export function stampView(r: StampSource): StampView {
  const state = stateOf(r);
  if (state === OTS_CONFIRMED) {
    const bloco = typeof r.otsBlockHeight === "number" ? r.otsBlockHeight : null;
    return {
      state, tone: "ok", chip: m.stamp.confirmedChip, hasProof: true,
      text: bloco === null ? m.stamp.confirmedNoBlock : fmt(m.stamp.confirmed, { bloco }),
    };
  }
  if (state === OTS_PENDING) return { state, tone: "pending", chip: m.stamp.pendingChip, text: m.stamp.pending, hasProof: true };
  return { state, tone: "neutral", chip: m.stamp.absentChip, text: m.stamp.absent, hasProof: false };
}
