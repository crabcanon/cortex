import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { siteDescription, siteTitle } from "@/lib/shared";

export const metadata: Metadata = {
  title: { absolute: siteTitle },
  description: siteDescription,
  alternates: { canonical: "/" },
};

export default function HomePage() {
  redirect("/zh/docs/cortex");
}
