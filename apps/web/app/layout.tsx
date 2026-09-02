import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TeleCommerce",
  description: "Shop from Web. Shop from Telegram.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
