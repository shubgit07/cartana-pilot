"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import * as React from "react";
import { ArrowLeft } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { SubmitButton } from "@/components/common/SubmitButton";
import { projectsApi, ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";

const MAX_NAME = 120;
const MAX_DESCRIPTION = 2000;

/** Show the counter only once the value is close to the cap. */
const COUNTER_THRESHOLD = 0.8;

export function NewProjectForm() {
  const router = useRouter();
  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [touched, setTouched] = React.useState(false);

  const nameError = touched && name.trim().length === 0 ? "Name is required" : null;

  const inputRef = React.useRef<HTMLInputElement | null>(null);
  React.useEffect(() => {
    inputRef.current?.focus();
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setTouched(true);
    if (!name.trim()) {
      inputRef.current?.focus();
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const project = await projectsApi.create({
        name: name.trim(),
        description: description.trim() ? description.trim() : null,
      });
      router.push(`/projects/${project.id}`);
    } catch (e: unknown) {
      setError(e instanceof ApiError ? e.message : "Failed to create project");
    } finally {
      setSubmitting(false);
    }
  }

  const showNameCount = name.length >= MAX_NAME * COUNTER_THRESHOLD;
  const showDescCount = description.length >= MAX_DESCRIPTION * COUNTER_THRESHOLD;

  return (
    <div className="mx-auto max-w-xl animate-fade-in space-y-6">
      <nav>
        <Link
          href="/"
          className={cn(
            "group inline-flex items-center gap-1.5 rounded-sm text-sm text-muted-foreground",
            "transition-colors hover:text-foreground",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          )}
        >
          <ArrowLeft
            className="h-3.5 w-3.5 transition-transform duration-200 ease-out-expo group-hover:-translate-x-0.5"
            aria-hidden="true"
          />
          All projects
        </Link>
      </nav>

      <Card>
        <CardHeader className="gap-1 border-b border-border/70">
          <span className="eyebrow">Create</span>
          <CardTitle className="font-serif text-xl">New project</CardTitle>
          <CardDescription>
            Name it clearly. You can upload documents on the next screen.
          </CardDescription>
        </CardHeader>

        <CardContent className="pt-5">
          <form onSubmit={onSubmit} className="space-y-4" noValidate>
            <div className="space-y-1.5">
              <div className="flex items-baseline justify-between gap-2">
                <Label htmlFor="projectName">
                  Name{" "}
                  <span className="text-danger" aria-hidden="true">
                    *
                  </span>
                </Label>
                {showNameCount && (
                  <span className="text-2xs text-muted-foreground tabular" aria-live="off">
                    {name.length}/{MAX_NAME}
                  </span>
                )}
              </div>
              <Input
                id="projectName"
                name="projectName"
                ref={inputRef}
                placeholder="e.g. Final Year Capstone\u2026"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                maxLength={MAX_NAME}
                autoComplete="off"
                spellCheck={false}
                aria-invalid={nameError ? true : undefined}
                aria-describedby={nameError ? "projectName-error" : undefined}
                className={cn(nameError && "border-danger focus-visible:ring-danger")}
              />
              {nameError && (
                <p id="projectName-error" role="alert" className="text-xs text-danger">
                  {nameError}
                </p>
              )}
            </div>

            <div className="space-y-1.5">
              <div className="flex items-baseline justify-between gap-2">
                <Label htmlFor="projectDescription">Description (optional)</Label>
                {showDescCount && (
                  <span className="text-2xs text-muted-foreground tabular">
                    {description.length}/{MAX_DESCRIPTION}
                  </span>
                )}
              </div>
              <Textarea
                id="projectDescription"
                name="projectDescription"
                placeholder="Short summary of the project so future-you remembers the context\u2026"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={4}
                maxLength={MAX_DESCRIPTION}
                spellCheck
              />
            </div>

            {error && (
              <p
                role="alert"
                className="rounded-lg border border-danger/25 bg-danger-soft px-3 py-2 text-sm text-danger-soft-foreground"
              >
                {error}
              </p>
            )}

            <div className="flex justify-end gap-2 border-t border-border/70 pt-4">
              <Button type="button" variant="ghost" asChild>
                <Link href="/">Cancel</Link>
              </Button>
              <SubmitButton type="submit" loading={submitting} loadingLabel="Creating\u2026">
                Create project
              </SubmitButton>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
