import { describe, expect, it } from 'vitest';

import { overridesPreferences } from './preferences';

describe('kronos preferences', () => {
  it('hides the language switch while the product is Chinese-only', () => {
    expect(overridesPreferences.widget?.languageToggle).toBe(false);
  });
});
