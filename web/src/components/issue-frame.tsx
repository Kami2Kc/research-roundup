"use client";

import { useRef } from "react";

// Shows a newsletter in an iframe sized to its content (same origin, so we can read its height).
export function IssueFrame({ src, title }: { src: string; title: string }) {
  const ref = useRef<HTMLIFrameElement>(null);

  function fitToContent() {
    const doc = ref.current?.contentDocument;
    if (ref.current && doc)
      ref.current.style.height = `${doc.documentElement.scrollHeight}px`;
  }

  return (
    <iframe
      ref={ref}
      src={src}
      title={title}
      onLoad={fitToContent}
      className="h-[80vh] w-full col-span-2 rounded-lg border bg-white"
    />
  );
}
