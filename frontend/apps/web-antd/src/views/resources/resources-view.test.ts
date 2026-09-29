import type { ResourceFilterKey } from './resources-view';

import { describe, expect, it } from 'vitest';

import {
  buildResourceListParams,
  canForceReleaseResource,
  canUseResourceDestructiveActions,
  resourceFilterItems,
  resourceTestStatusLabel,
} from './resources-view';

function emptyFilters(): Record<ResourceFilterKey, string> {
  return Object.fromEntries(
    resourceFilterItems.map((item) => [item.key, '']),
  ) as Record<ResourceFilterKey, string>;
}

describe('buildResourceListParams', () => {
  it('builds physical resource params from non-empty filters', () => {
    const filters = emptyFilters();
    filters.primary_ip = ' 172.168.131. ';
    filters.cpu_model = ' kunpeng ';

    expect(
      buildResourceListParams({
        currentUsername: 'te1',
        filters,
        matchMode: 'and',
        page: 2,
        showAll: true,
      }),
    ).toEqual({
      cpu_model: 'kunpeng',
      match: 'and',
      page: 2,
      primary_ip: '172.168.131.',
      resource_type: 'PHYSICAL',
    });
  });

  it('limits default view to resources occupied by the current user', () => {
    expect(
      buildResourceListParams({
        currentUsername: 'te1',
        filters: emptyFilters(),
        matchMode: 'or',
        page: 1,
        showAll: false,
      }),
    ).toEqual({
      current_lease_username: 'te1',
      match: 'or',
      page: 1,
      resource_type: 'PHYSICAL',
    });
  });
});

describe('canForceReleaseResource', () => {
  const baseResource = {
    current_lease_id: 'lease-1',
    current_lease_user_id: 'te-1',
    current_lease_user_role: 'TE',
    test_status: 'idle',
  } as const;

  it('allows an admin to release another user lease', () => {
    expect(
      canForceReleaseResource(baseResource, {
        currentRole: 'ADMIN',
        currentUserId: 'admin-1',
      }),
    ).toBe(true);
  });

  it('allows TSE to release TE leases but not ADMIN or TSE leases', () => {
    const context = { currentRole: 'TSE' as const, currentUserId: 'tse-1' };

    expect(canForceReleaseResource(baseResource, context)).toBe(true);
    expect(
      canForceReleaseResource(
        { ...baseResource, current_lease_user_role: 'TSE' },
        context,
      ),
    ).toBe(false);
    expect(
      canForceReleaseResource(
        { ...baseResource, current_lease_user_role: 'ADMIN' },
        context,
      ),
    ).toBe(false);
  });
});

describe('canUseResourceDestructiveActions', () => {
  it('allows idle resources and rejects resources under test', () => {
    expect(canUseResourceDestructiveActions({ test_status: 'idle' })).toBe(
      true,
    );
    expect(canUseResourceDestructiveActions({ test_status: 'testing' })).toBe(
      false,
    );
  });

  it('provides user-facing labels for the independent test state', () => {
    expect(resourceTestStatusLabel('idle')).toBe('空闲');
    expect(resourceTestStatusLabel('testing')).toBe('测试中');
  });
});
