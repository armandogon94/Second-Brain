/**
 * Convert [[wikilinks]] in markdown text to HTML anchor tags pointing to /wiki/{slug}.
 */
export function slugify(title: string): string {
  return title
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "") // strip diacritics
    .replace(/[^\w\s-]/g, "")
    .trim()
    .toLowerCase()
    .replace(/[-\s]+/g, "-") || "untitled";
}

export function convertWikilinks(text: string): string {
  return text.replace(/\[\[([^\]]+)\]\]/g, (_, title: string) => {
    const slug = slugify(title);
    return `[${title}](/wiki/${slug})`;
  });
}
