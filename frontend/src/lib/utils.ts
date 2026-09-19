import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatPassengers(value: number) {
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(value)
}

export function formatSigned(value: number, suffix = "") {
  const formatted = new Intl.NumberFormat("ru-RU", {
    maximumFractionDigits: 1,
    signDisplay: "always",
  }).format(value)
  return `${formatted}${suffix}`
}
