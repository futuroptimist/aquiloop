# Duckweed Scooper v1 Design

## Overview
The duckweed scooper is a 3D-printable tool for safely removing duckweed from aquatic habitats.
It aims to be durable, efficient, and non-harmful to pond life while remaining easy to print and use.

## Goals
- Clear floating duckweed without injuring fish or damaging plants.
- Print on common FDM printers without supports.
- Use modular components that can be iterated quickly.

## Non-Goals
- Motorized or automated removal systems.
- Long-term storage solutions for collected duckweed.

## Architecture
The design consists of a hollow mesh head attached to a lightweight handle.
OpenSCAD scripts define parametric dimensions so users can adjust size and thickness.

### Components
- **Handle**: tubular grip sized for common printing tolerances.
- **Mesh head**: perforated scoop that lets water drain while capturing duckweed.
- **Fastener interface**: optional socket for attaching poles or extensions.

## Material Considerations
- PETG or ASA for UV resistance.
- Rounded edges to avoid harming fish.

## Roadmap
- [ ] Prototype
  - [ ] Validate basic scoop geometry
  - [ ] Test wall thickness against bending forces
  - [ ] Evaluate mesh opening size for efficient draining
- [ ] Ergonomics
  - [ ] Add non-slip grip texture
  - [ ] Iterate handle angle for wrist comfort
- [ ] Durability
  - [ ] Stress-test handle/head joint
  - [ ] Explore reinforced ribs
- [ ] Fish Safety
  - [ ] Round all external edges
  - [ ] Simulate flow to reduce suction near fish
- [ ] Efficiency
  - [ ] Optimize mesh pattern for drainage vs. capture
  - [ ] Experiment with head curvature for scooping speed
- [ ] Printability
  - [ ] Ensure designs print without supports
  - [ ] Provide suggested slicer settings
- [ ] Future Extensions
  - [ ] Snap-on net for smaller particles
  - [ ] Telescoping handle module

## Open Questions
- Which mesh sizes best balance water drainage and duckweed retention?
- What handle length provides optimal leverage for most users?
