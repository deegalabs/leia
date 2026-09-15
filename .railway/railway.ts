/* Railway infrastructure for the LeIA project.
   This file replaces apps/llm-service/railway.toml: config as code is deprecated and stops being read
   on 2026-12-01, which would silently drop the healthcheck, the builder and the start command.
   Preview with `railway config plan`, apply with `railway config apply`. Never edit these settings in the
   dashboard, or the next apply will revert them. */
import { defineRailway, github, postgres, preserve, project, service, volume } from "railway/iac";

export default defineRailway(() => {
  const Postgres = postgres("Postgres", { region: "us-east4-eqdc4a" });
  Postgres.networking = { privateNetworkEndpoint: "postgres" };

  const llmServiceVolume = volume("llm-service-volume", { alerts: { usage: { "100": {}, "80": {}, "95": {} } }, allowOnlineResize: true, region: "us-east4-eqdc4a", sizeMB: 50000 });
  const postgresVolume = volume("postgres-volume", { alerts: { usage: { "100": {}, "80": {}, "95": {} } }, allowOnlineResize: true, region: "us-east4-eqdc4a", sizeMB: 50000 });

  const llmService = service("llm-service", {
    source: github("deegalabs/leia", {
      rootDirectory: "/apps/llm-service",
      /* wait for the CI workflow: a commit that breaks the suite never reaches production */
      checkSuites: true,
    }),
    build: {
      builder: "DOCKERFILE",
      dockerfilePath: "Dockerfile",
      /* keep what the platform already runs; omitting it would reset to the default */
      buildEnvironment: "V3",
      /* only the service triggers a service build; web and docs commits do not */
      watchPatterns: ["/apps/llm-service/**"],
    },
    deploy: {
      /* no startCommand here: Railway runs it without a shell, so $PORT stays a literal string and
         uvicorn refuses it. The Dockerfile CMD already wraps the same command in sh -c. */
      /* the route that authorises a new version to take over; tests_v3.py asserts the app serves it */
      healthcheckPath: "/health",
      healthcheckTimeout: 120,
      /* restartPolicyType is left out on purpose: ON_FAILURE is the platform default, so declaring it
         reads back as null and every plan would report a change that never settles */
      restartPolicyMaxRetries: 5,
      runtime: "V2",
    },
    replicas: { "us-east4-eqdc4a": 1 },
    volumeMounts: { "/data": llmServiceVolume },
    /* values stay on Railway; this file never carries a secret */
    env: { ADMIN_EMAIL: preserve(), ADMIN_NAME: preserve(), ADMIN_PASSWORD: preserve(), ADVOGADO_SIGNUP: preserve(), API_KEY: preserve(), BASE_URL: preserve(), BRAND_NAME: preserve(), CLIENT_APP_URL: preserve(), CORS_ORIGINS: preserve(), DATABASE_URL: preserve(), DATA_DIR: preserve(), GROQ_API_KEY: preserve(), GROQ_MODEL: preserve(), LOG_LEVEL: preserve(), OTS_ENABLED: preserve(), PIPELINE_CONCURRENCY: preserve(), RATE_LIMIT_PER_MINUTE: preserve(), SESSION_COOKIE_SECURE: preserve() },
  });

  return project("leia", {
    resources: [llmService, Postgres, llmServiceVolume, postgresVolume],
  });
});
