# ADR-0007: Skills are filesystem-backed instruction bundles in the MVP

## Status

Accepted — 2026-08-14. Closes the gap found in review 0002: the MVP agent
definition accepts a `skills` field that no workstream consumed.

## Context

Spec section 8 puts `skills` in the agent definition. Section 14
describes a skills system with a registry, versioning, installation,
dependencies, permissions, and dynamic loading, and marks those as future
capability. Section 24's MVP list never mentions skills, and section 26
defers a skill registry to Phase 2. The original decomposition therefore
gave skills no owner.

That produces two defects. An agent declaring
`skills: [git, playwright, pytest]` would have the field silently
ignored, which is the failure mode ADR-0004 exists to prevent. And the
section 25 acceptance test requires the agent to create and repair
Playwright tests, with nothing to carry the instructions describing how
that project's tests are structured.

Rejecting any definition that names a skill would close the first defect
and worsen the second.

## Decision

The MVP loads skills from the filesystem. There is no registry.

- Skills live in the top-level `skills/` directory that spec section 23
  already reserves, one directory per skill containing `skill.yaml` in
  the section 14 format: `name`, `version`, `description`, `tools`,
  `requirements.commands`, and `instructions`.
- At agent creation, every name in the definition's `skills` list must
  resolve to a loadable skill directory. An unresolvable name is a 422.
  Skills are never silently dropped.
- A skill contributes three things at run start: its `tools` are added to
  the tool set the agent may call, subject to the `permissions` block,
  which always wins; its `instructions` are appended to the system prompt
  in declaration order; and its `requirements.commands` are verified to
  exist inside the agent container before the first iteration, with a
  missing command failing the run before any model call is made.
- The agent can enumerate its loaded skills at run time through a
  `list_skills` tool, satisfying section 14's discovery requirement.
- The MVP ships three skills: `git`, `coding`, and `testing`, matching
  the directories named in section 23. The acceptance test in W12 adds a
  `playwright-testing` skill.

Skill registry, versioning, installation, dependency resolution, and
dynamic loading remain Phase 2 per section 14 and section 26.

## Consequences

- A new workstream, W7 Skills, sits between W6 workspace and runtime and
  the provider layer. Design 0001 becomes thirteen workstreams.
- Skills are declarative and diffable. Changing agent behavior does not
  require changing Juice Box.
- Verifying `requirements.commands` before the first model call turns a
  mid-run failure into a fast startup failure, which matters because a
  missing `npx` would otherwise be discovered after minutes of token
  spend.
- The permission block outranking skill-granted tools means a skill
  cannot widen an agent's authority. A skill listing the shell tool under
  `permissions.shell: false` gets its instructions and not the tool.
- Skills are local to the Juice Box deployment in the MVP, so an agent
  cannot acquire a skill the operator has not installed. That is the
  intended security posture, and section 29 lists dynamic skill
  generation as a non-goal.
