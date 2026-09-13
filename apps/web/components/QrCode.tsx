"use client";
import { useEffect, useState } from "react";
import QRCode from "qrcode";

export function QrCode({ value, label }: { value: string; label: string }) {
  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    const absolute = value.startsWith("/") ? `${window.location.origin}${value}` : value;
    QRCode.toDataURL(absolute, { width: 232, margin: 1, color: { dark: "#081820", light: "#FFFFFF" } }).then((u) => { if (alive) setSrc(u); }).catch(() => setSrc(null));
    return () => { alive = false; };
  }, [value]);
  if (!src) return <div className="mx-auto h-[232px] w-[232px] rounded bg-muted" role="status" aria-label="Gerando o QR" />;
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt={label} width={232} height={232} className="mx-auto" />;
}
