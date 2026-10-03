import type { ButtonHTMLAttributes, ReactNode } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "outline" | "ghost" | "icon" | "tab";
  children: ReactNode;
};

export function Button({ variant = "outline", className = "", type = "button", children, ...props }: Props) {
  return (
    <button type={type} className={`ui-button ui-button--${variant} ${className}`} {...props}>
      {children}
    </button>
  );
}
