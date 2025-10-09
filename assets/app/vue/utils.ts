// Check if we already have a local user preferred language
// Otherwise just use the navigators language.
export const defaultLocale = () => {
  const user = JSON.parse(localStorage?.getItem('tba/user') ?? '{}');
  return user?.settings?.language ?? navigator.language.split('-')[0];
};
