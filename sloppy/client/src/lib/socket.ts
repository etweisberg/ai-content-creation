// src/lib/socket.ts
const isBrowser = typeof window !== "undefined";

// Create a socket promise that resolves to either a real socket or empty object
export const socketPromise = isBrowser
  ? import("socket.io-client").then(({ io }) => {
      const SOCKET_URL =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      return io(SOCKET_URL, {
        transports: ["websocket", "polling"],
        autoConnect: false,
      });
    })
  : Promise.resolve({});

// For immediate use (will be empty object on server, real socket on client after import)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export let socket: any = {};

// Initialize socket immediately if in browser
if (isBrowser) {
  socketPromise.then((s) => {
    socket = s;
  });
}

// Type guard function
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const isSocketInstance = (s: any): boolean => {
  return s && typeof s.on === "function" && typeof s.emit === "function";
};
