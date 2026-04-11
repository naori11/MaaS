import "./globals.css";
import { AppRouteShell } from "./_components/app-route-shell";
import { MotionProvider } from "./_components/motion/motion-provider";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <MotionProvider>
          <AppRouteShell>{children}</AppRouteShell>
        </MotionProvider>
      </body>
    </html>
  );
}
