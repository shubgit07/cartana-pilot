// Public surface for toasts. Importing from "@/components/ui/toast"
// yields stable React entry points only — implementation detail lives
// in ./ToastProvider.

export { ToastProvider, useToast } from "./ToastProvider";
export type { ToastInput, ToastVariant } from "./ToastProvider";
