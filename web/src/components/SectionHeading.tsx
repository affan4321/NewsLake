import type { ReactNode } from "react";
import { Reveal } from "./Reveal";

export default function SectionHeading({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: ReactNode;
  children?: ReactNode;
}) {
  return (
    <Reveal>
      <p className="eyebrow">{eyebrow}</p>
      <h2 className="display mt-4 text-4xl md:text-6xl">{title}</h2>
      {children ? (
        <p className="mt-5 max-w-2xl text-base leading-relaxed text-muted">{children}</p>
      ) : null}
    </Reveal>
  );
}
