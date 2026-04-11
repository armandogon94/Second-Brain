import { describe, it, expect } from "vitest";
import { convertWikilinks } from "@/lib/wiki-utils";

describe("convertWikilinks", () => {
  it("converts single wikilink to Next.js link", () => {
    const result = convertWikilinks("See [[Machine Learning]] for details");
    expect(result).toContain("/wiki/machine-learning");
    expect(result).toContain("Machine Learning");
  });

  it("converts multiple wikilinks", () => {
    const result = convertWikilinks(
      "Both [[Python]] and [[Rust]] are great"
    );
    expect(result).toContain("/wiki/python");
    expect(result).toContain("/wiki/rust");
  });

  it("leaves text without wikilinks unchanged", () => {
    const input = "No links here";
    expect(convertWikilinks(input)).toBe(input);
  });

  it("handles special characters in titles", () => {
    const result = convertWikilinks("See [[What's New in Python 3.12?]]");
    expect(result).toContain("/wiki/whats-new-in-python-312");
  });

  it("handles empty string", () => {
    expect(convertWikilinks("")).toBe("");
  });

  it("preserves surrounding text", () => {
    const result = convertWikilinks("Start [[Link]] end");
    expect(result).toMatch(/^Start .* end$/);
  });
});
