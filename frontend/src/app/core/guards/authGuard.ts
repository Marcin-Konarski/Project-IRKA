import { inject } from '@angular/core';
import { CanActivateFn, Router, UrlTree } from '@angular/router';

import { UserState } from '../state/userState';

export const authGuard: CanActivateFn = (_route, state): boolean | UrlTree => {
    const userState = inject(UserState);
    const router = inject(Router);

    if (userState.isLoggedIn()) {
        return true;
    }

    return router.createUrlTree(['/login'], {
        queryParams: {
            authRequired: true,
            redirectTo: state.url,
        },
    });
};
