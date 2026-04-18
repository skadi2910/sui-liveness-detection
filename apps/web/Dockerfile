FROM node:22-alpine

WORKDIR /workspace

COPY packages/shared /workspace/packages/shared
COPY apps/web/package.json /workspace/apps/web/package.json

WORKDIR /workspace/apps/web

RUN npm install

COPY apps/web /workspace/apps/web

ENV NEXT_TELEMETRY_DISABLED=1

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0", "--port", "3000"]
