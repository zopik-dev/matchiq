import type { ReactNode } from "react";

export default function Glass({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-2xl border border-white/[0.07] bg-[#0B111E]/80 shadow-[0_12px_40px_rgba(0,0,0,0.5)] backdrop-blur-2xl ${className}`}
    >
      {children}
    </div>
  );
}
