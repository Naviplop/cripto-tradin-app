export interface License {
  valid: boolean;
  key: string;
  message?: string;
  hwid?: string;
}

export function isValidLicense(l: unknown): l is License {
  if (typeof l !== 'object' || l === null) return false;
  const obj = l as Record<string, unknown>;
  return typeof obj.valid === 'boolean' && typeof obj.key === 'string';
}
