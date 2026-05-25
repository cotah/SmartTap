import { describe, expect, it } from "vitest";
import { computeRewardState } from "./compute-reward";
import { canAwardStamp } from "./rate-limit";

describe("computeRewardState", () => {
  it("returns 0% with no stamps", () => {
    const state = computeRewardState(0, 10);
    expect(state.progress_percent).toBe(0);
    expect(state.reward_ready).toBe(false);
    expect(state.stamps_remaining).toBe(10);
  });

  it("flags reward ready when threshold met", () => {
    const state = computeRewardState(10, 10);
    expect(state.reward_ready).toBe(true);
    expect(state.stamps_remaining).toBe(0);
    expect(state.progress_percent).toBe(100);
  });

  it("caps progress at 100% when stamps exceed threshold", () => {
    const state = computeRewardState(15, 10);
    expect(state.progress_percent).toBe(100);
    expect(state.reward_ready).toBe(true);
  });
});

describe("canAwardStamp", () => {
  it("allows first stamp when never awarded", () => {
    expect(canAwardStamp(null, 120)).toBe(true);
  });

  it("blocks when within rate limit window", () => {
    const now = new Date("2026-01-01T12:00:00Z");
    const lastStamp = new Date("2026-01-01T11:00:00Z");
    expect(canAwardStamp(lastStamp, 120, now)).toBe(false);
  });

  it("allows after rate limit window passes", () => {
    const now = new Date("2026-01-01T14:00:00Z");
    const lastStamp = new Date("2026-01-01T11:00:00Z");
    expect(canAwardStamp(lastStamp, 120, now)).toBe(true);
  });

  it("never blocks when rate limit is zero", () => {
    const now = new Date("2026-01-01T12:00:01Z");
    const lastStamp = new Date("2026-01-01T12:00:00Z");
    expect(canAwardStamp(lastStamp, 0, now)).toBe(true);
  });
});
