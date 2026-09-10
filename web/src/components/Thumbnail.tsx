"use client";

import { useState } from "react";

/*
 * Thumbnails are hotlinked from 800+ arbitrary publisher CDNs, and a meaningful slice of
 * them refuse the request (Gannett returns 406 to non-browser referrers, others 403 or
 * time out). Without a fallback those render as a broken-image box, so any load failure
 * swaps in the medallion gradient instead.
 *
 * Plain <img> rather than next/image on purpose: every one of those domains would
 * otherwise need allowlisting in next.config.
 */
export default function Thumbnail({ src, alt = "" }: { src: string | null; alt?: string }) {
  const [failed, setFailed] = useState(false);

  if (!src || failed) {
    return <div className="bg-medallion h-full w-full opacity-20" />;
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={alt}
      loading="lazy"
      onError={() => setFailed(true)}
      className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
    />
  );
}
