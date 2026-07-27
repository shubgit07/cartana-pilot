// Seed script — creates the dev user + a small demo project so the UI is
// not empty on first boot. Run via `npm run db:seed`.

import { PrismaClient } from "@prisma/client";
import { config } from "../src/config";

const prisma = new PrismaClient();

async function main() {
  const user = await prisma.user.upsert({
    where: { id: config.DEV_USER_ID },
    update: {},
    create: {
      id: config.DEV_USER_ID,
      email: config.DEV_USER_EMAIL,
      name: config.DEV_USER_NAME,
    },
  });

  const existing = await prisma.project.findFirst({
    where: { userId: user.id, name: "Demo: Student Capstone Brief" },
  });
  if (existing) {
    console.log(`Seed: project already exists (${existing.id}). Skipping.`);
    return;
  }

  const project = await prisma.project.create({
    data: {
      userId: user.id,
      name: "Demo: Student Capstone Brief",
      description: "Sample project so the UI is not empty. Delete or ignore it.",
    },
  });

  // Add a starter text source so the user can immediately click 'chat'.
  const text = [
    "Final Year Capstone Project — Group C",
    "",
    "Deadline: 2026-12-15",
    "",
    "Project goals:",
    "- Build an admin dashboard with role-based access control.",
    "- Implement analytics charts for monthly active users.",
    "- Provide CSV export for all transactional tables.",
    "- Send weekly summary emails to admins.",
    "- Authentication must use email + OTP (no passwords).",
    "",
    "Acceptance criteria:",
    "- All routes require authentication.",
    "- Admin role can create, edit, and delete resources.",
    "- Employee role can only view.",
    "- Reports must be downloadable as PDF and CSV.",
    "- The system must handle at least 1000 concurrent users.",
  ].join("\n");

  await prisma.source.create({
    data: {
      projectId: project.id,
      userId: user.id,
      filename: "capstone-brief.txt",
      kind: "text",
      status: "uploaded",
      storageKey: "seed/capstone-brief.txt",
      mimeType: "text/plain",
      sizeBytes: Buffer.byteLength(text, "utf8"),
    },
  });

  console.log(`Seed complete. Demo project id: ${project.id}`);
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(() => prisma.$disconnect());