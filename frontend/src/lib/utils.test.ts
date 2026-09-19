import { describe, expect, it } from "vitest"

import { formatPassengers, formatSigned } from "./utils"

describe("formatting", () => {
  it("formats passenger counts for Russian locale", () => {
    expect(formatPassengers(12345)).toMatch(/12\s345/)
  })

  it("keeps a sign on scenario deltas", () => {
    expect(formatSigned(12, "%")).toBe("+12%")
  })
})
