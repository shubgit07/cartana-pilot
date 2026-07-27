"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import * as React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { SubmitButton } from "@/components/common/SubmitButton";
import { projectsApi, ApiError } from "@/lib/api";

const MAX_NAME = 120;
const MAX_DESCRIPTION = 2000;

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

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <nav>
        <Link href="/" className="text-sm text-muted-foreground hover:text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">
          ← All projects
        </Link>
      </nav>

      <Card>
        <CardHeader>
          <CardTitle>New project</CardTitle>
          <CardDescription>
            Name it clearly. You can upload documents on the next screen.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4" noValidate>
            <div className="space-y-2">
              <Label htmlFor="projectName">
                Name <span className="text-destructive" aria-hidden="true">*</span>
              </Label>
              <Input
                id="projectName"
                name="projectName"
                ref={inputRef}
                placeholder="e.g. Final Year Capstone…"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                maxLength={MAX_NAME}
                autoComplete="off"
                spellCheck={false}
                aria-invalid={nameError ? true : undefined}
                aria-describedby={nameError ? "projectName-error" : undefined}
              />
              {nameError && (
                <p id="projectName-error" role="alert" className="text-xs text-destructive">
                  {nameError}
                </p>
              )}
              <p className="text-xs text-muted-foreground tabular" aria-live="off">
                {name.length}/{MAX_NAME}
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="projectDescription">Description (optional)</Label>
              <Textarea
                id="projectDescription"
                name="projectDescription"
                placeholder="Short summary of the project so future-you remembers the context…"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={4}
                maxLength={MAX_DESCRIPTION}
                spellCheck
              />
              <p className="text-xs text-muted-foreground tabular">
                {description.length}/{MAX_DESCRIPTION}
              </p>
            </div>
            {error && (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="ghost" asChild>
                <Link href="/">Cancel</Link>
              </Button>
              <SubmitButton
                type="submit"
                loading={submitting}
                loadingLabel="Creating…"
              >
                Create project
              </SubmitButton>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
