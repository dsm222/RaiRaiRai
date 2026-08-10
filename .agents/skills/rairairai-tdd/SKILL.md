---
name: rairairai-tdd
description: Apply RaiRaiRai-specific test-driven development when implementing, fixing, or changing gameplay, simulation, persistence, scripting, physics adapters, or UE integration in this repository. This skill composes Matt's installed tdd skill with the project's current architecture and should be used instead of asking for both skills separately.
---

# RaiRaiRai Project TDD

Use this skill as a project-specific overlay. Do not copy general TDD teaching into it.

## Load the required skills

Before taking task actions:

1. Invoke and read the installed `$tdd` skill by Matt completely, including every reference it requires. Its current location is `C:\Users\dsm\.codex\skills\tdd\SKILL.md`; if that path changes, resolve the installed skill named `tdd` instead of silently skipping it.
2. Read `../rairairai-architecture/SKILL.md` completely to obtain the current modules, authority rules, and public seams.
3. Apply Matt's skill as the general TDD policy and this skill as the RaiRaiRai-specific mapping. Do not duplicate Matt's red/green, test-quality, anti-pattern, or Mock guidance here.
4. If Matt's skill cannot be found or read, report that explicitly and do not claim to have followed project TDD.

Invoking `$rairairai-tdd` is therefore sufficient; the user does not need to invoke `$tdd` separately.

## Evolve this skill

- Treat this file as a living project skill.
- Update it directly when real code reveals a better seam, test layout, scenario setup, engine-testing method, or deterministic simulation strategy, and use the improvement in the same task.
- Keep only current project-specific guidance. Remove replaced instructions instead of preserving competing approaches.
- Replace placeholders with real test names, commands, fixtures, and project-relative code links as soon as they exist.
- Update `../rairairai-architecture/SKILL.md` whenever a test improvement changes an architectural boundary.
- Report material skill changes in the task handoff.
- Ask the project owner when the expected player-visible behavior is ambiguous; optimize technical test mechanics without separate approval.

## Project seam mapping

Treat the architecture skill's GameSession boundary as the current candidate simulation seam:

```text
NewGame / Load
Execute(command)
Advance(ticks)
Query(request)
DrainEvents()
Save()
```

Before writing the first real test at this seam, confirm the actual public interface with the project owner as required by Matt's TDD skill. When code establishes a different name or shape, update both project skills before adding more tests.

Exercise simulation behavior through Commands and explicit time advancement. Observe it through command results, Queries, domain events, and public save/load behavior. Do not verify behavior through private systems, internal containers, Widget state, or Actor fields.

## Map tests to the architecture

### Simulation behavior

Test assembly, inventory, sales, orders, research, money, time, and other rules primarily through GameSession without loading a level or constructing gameplay Actors.

Build known state through a public scenario factory, `Load(snapshot)`, or another agreed public setup seam. Keep scenarios small and name them in game vocabulary, for example `GarageWithOneCardKit`. Do not mutate WorldState directly as a hidden test backdoor.

### Definition contracts

Add focused validation when real data assets appear: stable IDs must be unique, references must resolve, and required part/slot configuration must be valid. Keep these tests separate from player behavior tests.

### UE adapters and physics

Use focused Unreal integration tests only for behavior owned by the adapter, including input-to-Command translation, grabbing, collision, semantic snap selection, and event-to-presentation wiring.

Do not ask a physics test to prove inventory consumption, compatibility, card completion, price, or other core rules. Do not ask a headless core test to prove physical feel.

### Persistence

Test save/load through its public round trip. Verify that a restored session produces the same observable Query results and future behavior; do not inspect serialized bytes unless the file format itself is the agreed seam.

## Deterministic project setup

- Supply a known random seed when creating a session.
- Advance game time with explicit ticks or scheduled events; never wait for wall-clock time in a core behavior test.
- Include the seed, Command sequence, and concise state/event summary in failure diagnostics when practical.
- Use known literal expectations from the gameplay specification. Do not calculate expected card statistics with the production formula inside the test.
- Keep unordered iteration and render-frame count from changing simulation results.

Follow Matt's Mock policy. For this project, prefer controllable session inputs for time and randomness over mocking internal systems.

## Work one vertical behavior at a time

Use Matt's red/green loop on a vertical behavior that crosses the architecture through a public seam. The initial candidate sequence is:

1. Complete one graphics card from a known set of compatible parts and observe the finished card plus consumed inventory.
2. Reject a missing or incompatible part without partial state mutation.
3. List the finished card online.
4. Create one deterministic order and expose its observable status.
5. Hand the package to a courier and receive the known payment.

Treat this as an evolving order, not a batch of tests to write in advance. Add only the next test justified by the current slice.

## Current placeholders

No real gameplay tests exist yet. When the first one lands, update this skill with:

- the confirmed GameSession code link and exact seam;
- the Unreal test framework and test-file location;
- the command for one test and the command for the complete relevant suite;
- the real scenario/fixture entry point;
- one small compiling behavior-test example.

Do not retain conceptual pseudocode after real project code can replace it.
