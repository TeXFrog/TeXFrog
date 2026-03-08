/**
 * Port of texfrog/parser.py resolve_tag_ranges.
 *
 * Resolves a tag string like "G0,G3-G5" to a Set of labels,
 * where ranges are expanded by position in orderedLabels.
 */
export function resolveTagRanges(
  tagString: string,
  orderedLabels: string[]
): Set<string> {
  const labelIndex = new Map<string, number>();
  for (let i = 0; i < orderedLabels.length; i++) {
    labelIndex.set(orderedLabels[i], i);
  }

  const result = new Set<string>();

  for (const rawToken of tagString.split(",")) {
    const token = rawToken.trim();
    if (!token) {
      continue;
    }

    if (token.includes("-")) {
      // Could be a range like "G3-G5" or a single label containing "-".
      // Try splitting on "-" left-to-right until both halves are valid labels.
      const parts = token.split("-");
      let resolved = false;

      for (let splitAt = 1; splitAt < parts.length; splitAt++) {
        const start = parts.slice(0, splitAt).join("-");
        const end = parts.slice(splitAt).join("-");
        const iStart = labelIndex.get(start);
        const iEnd = labelIndex.get(end);

        if (iStart !== undefined && iEnd !== undefined) {
          if (iStart > iEnd) {
            throw new Error(
              `Range '${token}' is reversed: '${start}' comes after '${end}' in the game order.`
            );
          }
          for (let i = iStart; i <= iEnd; i++) {
            result.add(orderedLabels[i]);
          }
          resolved = true;
          break;
        }
      }

      if (!resolved) {
        // Treat as a literal label
        result.add(token);
      }
    } else {
      result.add(token);
    }
  }

  return result;
}
