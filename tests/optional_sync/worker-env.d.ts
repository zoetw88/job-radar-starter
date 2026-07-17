declare module "cloudflare:workers" {
  interface ProvidedEnv {
    STATUS_COORDINATOR: DurableObjectNamespace<
      import("../../optional-sync/cloudflare/src/index").StatusCoordinator
    >;
    SYNC_TOKEN: string;
  }
}
