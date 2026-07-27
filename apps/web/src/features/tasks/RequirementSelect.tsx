"use client";

import * as React from "react";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type Option = { id: string; title: string };

type Props = {
  value: string;
  onChange: (next: string) => void;
  requirements: Option[];
  id?: string;
  name?: string;
};

const NONE = "__none__";

export function RequirementSelect({
  value,
  onChange,
  requirements,
  id = "task-requirement",
  name = "taskRequirement",
}: Props) {
  if (requirements.length === 0) {
    return (
      <p className="text-xs text-muted-foreground">
        No linkable requirements yet. Accept or create a requirement first.
      </p>
    );
  }
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>Linked requirement (optional)</Label>
      <Select
        value={value || NONE}
        onValueChange={(v) => onChange(v === NONE ? "" : v)}
        name={name}
      >
        <SelectTrigger id={id} aria-label="Linked requirement">
          <SelectValue placeholder="None" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={NONE}>None</SelectItem>
          {requirements.map((r) => (
            <SelectItem key={r.id} value={r.id}>
              {r.title}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
