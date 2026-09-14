# Design

## Decisions
Use GitHub-native Mermaid for a maintainable workflow diagram and a separate detailed deployment diagram. Capture the existing local application with Playwright, using existing demo data and no paid generation. Images belong in docs/images and have descriptive alt text. Keep the README focused on product value, a short demonstration path, setup, configuration, validation and limitations. Move the previous README into a clearly historical reference for legacy commands, removing obsolete current-studio claims. No runtime interfaces or shared contracts change.

## Interfaces
Document goldcoast.api.studio_app, goldcoast.studio.worker, goldcoast.studio.admin and the existing React routes. Reference infra/lightsail/README.md for hosted commands. Screenshots use relative Markdown paths.
