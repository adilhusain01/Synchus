# Synchus Capability Lab

Incoming evidence sometimes describes a useful entity, field, workflow, or visualization that Synchus does not yet model. Synchus treats that as a capability gap—not permission for an AI model to edit production.

## Promotion path

1. Preserve the raw, redacted source as an immutable intake event.
2. Prefer existing context. A new capability is proposed only when ordinary knowledge cannot represent a reusable structured need.
3. Hold the extracted sample data outside canonical context.
4. Propose a typed, additive capability manifest with affected product surfaces, validation checks, source, risk, and rollback behavior.
5. Let an authorized person approve or reject it in Capability Lab.
6. On approval, register the manifest and activate the held record. On rollback, disable the capability and return records to held state without deleting evidence.

The current implementation is deliberately declarative. It supports new data shapes without generated SQL, shell commands, dependencies, or arbitrary source edits.

## When bespoke code is actually required

A later builder may turn an approved manifest into a code proposal, but it must operate outside the running application:

- create an isolated Git worktree pinned to a known base revision;
- generate the smallest patch and explicit forward/backward migration;
- run allowlisted formatting, type, unit, migration, and smoke checks;
- record the diff, commands, artifacts, test results, data impact, and rollback revision;
- require a second promotion approval before merge or deployment;
- never receive production credentials or direct write access to the production database.

Code approval and factual-data approval remain distinct. A successful build does not make the source statement true, and approving a statement does not authorize a deployment.
