const normalizeProjectName = (projectName: string) => projectName.toLowerCase();

/**
 * BrowserStack mobile project names identify the device OS, while the local
 * mobile-emulation project is named after its Pixel device profile.
 */
export const isMobileAndroidProject = (projectName: string) => {
  const normalizedProjectName = normalizeProjectName(projectName);
  return normalizedProjectName.includes('android') || normalizedProjectName.includes('pixel');
};

/** Identify current or future BrowserStack iOS projects without affecting desktop Safari. */
export const isMobileIOSProject = (projectName: string) => {
  const normalizedProjectName = normalizeProjectName(projectName);
  return normalizedProjectName.includes('ios') || normalizedProjectName.includes('iphone');
};

/** Return true for either an Android or iOS project. */
export const isMobileProject = (projectName: string) => (
  isMobileAndroidProject(projectName) || isMobileIOSProject(projectName)
);
