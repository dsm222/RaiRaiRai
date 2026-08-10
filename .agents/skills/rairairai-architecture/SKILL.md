---
name: rairairai-architecture
description: Apply and evolve the current architecture of the RaiRaiRai GPU-manufacturer simulation. Use for architecture, gameplay-system design, implementation, refactoring, review, module boundaries, simulation state, UE adapters, scripting, save/load, time, randomness, or physics integration in this repository. Do not use for work unrelated to RaiRaiRai.
---

# RaiRaiRai Project Architecture

Treat this skill as the project's current architecture, not as a frozen historical proposal.

## Evolve this skill

- Read this file before making an architectural or implementation decision.
- Inspect the current code before applying conceptual examples from this file.
- Update this `SKILL.md` directly when a simpler, safer, more testable design becomes clear, and use the improved design in the same task.
- Keep only the current recommended architecture. Replace superseded guidance instead of accumulating competing alternatives.
- Replace conceptual names and examples with real types, signatures, commands, and project-relative code links as implementation appears.
- Update `../rairairai-tdd/SKILL.md` whenever a changed boundary affects test seams or test setup.
- Report material skill changes in the task handoff.
- Ask the project owner before changing a player-facing product goal or materially expanding scope; purely technical improvements do not require separate approval.
- Resolve code/document drift deliberately: update this skill when the code is better, or update the code when this skill is better. Never leave two authoritative designs.

## Current project context

- Use Unreal Engine 5.8.
- Treat the existing `RaiRaiRai` runtime module as a project skeleton; no gameplay architecture has been implemented yet.
- Support the progression from manual GPU assembly and sales toward research, stores, factories, and upstream production without implementing speculative late-game systems early.
- Build one playable vertical slice at a time.

## Architecture shape

Use a **deterministic simulation core with multiple adapters**.

```text
UE input / physics ----\
Script / debug ---------> GameSession -> Commands -> Rules -> WorldState
Automated tests -------/                    |          |
                                            +-> Results / Events / Query Views
```

Use MVC only inside a presentation feature when useful. Use ECS or Unreal Mass only for high-volume homogeneous entities after profiling shows a need. Neither pattern defines the top-level architecture.

## Simulation data

Separate static definitions from per-save state.

### Definitions

Describe types and design data such as parts, interfaces, slots, machines, products, recipes, and research. Reference each definition by a stable ID.

### WorldState

Store authoritative runtime facts such as funds, game time, inventory, assembly projects, completed cards, listings, orders, research, stores, and production tasks.

Keep WorldState serializable and versioned. Do not store Actor pointers as durable identity. Treat Actors, Widgets, animations, and temporary physics bodies as projections of state, not alternative authorities.

## Simulation logic

Use one public application boundary, currently called `GameSession`. Keep this name provisional until real code establishes it.

```text
NewGame(seed)
Load(snapshot)
Execute(command) -> result
Advance(ticks) -> result
Query(request) -> read-only view
DrainEvents() -> domain events
Save() -> snapshot
```

Apply these rules:

- Express caller intent with semantic Commands such as `InstallPart`, `FinishGraphicsCard`, `ListProductOnline`, and `HandPackageToCourier`.
- Validate a Command before committing its state change. Return a stable, testable failure reason and avoid partial mutation.
- Let rules or systems mutate WorldState only behind GameSession; never let UI, Blueprint, Actor, test, or script edit authoritative state directly.
- Emit domain events for facts that already happened, such as `PartInstalled`, `GraphicsCardCompleted`, or `ProductSold`.
- Expose purpose-built read-only Query Views instead of returning mutable WorldState.
- Let UE, tests, scripts, and debug tools perform the same gameplay action through the same Command boundary.
- Keep internal systems and domain objects private implementation details unless a later design establishes another explicit public seam.

Use state snapshots for persistence. Do not adopt full event sourcing without a demonstrated need.

## Dependency boundaries

Keep dependencies pointing inward:

```text
UE / Script / Persistence adapters -> GameSession API -> Simulation rules and data
```

- Keep the simulation core independent of UMG, levels, input devices, and Chaos physics.
- Keep Blueprint focused on presentation and content orchestration; never let it bypass GameSession to change authoritative gameplay data.
- Map loaded Actors to simulation entities through stable IDs. Unloading an Actor must not delete or pause its durable simulation state unless a rule explicitly does so.
- Prefer a future `RaiRaiRaiSim` module for simulation code and keep `RaiRaiRai` as the UE-facing game/adapter module.
- Make `RaiRaiRaiSim` depend on the smallest practical UE foundation. Add a separate test module only when real build constraints justify it.

Update this section with actual module files and dependencies when the first slice creates them.

## Physical assembly boundary

Separate physical interaction from deterministic assembly rules.

Let the UE adapter handle picking up, rotating, colliding, dropping, highlighting, snapping, and playing installation feedback. When the player attempts a meaningful operation, translate it into a semantic command such as:

```text
InstallPart(CardId, SlotId, PartId)
```

Let the simulation core decide compatibility, ownership, inventory consumption, completion, and final card parameters. Apply the core result back to the physical presentation.

Test physical feel and input translation through focused UE integration tests. Test compatibility, inventory, completion, and statistics through deterministic simulation behavior tests.

## Time and randomness

- Advance gameplay time explicitly through the simulation instead of deriving authoritative results from render-frame count.
- Use fixed ticks or scheduled simulation events where time matters.
- Own seeded randomness inside the session or an injected boundary so a failed scenario can be replayed.
- Let UE interpolate visuals per frame without letting visual interpolation decide economic, assembly, order, or research results.

Change these defaults when implementation evidence supports a better deterministic model, and update both project skills at that time.

## Save evolution

- Save versioned WorldState snapshots plus the time and random state required for replaying future behavior.
- Reference Definitions with stable IDs.
- Add explicit migration or explicit rejection for incompatible save versions; never silently misread old data.
- Replace this section with real schema and migration links when they exist.

## First vertical slice

Prefer this initial end-to-end path:

> Assemble one graphics card from the friend's supplied parts, list it online, receive one deterministic order, hand the package to a courier, and receive payment.

Implement only the portion required by the current failing test. Use the completed slice to revise this architecture from evidence before expanding breadth.

## Decision check

Before completing a design or code change, verify:

- Is there one authoritative write path for each rule?
- Can UE, a script, and a test trigger the behavior through the same public boundary?
- Can the core behavior run without a loaded level or transient Actor?
- Are frame time, random state, and physics separated from deterministic rules?
- Is the design solving a current vertical slice instead of a hypothetical future framework?
- Did any new evidence require updating this skill or the project TDD skill?
