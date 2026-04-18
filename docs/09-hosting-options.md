# Hosting Options

## Goal

Choose a hosting path that matches the real maturity of the verifier stack instead of overbuilding too early.

## Default Delivery Path

### Stage 1

- run everything locally with Docker Compose
- include `web`, `verifier`, `redis`, and optional `nginx`
- use local hosting for developer velocity, webcam debugging, and model iteration

### Stage 2

- move the verifier stack to a single VPS
- keep the Next.js frontend on Vercel
- use this as the shared MVP environment

### Stage 3

- integrate real Sui testnet minting, Walrus, Seal, and zkLogin

### Stage 4

- add GPU or split services only when CPU-only inference becomes the bottleneck

## Local Development Recommendation

- Local Docker Compose is the default development environment.
- It is the fastest way to iterate on webcam flows, ONNX compatibility, and Move work.
- The current development machine is macOS `arm64`, so multi-arch Docker images and ONNX runtime compatibility must be part of bootstrap docs.
- Local exposure should be treated as demo-only, not as the long-lived shared environment.

## VPS Matrix

### Budget-First

Hetzner shared cloud is the cheapest serious VPS path if the preferred region is available. It is suitable for internal demos and early alpha traffic but is less attractive for sustained inference if shared CPU contention becomes visible.

Reference notes checked April 17, 2026:

- Hetzner cloud docs list cloud server availability in the USA and Singapore.
- Hetzner April 1, 2026 price-adjustment examples include `CX23` at `$4.99/mo` and `CX33` at `$7.99/mo` for Germany/Finland examples.
- Hetzner public IPv4 is billed separately in the docs.

Sources:

- [Hetzner Cloud Overview](https://docs.hetzner.com/cloud/servers/overview/)
- [Hetzner Price Adjustment](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/)

### Balanced Default

DigitalOcean Basic and Vultr Regular are the best default fits for a single-verifier VPS because they are predictable, well-documented, and common targets for small production services.

Recommended starting shape:

- `2 vCPU / 4 GB RAM / 80 GB SSD`

Recommended upgrade shape:

- `4 vCPU / 8 GB RAM`

Upgrade triggers:

- shared demos start timing out
- concurrent verification sessions exceed low single digits
- cold starts or model loads consume too much headroom

DigitalOcean pricing checked April 17, 2026:

- `2 GB / 1 vCPU`: `$12/mo`
- `4 GB / 2 vCPU`: `$24/mo`
- `8 GB / 4 vCPU`: `$48/mo`
- CPU-Optimized starts at `4 GB / 2 vCPU`: `$42/mo`

Sources:

- [DigitalOcean Droplet Pricing](https://www.digitalocean.com/pricing/droplets)
- [DigitalOcean Droplet Pricing Docs](https://docs.digitalocean.com/products/droplets/details/pricing/)

Vultr pricing checked April 17, 2026:

- `2 GB / 1 vCPU`: `$10/mo`
- `4 GB / 2 vCPU`: `$20/mo`
- `8 GB / 4 vCPU`: `$40/mo`

Source:

- [Vultr Pricing](https://www.vultr.com/pricing/)

### AWS-Aligned

Lightsail is the most straightforward path when the team expects to migrate deeper into AWS later. It is less cost-efficient than the cheapest VPS vendors, but familiar AWS tooling may reduce operational friction.

Pricing checked April 17, 2026:

- `2 GB / 2 vCPU`: `$12/mo`
- `4 GB / 2 vCPU`: `$24/mo`
- `8 GB / 2 vCPU`: `$44/mo`

Source:

- [AWS Lightsail Pricing](https://aws.amazon.com/lightsail/pricing/)

## Recommendation

### Development Default

- local Docker Compose

### Shared MVP Default

- Next.js frontend on Vercel
- verifier stack on one VPS
- `FastAPI + Redis + Nginx`

### Preferred First VPS Profile

- `2 vCPU / 4 GB RAM`

### Preferred Provider

- DigitalOcean Basic if predictable operations and documentation matter most
- Vultr Regular if minimizing monthly cost matters most

### Defer

- GPU instances until Phase 4 or until heavier anti-spoof and deepfake models are adopted
- Kubernetes until there is a clear concurrency or reliability need

## Deployment Notes To Preserve

- keep chain, Walrus, and Seal credentials out of the frontend
- terminate TLS at Nginx on the VPS
- preserve WebSocket upgrade headers
- expose only the services that must be public
