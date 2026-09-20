/* The landing is read before anyone sees the engine run, so a promise made here is the one a visitor has no
   way to check. A promise that ties what the reader gets to the kind of document can only be published once
   the pipeline has a step that tells one kind from another. Since 20/09/2026 it has one: T0 reads the species
   before anything is extracted, and it is what picks the vocabulary the later steps use to name the parties.
   So the first test below flipped: it now holds that step in place, because dropping it would quietly turn
   any such copy back into a promise nobody can keep. The second one still guards the copy, which has not been
   rewritten: the engine can back that claim now, but nobody has written a sentence that is true about it yet,
   and a claim is only allowed here once someone does. STEP_NAMES is this app's own list of the steps the
   service reports for every task. */
import { describe, expect, it } from "vitest";

import { faq } from "./landing";
import { STEP_NAMES } from "./mock";

const sentencesOf = (text: string) => text.split(/(?<=[.?!])\s+/).filter(Boolean);
const KIND_OF_DOCUMENT = /tipos? d[eo] documento/i;
const VARIES = /\b(muda|mudam|varia|variam|depende|dependem|conforme|de acordo com)\b/i;
const promisesByKindOfDocument = (text: string) =>
  sentencesOf(text).filter((s) => KIND_OF_DOCUMENT.test(s) && VARIES.test(s));

describe("what the landing promises about the engine", () => {
  it("runs a pipeline whose first step tells one kind of document from another", () => {
    expect(STEP_NAMES.filter((step) => /\btipo\b/i.test(step))).toEqual(["Reconhecer o tipo do documento"]);
    expect(STEP_NAMES[0]).toBe("Reconhecer o tipo do documento");
  });

  it("promises nothing that changes with the kind of document", () => {
    expect(faq.flatMap((entry) => promisesByKindOfDocument(entry.a))).toEqual([]);
  });
});
