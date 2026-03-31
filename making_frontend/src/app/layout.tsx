import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PalX Blender Console",
  description: "LangGraph-driven architectural space design and Blender output console",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="h-full antialiased">
      <body className="min-h-full bg-[var(--color-background)] text-[var(--color-foreground)]">
        {children}
      </body>
    </html>
  );
}
