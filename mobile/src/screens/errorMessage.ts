import type { TFunction } from 'i18next';

import { ApiError } from '../api/client';

/**
 * Text to show for a failed request. The API already answers in the user's
 * language for errors it knows; the app only supplies wording for failures
 * the server could not describe (no connection, malformed input, unknown).
 */
export function errorMessage(error: unknown, t: TFunction): string {
  if (error instanceof ApiError) {
    if (['network_error', 'validation_error', 'unexpected_error'].includes(error.code)) {
      return t(`errors.${error.code}`);
    }
    return error.message;
  }
  return t('errors.unexpected_error');
}
