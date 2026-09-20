/* The landing is read before anyone sees the engine run, so a promise made here is the one a visitor has no
   way to check. A promise that ties what the reader gets to the kind of document can only be published once
   the pipeline has a step that tells one kind from another: until then the copy has to describe the single
   path every PDF takes. STEP_NAMES is this app's own list of the steps the service reports for every task. */
import { describe, expect, it } from "vitest";

import { faq } from "./landing";
import { STEP_NAMES } from "./mock";

const sentencesOf = (text: string) => text.split(/(?<=[.?!])\s+/).filter(Boolean);
const KIND_OF_DOCUMENT = /tipos? d[eo] documento/i;
const VARIES = /\b(muda|mudam|varia|variam|depende|dependem|conforme|de acordo com)\b/i;
const promisesByKindOfDocument = (text: string) =>
  sentencesOf(text).filter((s) => KIND_OF_DOCUMENT.test(s) && VARIES.test(s));

describe("what the landing promises about the engine", () => {
  it("runs one pipeline, with no step that tells one kind of document from another", () => {
    expect(STEP_NAMES.filter((step) => /\btipo/i.test(step))).toEqual([]);
  });

  it("promises nothing that changes with the kind of document", () => {
    expect(faq.flatMap((entry) => promisesByKindOfDocument(entry.a))).toEqual([]);
  });
});
