// Barrel — every consumer should import from `@/hooks/api` so the
// original `useApi.ts` location can be deleted and individual modules
// remain tree-shakable.

export { messageOf, useProject, useProjects } from "./projects";
export type { ResourceState } from "./projects";
export { useSourceStatus, useSources } from "./sources";
export type { SourceLiveStatus } from "./sources";
export { useChat } from "./chat";
export { useRequirements } from "./requirements";
export { useGenerateTasks, useTasks } from "./tasks";
export { useAuditRuns, useCoverageLinks, useLatestAudit, useRunAudit } from "./audit";
