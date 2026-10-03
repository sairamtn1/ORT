import type { Metadata } from "next";
import "mapbox-gl/dist/mapbox-gl.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "ORT — Find. Reserve. Park.",
  description: "ORT makes it easier to find and reserve parking near you.",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
