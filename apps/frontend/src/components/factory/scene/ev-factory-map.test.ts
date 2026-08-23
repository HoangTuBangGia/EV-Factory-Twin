import { beforeAll, describe, expect, it, vi } from "vitest";
import { AMR_FLEET_DATA } from "./ev-factory-data";
import { buildFactoryScene } from "./ev-factory-map";

beforeAll(() => {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
});

describe("buildFactoryScene", () => {
  it("excludes prototype AMRs unless the standalone demo explicitly requests them", () => {
    const realtimeEnvironment = buildFactoryScene();
    const standaloneDemo = buildFactoryScene({ includeDemoAmrs: true });

    expect(realtimeEnvironment.amrEntities).toHaveLength(0);
    expect(standaloneDemo.amrEntities).toHaveLength(AMR_FLEET_DATA.length);

    realtimeEnvironment.dispose();
    standaloneDemo.dispose();
  });
});
