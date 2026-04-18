import { DEFAULT_DENYLIST, MAX_CAPTURED_TEXT_LENGTH } from "../lib/constants"

const PAYMENT_AUTOCOMPLETE_RE = /(cc-|card|payment)/i
const NAME_AUTOCOMPLETE_RE = /(?:^|[\s-])(name)$/i
const CARD_NUMBER_RE = /\b(?:\d[ -]*?){13,19}\b/

export function isDeniedUrl(url: string, extraDenylist: string[] = []): boolean {
  const denylist = [...DEFAULT_DENYLIST, ...extraDenylist]
  return denylist.some((entry) => url.includes(entry))
}

export function shouldCaptureField(
  fieldType: string | null | undefined,
  autocomplete: string | null | undefined,
  value = ""
): boolean {
  if ((fieldType ?? "").toLowerCase() === "password") {
    return false
  }

  if (autocomplete && (PAYMENT_AUTOCOMPLETE_RE.test(autocomplete) || NAME_AUTOCOMPLETE_RE.test(autocomplete))) {
    return false
  }

  if (CARD_NUMBER_RE.test(value)) {
    return false
  }

  return true
}

export function redactValue(value: string, maxLength = MAX_CAPTURED_TEXT_LENGTH): string {
  return value.slice(0, maxLength)
}
