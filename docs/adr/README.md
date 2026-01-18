# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records documenting significant architectural decisions made for the Tequipy platform.

## What is an ADR?

An Architecture Decision Record (ADR) is a document that captures an important architectural decision made along with its context and consequences.

## ADR Index

| ID                                     | Title                              | Status   | Date    |
| -------------------------------------- | ---------------------------------- | -------- | ------- |
| [0001](./0001-layered-architecture.md) | Layered Architecture Pattern       | Accepted | 2025-01 |
| [0002](./0002-jwt-authentication.md)   | JWT-Based Authentication           | Accepted | 2025-01 |
| [0003](./0003-repository-pattern.md)   | Repository Pattern for Data Access | Accepted | 2025-01 |
| [0004](./0004-http-client-and-caching.md) | HTTP Client and Caching Strategy | Accepted | 2025-01 |

## ADR Template

Use this template when creating new ADRs:

```markdown
# ADR-NNNN: Title

## Status

Proposed | Accepted | Deprecated | Superseded by ADR-XXXX

## Context

What is the issue that we're seeing that is motivating this decision or change?

## Decision

What is the change that we're proposing and/or doing?

## Consequences

What becomes easier or more difficult to do because of this change?

### Positive

- List positive consequences

### Negative

- List negative consequences

### Neutral

- List neutral consequences

## Alternatives Considered

### Alternative 1: Name

Description and why it was not chosen.

### Alternative 2: Name

Description and why it was not chosen.

## References

- Link to relevant documentation
- Link to related ADRs
```

## Creating a New ADR

1. Copy the template above
2. Create a new file: `NNNN-kebab-case-title.md`
3. Fill in all sections
4. Submit for review
5. Update this index

## ADR Lifecycle

```
Proposed → Accepted → [Deprecated | Superseded]
```

- **Proposed**: Under discussion
- **Accepted**: Decision has been made and implemented
- **Deprecated**: No longer valid but kept for historical context
- **Superseded**: Replaced by a newer ADR
