import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';

import { UserState } from '../state/userState';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
    const userState = inject(UserState);
    const token = userState.accessToken();

    if (!token) {
        return next(req);
    }

    return next(
        req.clone({
            setHeaders: {
                Authorization: `Bearer ${token}`,
            },
        })
    );
};
