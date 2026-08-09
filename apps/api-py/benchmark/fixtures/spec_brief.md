# Project Atlas — Team Task Management API

**Product Requirements Document · v2.1**

## 1. Overview

Project Atlas is a small team task-management API. Users register an account,
create and manage tasks, assign tasks to teammates, and are notified when work
is handed to them. The product is API-first: a single REST backend consumed by
a web client.

This document defines the release scope for the v2.1 milestone. Implementation
is delivered as a sequence of pull requests against the Atlas codebase.

## 2. Goals & Non-Goals

**Goals**

- Provide a secure, multi-user task management backend.
- Give users a clear audit trail of all changes made to their workspace.
- Protect authentication endpoints from brute-force credential stuffing.

**Non-Goals**

- Real-time collaboration or presence.
- Mobile push notifications (email / in-app notifications only).

## 3. Functional Requirements

### 3.1 User authentication

Users must be able to register with an email and a password, sign in to obtain a
session token, and sign out to revoke it. Passwords must never be stored in
plain text. Sign-in failures must return the same generic error regardless of
whether the email exists, to avoid account enumeration.

### 3.2 Task management

Authenticated users must be able to create, list, update, and delete tasks.
Tasks carry a title and an optional description. Only the workspace owner may
delete a task.

### 3.3 Task assignment and status tracking

Tasks must be assignable to users and track a status of `todo`, `in_progress`,
or `done`. Reassigning a task to another user is allowed and records the new
owner.

### 3.4 Notification delivery

The system must deliver a notification alert to a user when a task is assigned
to them, either as an in-app notification or an email. Assignment performed by
the user themselves does not produce a notification.

## 4. Non-Functional Requirements

### 4.1 Rate limiting on authentication

Authentication endpoints must be rate limited to prevent brute force attacks.
Clients exceeding the limit within a rolling window receive a `429` response and
a short backoff.

### 4.2 Audit logging

All mutating operations (task create, update, delete, reassignment) must write
an audit log entry recording the actor, the action, and a timestamp.

## 5. Acceptance Criteria

1. A user can register, sign in, sign out, and cannot sign in with a wrong
   password.
2. A user can create, list, update, and delete a task.
3. A user can assign a task to a teammate and move it through
   `todo → in_progress → done`.
4. Assigning a task to a teammate delivers a notification to that teammate.
5. More than N rapid authentication attempts return `429` and trigger the rate
   limiter.
6. Every mutating operation produces an audit log entry.

## 6. Out of Scope

- Billing, workspaces, roles beyond owner/member.
- Deletion of accounts and GDPR export tooling.
