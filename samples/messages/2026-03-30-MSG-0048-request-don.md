$PROTO: AICP/1.0
$TYPE: REQUEST
$ID: MSG-0048
$REF: NONE
$SEQ: 50
$FROM: Don
$TO: Pharos
$TIME: 2026-03-30T18:30:00-04:00
$TASK: Define and begin migration of AICP core services from JavaScript to .NET
$STATUS: PENDING
$ROLE: Orchestrator
$INTENT: Establish a hybrid architecture with JavaScript UI and .NET protocol core for scalability, validation, and maintainability
PROJECT: InterAI-Protocol
DOMAIN: System Architecture / Protocol Core Migration

---PAYLOAD---

CONTEXT:
The AICP system has expanded beyond initial JavaScript-based prototyping and now supports multiple domains including Operator Hub, InterAI Protocol, and Study Guide. The protocol is becoming central infrastructure, requiring stronger validation, structure, and long-term maintainability.

ARCHITECTURAL DIRECTION:
Adopt a hybrid model:
- JavaScript remains the front-end layer (Viewer, Builder, UI interactions)
- .NET becomes the protocol core (models, validation, services)

OBJECTIVE:
Design and initiate a phased migration of AICP core services into a .NET-based architecture while maintaining compatibility with the existing JavaScript system.

RATIONALE:
The system now requires:
- Strong typing and schema enforcement
- Reusable parsing and validation logic
- Project registry integration
- Routing and orchestration services
- Improved testability and reliability
- A scalable foundation for future productization

SCOPE OF MIGRATION:

MOVE TO .NET CORE:
- AICP message model (header + payload)
- Parser and serializer
- Validation engine
- Project registry service
- Routing resolver (future-ready)
- Shared business rules

REMAIN IN JAVASCRIPT:
- Viewer UI
- Builder UI
- Visualization and interaction layers
- Lightweight client-side workflows

PROPOSED .NET COMPONENT:
Create a class library (name to be finalized):
- InterAI.Protocol
- AICP.Core
- Lodestar.AICP.Core

SUGGESTED CORE STRUCTURE:
Models:
- AicpMessage
- AicpHeader
- AicpPayload

Services:
- AicpParser
- AicpValidator
- ValidationResult
- ProjectRegistryService
- RoutingResolver

SUGGESTED CORE METHODS:
- Parse(rawMessage)
- Serialize(message)
- Validate(message)
- LoadProjects()
- SaveProject(project)
- GetProjectById(id)
- ResolveRoute(message)

PHASED MIGRATION PLAN:

PHASE 1:
- Create .NET class library
- Implement message models, parser, and validator
- Add unit tests for parsing and validation

PHASE 2:
- Implement Project Registry service in .NET
- Integrate with existing project-registry.json

PHASE 3:
- Expose .NET functionality via local API or integration layer
- Connect JS Builder/Viewer to .NET services

PHASE 4:
- Migrate routing and relay logic as appropriate
- Evaluate performance and scalability improvements

REQUIREMENTS:
- Maintain backward compatibility with current JS system
- Avoid full system rewrite
- Ensure modular and testable design
- Support future deployment as API, service, or desktop component

DELIVERABLES:
- Proposed .NET solution/project structure
- Migration roadmap with phases
- Initial implementation plan (Phase 1)
- Data contract between JS and .NET layers
- Risk assessment and compatibility notes

SUCCESS CRITERIA:
- AICP messages can be parsed and validated in .NET reliably
- Project registry functions consistently across systems
- JS front end remains operational with minimal disruption
- Architecture supports multi-project scaling and future productization

NOTES:
This effort represents the transition of AICP from a prototyping system to a durable, extensible protocol platform.

---END---
