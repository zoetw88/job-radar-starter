interface Env {
  STATUS_COORDINATOR: DurableObjectNamespace<
    import("./src/index").StatusCoordinator
  >;
  SYNC_TOKEN: string;
}
