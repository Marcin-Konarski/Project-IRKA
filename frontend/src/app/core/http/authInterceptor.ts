import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

import { UserState } from '../state/userState';

let handlingUnauthorized = false;

function shouldIgnoreUnauthorized(url: string): boolean {
    return url.includes('/auth/login') || url.includes('/auth/signup');
}

export const authInterceptor: HttpInterceptorFn = (req, next) => {
    const userState = inject(UserState);
    const router = inject(Router);
    const token = userState.accessToken();

    const authReq = token
        ? req.clone({
            setHeaders: {
                Authorization: `Bearer ${token}`,
            },
        })
        : req;

    return next(authReq).pipe(
        catchError((error: HttpErrorResponse) => {
            if (
                error.status === 401
                && token
                && !shouldIgnoreUnauthorized(req.url)
                && !handlingUnauthorized
            ) {
                handlingUnauthorized = true;
                userState.clearUser();

                void router.navigate(['/login'], {
                    queryParams: {
                        authRequired: true,
                        sessionExpired: true,
                        redirectTo: router.url,
                    },
                }).finally(() => {
                    handlingUnauthorized = false;
                });
            }

            return throwError(() => error);
        }),
    );
};
