import type { ReactNode } from "react";

export default function Glass({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-xl border border-white/[0.06] bg-[#0F1626] shadow-sm ${className}`}>
      {children}
    </div>
  );
}
