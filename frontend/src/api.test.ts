import { api, ApiError, getStoredApiToken, removeStoredApiToken, setStoredApiToken } from "./api";

function mockFetch(status: number, payload?: unknown, reject?: Error) {
  const implementation = vi.fn().mockImplementation(() => {
    if (reject) return Promise.reject(reject);
    return Promise.resolve({
      ok: status >= 200 && status < 300,
      status,
      json: () => Promise.resolve(payload ?? {}),
    });
  });
  window.fetch = implementation as unknown as typeof fetch;
  return implementation;
}

describe("api token handling", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("does not send authorization without a stored token", async () => {
    const fetchMock = mockFetch(200, { items: [] });

    await api.projects();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects",
      expect.objectContaining({ headers: expect.not.objectContaining({ Authorization: expect.any(String) }) }),
    );
  });

  it("sends bearer authorization after setting a token", async () => {
    const fetchMock = mockFetch(200, { items: [] });
    setStoredApiToken("user-token");

    await api.projects();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects",
      expect.objectContaining({ headers: { Authorization: "Bearer user-token" } }),
    );
  });

  it("uses a changed token immediately", async () => {
    const fetchMock = mockFetch(200, { items: [] });
    setStoredApiToken("first-token");
    await api.projects();
    setStoredApiToken("second-token");
    await api.projects();

    expect(fetchMock.mock.calls[1][1]).toEqual(expect.objectContaining({ headers: { Authorization: "Bearer second-token" } }));
  });

  it("stops sending authorization after clearing the token", async () => {
    const fetchMock = mockFetch(200, { items: [] });
    setStoredApiToken("user-token");
    removeStoredApiToken();

    await api.projects();

    expect(fetchMock.mock.calls[0][1]).toEqual(expect.objectContaining({ headers: {} }));
  });

  it("marks 401 responses as unauthorized", async () => {
    mockFetch(401, { detail: "Invalid API token" });

    const error = await api.projects().catch((value: unknown) => value);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).unauthorized).toBe(true);
    expect((error as ApiError).message).toContain("token");
  });

  it("converts network failures to a readable error", async () => {
    mockFetch(0, undefined, new TypeError("Network down"));

    const error = await api.projects().catch((value: unknown) => value);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).message).toContain("无法连接服务");
  });

  it("rejects an empty token as unset", () => {
    setStoredApiToken("   ");

    expect(getStoredApiToken()).toBeNull();
  });
});
