# Status: 0017 hosted deployment

Blocked - deferred by user

## Evidence

The user requested: "I want to see a local deployment and test it out before we go ahead with hosting it."

AWS discovery found no configured profiles, credentials or region. No AWS resources were created, no cloud credentials were requested in chat, and no hosted URL exists. Requirements/design are a deployment draft only; infrastructure implementation and provisioning are deferred until local acceptance testing and an explicit hosting go-ahead. The completed application is available locally through the studio API on 8001, Vite on 5173, PostgreSQL on 5433, Keycloak on 8080, and the separate worker. Global live generation remains paused; both local accounts have zero grants. Sample replay works through the demo account without provider calls.
