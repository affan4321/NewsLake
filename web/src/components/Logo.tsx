/*
 * A static stand-in for the hero's animated dot-globe (Globe.tsx) — same idea, same
 * palette, but hand-placed rather than computed, since a favicon has to read clearly at
 * 16px where a genuine Fibonacci-sphere point cloud would just blur into noise.
 *
 * Colors are hardcoded hex, not Tailwind classes: this markup is duplicated verbatim in
 * src/app/icon.svg (a static file, which can't consume Tailwind's @theme tokens), so the
 * two stay in sync by construction. If the palette in globals.css ever changes, update
 * both.
 */
export default function Logo({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" fill="none" className={className} aria-hidden>
      <defs>
        <linearGradient id="nl-logo-medallion" x1="6%" y1="0%" x2="94%" y2="30%">
          <stop offset="0%" stopColor="#c77c46" />
          <stop offset="55%" stopColor="#9aaec4" />
          <stop offset="100%" stopColor="#e0b23e" />
        </linearGradient>
      </defs>

      <circle cx="32" cy="32" r="27" stroke="url(#nl-logo-medallion)" strokeWidth="3" opacity="0.95" />

      <ellipse cx="32" cy="32" rx="27" ry="8" stroke="#9aaec4" strokeWidth="1" opacity="0.25" />
      <ellipse cx="32" cy="32" rx="9" ry="27" stroke="#9aaec4" strokeWidth="1" opacity="0.2" />

      <circle cx="19" cy="17" r="2.4" fill="#edf0f5" />
      <circle cx="35" cy="14" r="2.4" fill="#e0b23e" />
      <circle cx="46" cy="26" r="2.4" fill="#9aaec4" />
      <circle cx="40" cy="41" r="2.4" fill="#c77c46" />
      <circle cx="24" cy="45" r="2.4" fill="#edf0f5" />
      <circle cx="17" cy="31" r="2.2" fill="#9aaec4" />

      <circle cx="26" cy="22" r="6" stroke="#38bdf8" strokeWidth="1" opacity="0.35" />
      <circle cx="26" cy="22" r="2.6" fill="#38bdf8" />
      <circle cx="36" cy="30" r="5.5" stroke="#38bdf8" strokeWidth="1" opacity="0.3" />
      <circle cx="36" cy="30" r="2.4" fill="#38bdf8" />
    </svg>
  );
}
