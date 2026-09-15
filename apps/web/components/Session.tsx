"use client";
import { useEffect, type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LayoutList, LogIn, LogOut } from "lucide-react";
import { logout, useAuth } from "@/lib/auth";
import { m } from "@/lib/i18n";

/* Sign-in / panel / sign-out links. "dark" sits on navy (headers, landing hero). */
export function AuthNav({ dark = true }: { dark?: boolean }) {
  const { usuario, ready } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const cls = `inline-flex min-h-[44px] items-center gap-1.5 whitespace-nowrap rounded-button px-2 text-[0.95rem] font-bold underline underline-offset-4 sm:px-2.5 ${dark ? "text-paper hover:bg-white/10" : "text-teal-deep hover:bg-teal-soft"}`;
  if (!ready) return <span className="min-h-[44px]" aria-hidden />;
  if (!usuario) return <Link href="/entrar" className={cls}><LogIn size={18} aria-hidden /> {m.auth.signIn}</Link>;
  return (
    <nav aria-label="Sua conta" className="flex shrink-0 items-center gap-0.5 sm:gap-1">
      <span className={`hidden text-[0.95rem] sm:inline ${dark ? "text-paper/85" : "text-ink-2"}`}>{usuario.nome.split(" ")[0]}</span>
      {!pathname.startsWith("/painel") && <Link href="/painel" className={cls}><LayoutList size={18} aria-hidden /> {m.auth.myPanel}</Link>}
      <button type="button" className={cls} onClick={async () => { await logout(); router.push("/"); }}><LogOut size={18} aria-hidden /> {m.auth.signOut}</button>
    </nav>
  );
}

/* Sends visitors to /entrar?next=... once the stored session has been read. */
export function RequireAuth({ next, children }: { next: string; children: ReactNode }) {
  const { usuario, ready } = useAuth();
  const router = useRouter();
  useEffect(() => { if (ready && !usuario) router.replace(`/entrar?next=${encodeURIComponent(next)}`); }, [ready, usuario, next, router]);
  if (!ready || !usuario) return <p role="status" className="text-ink-2">{m.common.loading}</p>;
  return <>{children}</>;
}
