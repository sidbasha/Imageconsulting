// In-memory stand-in for the device keychain, used by Jest.
const entries = new Map<string, { username: string; password: string }>();
const key = (options?: { service?: string }) => options?.service ?? 'default';

export const setGenericPassword = jest.fn(async (username: string, password: string, options?: { service?: string }) => {
  entries.set(key(options), { username, password });
  return { service: key(options), storage: 'mock' };
});

export const getGenericPassword = jest.fn(async (options?: { service?: string }) => entries.get(key(options)) ?? false);

export const resetGenericPassword = jest.fn(async (options?: { service?: string }) => entries.delete(key(options)));

export const __reset = () => entries.clear();
