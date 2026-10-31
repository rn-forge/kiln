import { TestBed } from '@angular/core/testing';
import { LocalStorageService } from '@rn-forge/ng/core';
import { appConfig } from './app.config';

describe('appConfig', () => {
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({ providers: appConfig.providers });
  });

  it('configures ngkit so LocalStorageService round-trips JSON', () => {
    const storage = TestBed.inject(LocalStorageService);
    storage.setJSON('prefs', { theme: 'dark' });
    expect(storage.getJSON<{ theme: string }>('prefs')).toEqual({
      theme: 'dark',
    });
  });
});
