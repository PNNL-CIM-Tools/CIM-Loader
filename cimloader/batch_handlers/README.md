# batch_handlers

Placeholder package for multi-file CIM workflows.

## Planned use case

CIM models are often distributed as a **package** of profile-specific
files — Equipment (EQ), Topology (TP), and Steady-State Hypothesis (SSH)
each contain complementary attributes for the same objects (same mRIDs).

Uploading each file in turn with a plain `upload_from_file` overwrites the
previous file's attributes. The intended batch handler here would:

1. Take a list of profile files (EQ, TP, SSH, ...).
2. Upload them in order, **appending** attributes to existing objects
   keyed by mRID rather than replacing them.
3. Emit a report of which attributes came from which profile.

No implementation yet. See `design/TODO.md`.
