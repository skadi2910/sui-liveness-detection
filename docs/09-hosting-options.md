# Hosting Options

## Goal

Choose the simplest hosting path that fits the actual MVP:

- Docker is the deployment priority.
- low-ops shared environments matter more than platform sophistication
- CPU-only inference is the baseline until real usage proves otherwise
- WebSocket session flow and backend-kept secrets are non-negotiable

## MVP Reality Check

The repository already points toward a Docker-first stack:

- `apps/web` has a Dockerfile
- `services/verifier` has a Dockerfile
- root `docker-compose.yml` already wires `web`, `verifier`, and `redis`

The current Compose setup is ideal for local development, but not yet a production deployment shape:

- `apps/web/Dockerfile` runs `npm run dev`
- there is no production reverse-proxy config yet
- there is no production Compose manifest yet
- there is no VPS bootstrap or runbook yet

Implementation status as of April 18, 2026:

- `docker-compose.prod.yml` now exists for local production-parity testing
- `proxy/nginx.conf` now routes `/` to Next.js and `/api/*` plus `/ws/*` to the verifier
- `apps/web/Dockerfile.prod` builds a production `next build` + `next start` image using standalone output
- `services/verifier/Dockerfile` now includes the system libraries required by OpenCV / ONNX Runtime
- browser-facing verifier URLs now default to same-origin routing when public env overrides are unset

That means the right question for MVP is not "which sophisticated platform should we use?"
It is "what is the smallest stable Docker deployment we can support with confidence?"

## Recommendation

### Development Default

- keep local Docker Compose as the default developer workflow
- use it for webcam flow testing, ONNX compatibility checks, and verifier iteration
- treat local exposure as demo-only, not as the shared team environment

### Shared MVP Default

- deploy the first shared environment to one Linux VPS
- run the stack with Docker Compose
- host `web`, `verifier`, `redis`, and `nginx` or `caddy` on the same machine

### Why This Is The Best MVP Fit

- Docker parity stays high between local and shared environments
- `web` and `verifier` move together as one release unit
- WebSocket routing is simpler when the reverse proxy and backend sit together
- verifier secrets stay off the frontend by default
- Redis stays private on the Docker network
- one VPS is cheaper and easier to debug than a split multi-provider setup

## Recommended Delivery Path

### Stage 1: Local Docker Compose

- continue using the current root `docker-compose.yml`
- verify webcam capture, REST session creation, WebSocket flow, and model loading locally
- use this phase to harden the container images
- use `docker-compose.prod.yml` for proxy-based production-parity smoke tests

### Stage 2: Single-VPS Docker MVP

Run these containers on one VPS:

- `web`
- `verifier`
- `redis`
- `nginx` or `caddy`

Operational shape:

- TLS terminated at the reverse proxy
- only `80` and `443` exposed publicly
- `redis` private to the internal Docker network
- `verifier` not exposed directly if the proxy can route to it internally
- persistent volume only where genuinely needed

This should be the first shared demo, alpha, and partner-testing environment.

### Stage 3: Selective Split

Only split the stack when one of these becomes true:

- frontend preview workflows become more important than environment parity
- verifier CPU load starts starving the web container
- shared demos need stricter rollback and release isolation

The first split, if needed, should be:

- `web` on Vercel
- `verifier + redis + reverse proxy` on a VPS

This is a later optimization, not the default MVP recommendation.

### Stage 4: GPU Or Service Decomposition

Only consider this when CPU-only inference is no longer good enough:

- repeated verifier latency spikes under real concurrent use
- higher-cost anti-spoof or deepfake models become required
- evidence handling or chain integration needs independent scaling

Do not introduce Kubernetes in the MVP phase.

## Hosting Options Ranked For This Project

### Option A: Single VPS + Docker Compose

Best fit for MVP.

Pros:

- highest local-to-shared parity
- simplest release story
- lowest operational sprawl
- easiest to keep Redis private
- easiest path for reverse-proxying REST and WebSockets together

Cons:

- manual server ownership
- less polished preview workflow than Vercel or Render
- one box is a single point of failure

Verdict:

- recommended default for the first shared environment

### Option B: Vercel For `web` + VPS For `verifier`

Good second step once the frontend needs independent preview and release velocity.

Pros:

- excellent frontend previews
- simpler frontend deployment workflow
- verifier still stays in Docker on a VPS

Cons:

- lower parity with local Compose
- extra origin and WebSocket coordination
- two deployment surfaces instead of one

Verdict:

- useful later, but premature as the first shared MVP environment if Docker parity is the current priority

### Option C: Managed Docker PaaS

Candidates worth knowing about:

- Render supports Docker-based deploys and inbound WebSockets
- Railway can build and deploy from a Dockerfile
- Fly.io is Docker-friendly and offers usage-based machine pricing

Pros:

- less server administration
- faster initial deployment experience
- some platform features out of the box

Cons:

- more platform-specific behavior than a plain VPS
- pricing can become less predictable than a single VPS
- Redis, disk, networking, and process topology need closer platform-specific review

Verdict:

- acceptable fallback if the team wants less ops than VPS management, but not the clearest first choice for this repo

## Provider Guidance For The First VPS

### Best Default: DigitalOcean

Why:

- predictable pricing
- straightforward docs
- widely used small-production VPS path
- easy recommendation for a first Docker host

Recommended starting shape:

- `2 vCPU / 4 GB RAM / 80 GB SSD`

Recommended upgrade shape:

- `4 vCPU / 8 GB RAM`

DigitalOcean pricing checked April 18, 2026:

- `2 GB / 1 vCPU / 50 GB SSD`: `$12/mo`
- `4 GB / 2 vCPU / 80 GB SSD`: `$24/mo`
- `8 GB / 4 vCPU / 160 GB SSD`: `$48/mo`
- CPU-Optimized starts at `4 GB / 2 vCPU / 25 GB SSD`: `$42/mo`

Source:

- [DigitalOcean Droplet Pricing](https://www.digitalocean.com/pricing/droplets)

### Budget Alternative: Vultr

Why:

- familiar VPS experience
- competitive standard pricing
- good fit if minimizing monthly cost matters more than vendor familiarity

Vultr pricing checked April 18, 2026:

- Regular Performance `2 GB / 1 vCPU / 55 GB`: `$10/mo`
- Regular Performance `4 GB / 2 vCPU / 80 GB`: `$20/mo`
- High Performance `4 GB / 2 vCPU / 128 GB`: `$24/mo`
- High Performance `8 GB / 3 vCPU / 256 GB`: `$48/mo`

Sources:

- [Vultr Pricing](https://www.vultr.com/pricing/)
- [Vultr Cloud Compute Docs](https://docs.vultr.com/products/compute/cloud-compute)

### Lowest-Cost Option To Watch Carefully: Hetzner

Why:

- very attractive pricing in Europe and the USA
- strong option if region availability lines up with users and operations

Tradeoff:

- pricing varies meaningfully by region
- public IPs are not included in server prices
- Singapore pricing is much less aggressive than Germany or Finland

Hetzner pricing checked April 18, 2026:

Germany / Finland examples:

- `CX23`: `$4.99/mo`
- `CX33`: `$7.99/mo`
- `CPX32`: `$15.99/mo`

Singapore examples:

- `CPX22`: `$18.49/mo`
- `CPX32`: `$38.49/mo`

Sources:

- [Hetzner Cloud Overview](https://docs.hetzner.com/cloud/servers/overview)
- [Hetzner Price Adjustment](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/)

### AWS-Aligned Option: Lightsail

Why:

- appropriate if the team expects to move deeper into AWS later
- simpler than full AWS while keeping familiar account and region workflows

Tradeoff:

- usually not the cheapest path for this MVP

Lightsail pricing checked April 18, 2026:

- `2 GB / 2 vCPU`: `$12/mo`
- `4 GB / 2 vCPU`: `$24/mo`
- `8 GB / 2 vCPU`: `$44/mo`

Lightsail regional note checked April 18, 2026:

- Asia Pacific Singapore is available
- Asia Pacific Malaysia became available on April 7, 2026

Sources:

- [AWS Lightsail Pricing](https://aws.amazon.com/lightsail/pricing/)
- [Lightsail Regions and Availability Zones](https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-regions-and-availability-zones-in-amazon-lightsail.html)
- [AWS Lightsail Malaysia Region Announcement](https://aws.amazon.com/about-aws/whats-new/2026/04/amazon-lightsail-malaysia/)

## Region Recommendation

For a Vietnam-centered or Southeast-Asia-centered MVP, prefer the nearest practical region:

- Singapore first
- Malaysia second if it is available and makes account or latency sense
- avoid Europe-first deployments unless price clearly outweighs latency

This matters because the product depends on camera flow responsiveness and WebSocket interaction, not only background API calls.

## MVP Infrastructure Plan

### Must Do Before Shared MVP

1. convert `apps/web` from a development Docker image to a production image using `next build` and `next start`
2. create a production Compose file for VPS deployment
3. add reverse-proxy configuration for TLS and WebSocket upgrades
4. add health checks and restart policies
5. document required environment variables and secret placement
6. confirm Linux `amd64` model/runtime behavior for ONNX and OpenCV

### Nice To Have Soon After

1. automated image builds in CI
2. a basic deployment runbook
3. log retention and error monitoring
4. snapshot or backup guidance for VPS recovery

## Final Recommendation

For the MVP, use a Docker-first path end to end:

- local development on Docker Compose
- first shared environment on one VPS with Docker Compose
- choose DigitalOcean as the default first provider
- start with `2 vCPU / 4 GB RAM`
- keep Vercel and managed Docker platforms as later optimizations, not the starting point

This keeps the team focused on product validation instead of platform complexity.
