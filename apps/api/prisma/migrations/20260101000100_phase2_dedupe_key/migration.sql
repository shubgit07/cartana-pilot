-- Phase 2: Add dedupeKey to Requirement and Task for idempotent re-extraction.
--
-- The extractor computes a deterministic hash from (sourceId + normalized title)
-- and stores it here. Re-running extraction on the same source can then upsert
-- by dedupeKey instead of duplicating rows.
--
-- User-edited / user-accepted / user-rejected rows are NEVER overwritten by
-- the extractor; this column just lets us recognize them.

-- AlterTable
ALTER TABLE "Requirement" ADD COLUMN "dedupeKey" TEXT;

-- AlterTable
ALTER TABLE "Task" ADD COLUMN "dedupeKey" TEXT;

-- CreateIndex
CREATE INDEX "Requirement_dedupeKey_idx" ON "Requirement"("dedupeKey");

-- CreateIndex
CREATE INDEX "Task_dedupeKey_idx" ON "Task"("dedupeKey");