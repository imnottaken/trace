import type { Metadata } from "next";
import "./globals.css";

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
    <html lang="en">
      <body className="min-h-screen bg-trace-green text-trace-yellow antialiased">
        {children}
      </body>
    </html>
  );
}
