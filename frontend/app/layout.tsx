import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Providers } from "@/components/providers";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

export const metadata: Metadata = {
  title: "LOOD — حمّل الوسائط بوضوح",
  description: "حلّل الروابط العامة وحمّل الصيغة والجودة المتاحة التي تختارها.",
  applicationName: "LOOD",
  manifest: `${basePath}/manifest.webmanifest`,
  appleWebApp: { capable: true, title: "LOOD", statusBarStyle: "black-translucent" },
  icons: {
    icon: [{ url: `${basePath}/icons/icon-192.png`, sizes: "192x192", type: "image/png" }],
    apple: [{ url: `${basePath}/icons/icon-192.png`, sizes: "192x192", type: "image/png" }]
  }
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f4f7ff" },
    { media: "(prefers-color-scheme: dark)", color: "#080b17" }
  ]
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ar" dir="rtl" suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
