import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'SyllExtract Acquisition Pro — Academic Book Discovery & Legal Access Agent',
  description:
    'SaaS academic book discovery platform with explainable match confidence, multi-source bibliographic aggregation, independent licensing verification, and server-side acquisition audit management.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                const savedTheme = localStorage.getItem('syllex_theme');
                if (savedTheme === 'dark' || (!savedTheme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
                  document.documentElement.classList.add('dark');
                } else {
                  document.documentElement.classList.remove('dark');
                }
              } catch (_) {}
            `,
          }}
        />
      </head>
      <body className="min-h-screen antialiased bg-slate-50 text-slate-900 dark:bg-[#0b1120] dark:text-slate-100 transition-colors duration-150">
        {children}
      </body>
    </html>
  );
}
