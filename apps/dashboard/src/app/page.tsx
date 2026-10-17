"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

// Klient tomonda yo'naltirish — statik eksportda (Node serversiz) ham ishlaydi
export default function Home() {
  const router = useRouter();
  useEffect(() => { router.replace("/overview"); }, [router]);
  return null;
}
