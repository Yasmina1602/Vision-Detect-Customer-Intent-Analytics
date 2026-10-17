import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: { default: "Vision Detect", template: "%s · Vision Detect" },
  description: "Rasm orqali qidiruv va xaridor talablari analitikasi",
};

export const viewport: Viewport = { themeColor: "#6d28d9", width: "device-width", initialScale: 1 };

// Mavzuni sahifa chizilishidan oldin qo'llash (miltillashsiz)
const themeScript = `try{var t=localStorage.getItem('vd_theme');if(t==='dark'||(!t&&matchMedia('(prefers-color-scheme: dark)').matches))document.documentElement.classList.add('dark')}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="uz" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
