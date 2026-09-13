import { Suspense } from "react";
import { AuthForm } from "@/components/AuthForm";

export const metadata = { title: "Entrar" };

export default function SignInPage() {
  return <Suspense fallback={null}><AuthForm /></Suspense>;
}
