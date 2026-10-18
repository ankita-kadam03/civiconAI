import { useEffect, useState } from "react";

function fileKey(file: File) {
  return `${file.name}:${file.size}:${file.lastModified}`;
}

/** Stable blob URLs for file previews; revokes only when files are removed or on unmount. */
export function useFileObjectUrls(files: File[]): string[] {
  const fingerprint = files.map(fileKey).join("|");
  const [urls, setUrls] = useState<string[]>([]);

  useEffect(() => {
    const next = files.map((file) => URL.createObjectURL(file));
    setUrls(next);
    return () => {
      next.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [fingerprint]);

  return urls.length === files.length ? urls : [];
}
