import type { ReactNode } from "react";

export default function Glass({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={`mi-surface ${className}`}>{children}</div>;
}
