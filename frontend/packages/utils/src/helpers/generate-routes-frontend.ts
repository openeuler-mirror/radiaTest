import type { RouteRecordRaw } from 'vue-router';

import { filterTree, mapTree } from '@vben-core/shared/utils';

/**
 * 动态生成路由 - 前端方式
 */
async function generateRoutesByFrontend(
  routes: RouteRecordRaw[],
  roles: string[],
  forbiddenComponent?: RouteRecordRaw['component'],
): Promise<RouteRecordRaw[]> {
  if (forbiddenComponent) {
    return mapTree(routes, (route) => {
      if (canAccessRoute(route, roles)) {
        return route;
      }

      const meta = route.meta;
      if (!meta) {
        return route;
      }
      route.component = forbiddenComponent;
      route.children = [];
      route.meta = {
        ...meta,
        hideInMenu: !menuHasVisibleWithForbidden(route),
      };
      return route;
    });
  }

  // 根据角色标识过滤路由表,判断当前用户是否拥有指定权限
  return filterTree(routes, (route) => {
    return hasAuthority(route, roles);
  });
}

/**
 * 判断路由是否有权限访问
 * @param route
 * @param access
 */
function hasAuthority(route: RouteRecordRaw, access: string[]) {
  const canAccess = canAccessRoute(route, access);
  return canAccess || (!canAccess && menuHasVisibleWithForbidden(route));
}

function canAccessRoute(route: RouteRecordRaw, access: string[]) {
  const authority = route.meta?.authority;
  if (!authority) {
    return true;
  }
  return access.some((value) => authority.includes(value));
}

/**
 * 判断路由是否在菜单中显示，但是访问会被重定向到403
 * @param route
 */
function menuHasVisibleWithForbidden(route: RouteRecordRaw) {
  return (
    !!route.meta?.authority &&
    Reflect.has(route.meta || {}, 'menuVisibleWithForbidden') &&
    !!route.meta?.menuVisibleWithForbidden
  );
}

export { generateRoutesByFrontend, hasAuthority };
