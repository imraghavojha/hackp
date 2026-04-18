const DEFAULT_DENYLIST = ["mail.google.com", "bank", "payments", "stripe"]

export function isDeniedUrl(url: string, extraDenylist: string[] = []): boolean {
  const denylist = [...DEFAULT_DENYLIST, ...extraDenylist]
  return denylist.some((entry) => url.includes(entry))
}

export function shouldCaptureField(fieldType: string | null | undefined): boolean {
  if (!fieldType) {
    return true
  }

  return !["password", "credit-card", "cc-number", "cc-csc"].includes(fieldType)
}

export function redactValue(value: string, maxLength = 500): string {
  return value.slice(0, maxLength)
}
