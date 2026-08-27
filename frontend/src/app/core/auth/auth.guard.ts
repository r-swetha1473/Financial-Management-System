import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { Permission, canMaintainReference, hasPermission } from '../rbac/permissions';
import { AuthService } from './auth.service';

export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (auth.isAuthenticated()) {
    return true;
  }
  return router.createUrlTree(['/login']);
};

export const guestGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (auth.isAuthenticated()) {
    return router.createUrlTree(['/dashboard']);
  }
  return true;
};

export function permissionGuard(permission: Permission): CanActivateFn {
  return () => {
    const auth = inject(AuthService);
    const router = inject(Router);
    if (hasPermission(auth.session()?.role, permission)) {
      return true;
    }
    return router.createUrlTree(['/dashboard']);
  };
}

export const referenceDataGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (canMaintainReference(auth.session()?.role)) {
    return true;
  }
  return router.createUrlTree(['/dashboard']);
};
