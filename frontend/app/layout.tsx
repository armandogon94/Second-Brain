import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Toaster } from "sonner";
import { ThemeProvider } from "@/components/ThemeProvider";
import { Sidebar } from "@/components/Sidebar";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Second Brain",
  description: "Your personal knowledge base",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <div className="flex h-screen overflow-hidden">
            <Sidebar />
            <main className="flex-1 overflow-y-auto">{children}</main>
          </div>
          <Toaster richColors position="bottom-right" />
        </ThemeProvider>
      </body>
    </html>
  );
}
