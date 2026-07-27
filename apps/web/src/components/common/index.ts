// Public surface for common (cross-feature) components.
//
// These components are NOT domain-specific — they apply anywhere in the
// app. For domain-specific (project/chat/task) components, see
// `src/features/<feature>/index.ts`.

export { ConfirmDialog } from "./ConfirmDialog";
export type { ConfirmDialogProps } from "./ConfirmDialog";
export { EmptyState } from "./EmptyState";
export { SourceFileInput } from "./SourceFileInput";
export { SubmitButton } from "./SubmitButton";
