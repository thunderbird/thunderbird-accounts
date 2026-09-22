/**
 * Deduplicates critical errors by consolidating ehloError and readGreetingError
 * since they represent the same issue (inability to verify domain records connect to Thundermail)
 */
export const deduplicateCriticalErrors = (errors: string[]): string[] => {
  const errorSet = new Set(errors);

  // If both ehloError and readGreetingError exist, keep only readGreetingError
  if (errorSet.has('ehloError') && errorSet.has('readGreetingError')) {
    errorSet.delete('ehloError');
  }

  // If only ehloError exists, replace it with readGreetingError
  else if (errorSet.has('ehloError')) {
    errorSet.delete('ehloError');
    errorSet.add('readGreetingError');
  }

  return Array.from(errorSet);
};
