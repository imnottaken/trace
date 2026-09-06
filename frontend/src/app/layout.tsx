import type { Metadata } from "next";
import { Playfair_Display, JetBrains_Mono, Rozha_One } from "next/font/google";
import "./globals.css";

const playfair = Playfair_Display({
  subsets: ["latin"],
  variable: "--font-playfair",
  weight: ["400", "600", "700", "900"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["300", "400", "500", "700", "800"],
  display: "swap",
});

const rozhaOne = Rozha_One({
  subsets: ["latin", "devanagari"],
  variable: "--font-devanagari",
  weight: ["400"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "TRACE — चेहरा → सबूत",
  description: "DISCOVER · VERIFY · PROVE — Face Identification & Blockchain Verification",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${playfair.variable} ${jetbrainsMono.variable} ${rozhaOne.variable}`}
    >
      <body className="min-h-screen bg-trace-green text-trace-yellow font-mono antialiased selection:bg-trace-pink selection:text-white">
        {children}
      </body>
    </html>
  );
}
