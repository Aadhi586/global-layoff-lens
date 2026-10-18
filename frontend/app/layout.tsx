import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Global Layoff Lens — Explore workforce trends",
  description: "An interactive EDA project for exploring recorded global layoff patterns.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
