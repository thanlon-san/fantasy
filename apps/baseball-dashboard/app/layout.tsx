import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster"
import { ThemeProvider } from "@/components/theme-provider"
import { Providers } from "./providers"
import { MobileNav } from "@/components/mobile-nav"

export const metadata: Metadata = {
  title: "Fantasy Baseball Dashboard",
  description: "Your year-round competitive advantage",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased pb-14 md:pb-0">
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <Providers>
            {children}
          </Providers>
          <Toaster />
          <MobileNav />
        </ThemeProvider>
      </body>
    </html>
  );
}
