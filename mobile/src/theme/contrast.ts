export function contrastRatio(foreground: string, background: string): number {
  const lum = (hex: string): number => {
    const c = hex.replace('#', '');
    const vals = [0, 2, 4]
      .map((i) => parseInt(c.slice(i, i + 2), 16) / 255)
      .map((v) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
    return 0.2126 * vals[0]! + 0.7152 * vals[1]! + 0.0722 * vals[2]!;
  };
  const a = lum(foreground);
  const b = lum(background);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}
