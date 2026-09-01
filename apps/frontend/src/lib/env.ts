export const env = {
  dataSource: process.env.NEXT_PUBLIC_DATA_SOURCE ?? "mock",
  apiUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  wsUrl: process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/factory",
  showDemoCredentials: process.env.NEXT_PUBLIC_SHOW_DEMO_CREDENTIALS === "true",
};

export const usesMockData = env.dataSource !== "api";
